"""Etapa 5: histórico completo tipado e camada analítica escolar."""

import csv
import json
import logging
import re
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq

from src.pipeline.camada_analitica import gerar_camada_analitica, validar_relacionamentos
from src.pipeline.config import (
    BASE_TAXAS_RENDIMENTO_CONSOLIDADA, INTERIM_TAXAS_RENDIMENTO_DIR,
    RELATORIO_CONSOLIDACAO, TAMANHO_LOTE, COMPRESSAO_PARQUET, DASHBOARD_DIR, SCHEMA_CONSOLIDACAO,
)
from src.pipeline.metricas import mapa_metricas
from src.pipeline.validacao_consolidacao import (
    Auditoria, IDENTIFICACAO, RASTREABILIDADE, colunas_taxas, schema_historico, tipar_lote,
)

LOGGER = logging.getLogger(__name__)
PADRAO_ANO_ARQUIVO = re.compile(r"taxas_rendimento_(\d{4})\.parquet$")


def extrair_ano_arquivo(caminho: Path) -> str:
    correspondencia = PADRAO_ANO_ARQUIVO.fullmatch(caminho.name)
    return correspondencia.group(1) if correspondencia else ""


def listar_arquivos_padronizados(diretorio_entrada: Path = INTERIM_TAXAS_RENDIMENTO_DIR) -> list[Path]:
    # Inclui nomes inesperados para reportá-los, em vez de omiti-los silenciosamente.
    return sorted(diretorio_entrada.rglob("*.parquet"))


def salvar_relatorio_consolidacao(relatorio: list[dict], caminho_saida: Path) -> None:
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    campos = list(dict.fromkeys(c for linha in relatorio for c in linha))
    with TemporaryDirectory(prefix=".relatorio-", dir=caminho_saida.parent) as pasta:
        temporario = Path(pasta) / caminho_saida.name
        with temporario.open("w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=campos)
            escritor.writeheader()
            escritor.writerows(relatorio)
        temporario.replace(caminho_saida)


def inspecionar_entradas(arquivos: list[Path], relatorio: list[dict]) -> dict[int, tuple[Path, pa.Schema]]:
    entradas = {}
    for caminho in arquivos:
        ano = extrair_ano_arquivo(caminho)
        registro = dict(ano=ano, arquivo_entrada=caminho.as_posix(), status="ok", observacao="")
        relatorio.append(registro)
        try:
            if not ano:
                raise ValueError("Nome de arquivo anual inválido.")
            if int(ano) in entradas:
                raise ValueError(f"Mais de um arquivo para o ano {ano}.")
            mapa_metricas(int(ano))
            parquet = pq.ParquetFile(caminho)
            schema = parquet.schema_arrow
            if len(schema.names) != len(set(schema.names)):
                raise ValueError("Nomes de colunas duplicados.")
            if not {"ano", "co_entidade"}.issubset(schema.names):
                raise ValueError("Colunas obrigatórias ausentes: ano e/ou co_entidade.")
            if not colunas_taxas(schema.names):
                raise ValueError("Arquivo sem colunas de taxas.")
            for campo in schema:
                if pa.types.is_nested(campo.type) or pa.types.is_binary(campo.type):
                    raise ValueError(f"Metadado não escalar não suportado: {campo.name}.")
            entradas[int(ano)] = (caminho, schema)
            registro.update(quantidade_linhas_entrada=parquet.metadata.num_rows,
                            quantidade_colunas_originais=len(schema),
                            colunas_ausentes=";".join(sorted(set(IDENTIFICACAO + RASTREABILIDADE).difference(schema.names))),
                            colunas_desconhecidas=";".join(sorted(set(schema.names).difference(
                                IDENTIFICACAO + RASTREABILIDADE + list(mapa_metricas(int(ano)))))),
                            metricas_ausentes=";".join(sorted(set(mapa_metricas(int(ano))).difference(schema.names))),
                            metricas_desconhecidas=";".join(sorted(set(colunas_taxas(schema.names)).difference(mapa_metricas(int(ano))))))
        except (OSError, ValueError, pa.ArrowException) as erro:
            registro.update(status="erro", observacao=str(erro))
            LOGGER.error("%s: %s", caminho.name, erro)
    return entradas


def consolidar_arquivo(caminho: Path, ano: int, schema: pa.Schema,
                       escritor: pq.ParquetWriter) -> Auditoria:
    auditoria = Auditoria()
    for lote in pq.ParquetFile(caminho).iter_batches(batch_size=TAMANHO_LOTE):
        dados, textos = tipar_lote(lote.to_pandas(), ano, schema)
        auditoria.atualizar(dados, textos)
        tabela = pa.Table.from_pandas(dados, schema=schema, preserve_index=False, safe=True)
        escritor.write_table(tabela)
    return auditoria


def publicar(saidas: list[tuple[Path, Path]], pasta_backup: Path) -> None:
    """Substitui artefatos completos e restaura anteriores em falhas de publicação.

    Recupera exceções de I/O; não é uma transação contra desligamento do sistema.
    """
    publicados, backups = [], []
    try:
        for i, (origem, destino) in enumerate(saidas):
            destino.parent.mkdir(parents=True, exist_ok=True)
            if destino.exists():
                backup = pasta_backup / f"backup-{i}"
                destino.replace(backup)
                backups.append((backup, destino))
            origem.replace(destino)
            publicados.append((destino, origem))
    except OSError:
        for destino, origem in reversed(publicados):
            destino.replace(origem)
        for backup, destino in reversed(backups):
            backup.replace(destino)
        raise


def registrar_schemas(historico: Path, dashboard: Path, destino: Path) -> None:
    arquivos = {"historico": historico}
    arquivos.update({p.relative_to(dashboard).as_posix(): p for p in sorted(dashboard.rglob("*.parquet"))})
    schemas = {nome: {c.name: str(c.type) for c in pq.ParquetFile(p).schema_arrow}
               for nome, p in arquivos.items()}
    documento = dict(schemas=schemas, particionamento={"campo": "ano", "tipo": "int32", "formato": "hive"},
                     chave_analitica=["ano", "co_entidade"],
                     duplicidades="contagens de ocorrências excedentes, não todos os membros do grupo",
                     dimensoes="IDs SHA-256 dos atributos; junção por id_escola/id_municipio")
    destino.write_text(json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8")


def gerar_base_consolidada(
    diretorio_entrada: Path = INTERIM_TAXAS_RENDIMENTO_DIR,
    caminho_saida: Path = BASE_TAXAS_RENDIMENTO_CONSOLIDADA,
    caminho_relatorio: Path = RELATORIO_CONSOLIDACAO,
    diretorio_dashboard: Path | None = None,
    caminho_schema: Path | None = None,
) -> list[dict]:
    """Publica as duas camadas somente após validação de todas as entradas.

    Falhas ficam no relatório (TOTAL.status=erro); produtos anteriores permanecem.
    Caminhos derivados dos parâmetros permitem execução isolada em testes.
    """
    dashboard = diretorio_dashboard or (
        DASHBOARD_DIR if caminho_saida == BASE_TAXAS_RENDIMENTO_CONSOLIDADA
        else caminho_saida.parent / DASHBOARD_DIR.name)
    schema_saida = caminho_schema or (
        SCHEMA_CONSOLIDACAO if caminho_relatorio == RELATORIO_CONSOLIDACAO
        else caminho_relatorio.parent / SCHEMA_CONSOLIDACAO.name)
    relatorio: list[dict] = []
    arquivos = listar_arquivos_padronizados(diretorio_entrada)
    total = dict(ano="TOTAL", arquivos_encontrados=len(arquivos), arquivos_processados=0,
                 anos_encontrados="", anos_processados="",
                 quantidade_linhas_entrada=0, quantidade_linhas_consolidadas=0,
                 quantidade_linhas_descartadas=0, linhas_analiticas=0, publicado=False,
                 arquivo_saida=caminho_saida.as_posix(), status="erro", observacao="")
    escolas, municipios, ufs = set(), set(), set()
    try:
        if not arquivos:
            raise ValueError("Nenhum arquivo Parquet padronizado encontrado.")
        entradas = inspecionar_entradas(arquivos, relatorio)
        total["anos_encontrados"] = ";".join(map(str, sorted(entradas)))
        total["quantidade_linhas_entrada"] = sum(r.get("quantidade_linhas_entrada", 0) for r in relatorio)
        if any(r["status"] == "erro" for r in relatorio):
            raise ValueError("Entradas inválidas; nenhuma saída substituída.")
        schema = schema_historico([s for _, s in entradas.values()])
        anos = sorted(entradas)
        lacunas = sorted(set(range(min(anos), max(anos) + 1)).difference(anos))
        total.update(anos_ausentes=";".join(map(str, lacunas)),
                     quantidade_colunas_consolidadas=len(schema), quantidade_colunas_taxas=len(colunas_taxas(schema.names)))
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".consolidacao-", dir=caminho_saida.parent) as pasta:
            temporario = Path(pasta)
            historico = temporario / "historico.parquet"
            with pq.ParquetWriter(historico, schema, compression=COMPRESSAO_PARQUET) as escritor:
                for registro in relatorio:
                    ano = int(registro["ano"])
                    caminho, original = entradas[ano]
                    LOGGER.info("Consolidando %s", caminho.name)
                    try:
                        auditoria = consolidar_arquivo(caminho, ano, schema, escritor)
                    except (OSError, ValueError, TypeError, pa.ArrowException) as erro:
                        registro.update(status="erro", observacao=str(erro))
                        raise
                    registro.update(auditoria.resumo())
                    registro["quantidade_colunas_ausentes"] = len(set(schema.names).difference(original.names))
                    avisos = any(auditoria.contagens[c] for c in (
                        "escolas_ausentes", "municipios_ausentes", "ufs_invalidas", "valores_invalidos", "valores_textuais",
                        "codigos_escola_invalidos", "codigos_municipio_invalidos"))
                    registro["status"] = "aviso" if (
                        avisos or registro["colunas_ausentes"] or registro["metricas_ausentes"]
                        or registro["colunas_desconhecidas"]) else "ok"
                    if auditoria.contagens["duplicidades_ano_escola"]:
                        registro.update(status="erro", observacao="Chave ano/escola repetida; camada analítica bloqueada.")
                    for chave, valor in auditoria.contagens.items():
                        if chave != "quantidade_linhas_entrada":
                            total[chave] = total.get(chave, 0) + valor
                    escolas.update(auditoria.escolas)
                    municipios.update(auditoria.municipios)
                    ufs.update(auditoria.ufs)
                    total["arquivos_processados"] += 1
                    total["anos_processados"] = ";".join(
                        r["ano"] for r in relatorio if "quantidade_linhas_consolidadas" in r)
                    LOGGER.info("Ano %s: %s", ano, registro)
            if any(r["status"] == "erro" for r in relatorio):
                raise ValueError("Duplicidades detectadas; nenhuma saída substituída.")
            if pq.ParquetFile(historico).metadata.num_rows != total["quantidade_linhas_entrada"]:
                raise ValueError("Contagem histórica divergente da entrada.")
            contagens = gerar_camada_analitica(historico, temporario / "dashboard",
                                             {a: s.names for a, (_, s) in entradas.items()})
            for registro in relatorio:
                registro["linhas_analiticas"] = contagens[int(registro["ano"])]
                if registro["linhas_analiticas"] != registro["quantidade_linhas_consolidadas"] - registro["escolas_ausentes"]:
                    raise ValueError("Contagem analítica divergente.")
            registrar_schemas(historico, temporario / "dashboard", temporario / "schema.json")
            validar_relacionamentos(temporario / "dashboard")
            total["relacionamentos_validados"] = True
            publicar([(historico, caminho_saida), (temporario / "dashboard", dashboard),
                      (temporario / "schema.json", schema_saida)], temporario)
            total.update(publicado=True, linhas_analiticas=sum(contagens.values()),
                         status="aviso" if lacunas or any(r["status"] == "aviso" for r in relatorio) else "ok",
                         observacao="Histórico e camada analítica publicados. Exclusão analítica somente por escola ausente.")
    except (OSError, ValueError, TypeError, sqlite3.Error, pa.ArrowException) as erro:
        total.update(status="erro", observacao=str(erro))
        LOGGER.error("Consolidação não publicada: %s", erro)
    total.update(quantidade_escolas=len(escolas), municipios_unicos=len(municipios),
                 ufs_encontradas=";".join(sorted(ufs)))
    relatorio.append(total)
    salvar_relatorio_consolidacao(relatorio, caminho_relatorio)
    return relatorio
