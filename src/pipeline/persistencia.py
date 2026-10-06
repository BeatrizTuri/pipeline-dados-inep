"""Carga integral, auditável e transacional da publicação analítica da Etapa 5."""

import csv
import hashlib
import json
import logging
import math
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from dotenv import dotenv_values

from src.pipeline.camada_analitica import ATRIBUTOS_ESCOLA, ATRIBUTOS_MUNICIPIO, SCHEMA_ANALITICO
from src.pipeline.config import DASHBOARD_DIR, PROJECT_ROOT, RELATORIOS_DIR, TAMANHO_LOTE
from src.pipeline.metricas import COLUNAS_METRICAS, dimensao_metricas

LOGGER = logging.getLogger(__name__)
VERSAO = "etapa6-v1"
LOCK = 60420072024
TABELAS = ("dim_municipio", "dim_escola", "catalogo_metricas", "fato_rendimento_escolar")
COLUNAS = {
    "dim_municipio": ["id_municipio", *ATRIBUTOS_MUNICIPIO],
    "dim_escola": ["id_escola", "co_entidade", "no_entidade", "id_municipio", "tipoloca", "dependad", *ATRIBUTOS_MUNICIPIO],
    "catalogo_metricas": list(dimensao_metricas().columns),
    "fato_rendimento_escolar": ["ano", "co_entidade", "id_escola", "id_municipio", *COLUNAS_METRICAS],
}
EXTRAS_FATO = [c for c in SCHEMA_ANALITICO.names if c not in COLUNAS["fato_rendimento_escolar"]]
CHAVES = {"dim_municipio": ["id_municipio"], "dim_escola": ["id_escola"],
          "catalogo_metricas": ["ano_inicio", "codigo_original"], "fato_rendimento_escolar": ["ano", "co_entidade"]}


class ErroPersistencia(ValueError):
    """Violação do contrato ou pré-condição da carga."""


def configuracao(caminho=None):
    """Lê exclusivamente .env; nunca devolve credenciais para logs/relatórios."""
    valores = dotenv_values(caminho or PROJECT_ROOT / ".env", interpolate=False)
    nomes = {"host": "POSTGRES_HOST", "port": "POSTGRES_PORT", "dbname": "POSTGRES_DB",
             "user": "POSTGRES_USER", "password": "POSTGRES_PASSWORD"}
    ausentes = [v for v in nomes.values() if not valores.get(v)]
    if ausentes:
        raise ErroPersistencia("Configuração ausente no .env: " + ", ".join(ausentes))
    try:
        porta = int(valores["POSTGRES_PORT"])
        if not 1 <= porta <= 65535:
            raise ValueError
    except ValueError:
        raise ErroPersistencia("POSTGRES_PORT deve estar entre 1 e 65535.") from None
    if valores["POSTGRES_USER"].lower() == "postgres":
        raise ErroPersistencia("Configure o usuário da aplicação, não postgres.")
    return {**{k: valores[v] for k, v in nomes.items()}, "port": porta, "connect_timeout": 5}


def identidade_git():
    try:
        def executar(*args):
            return subprocess.check_output(["git", *args], cwd=PROJECT_ROOT, text=True,
                                           stderr=subprocess.DEVNULL, timeout=10).strip()
        return {"commit_pipeline": executar("rev-parse", "HEAD"),
                "codigo_modificado": bool(executar("status", "--porcelain"))}
    except (OSError, subprocess.SubprocessError):
        return {"commit_pipeline": None, "codigo_modificado": None,
                "aviso_git": "Git indisponível; identidade do código não confirmada."}


def hash_arquivo(caminho):
    h = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def arquivos_origem(origem):
    arquivos = [origem / n for n in ("dim_municipios.parquet", "dim_escolas.parquet", "dim_metricas.parquet")]
    arquivos += sorted((origem / "taxas").rglob("*.parquet"))
    if len(arquivos) < 4 or any(not p.is_file() for p in arquivos):
        raise ErroPersistencia("Produtos da Etapa 5 ausentes: dimensões, catálogo e partições de taxas são obrigatórios.")
    return arquivos


def capturar_origem(origem, destino, relatorios):
    """Cópia imutável; hashes antes/depois impedem captura de arquivos em substituição."""
    origem, destino = Path(origem), Path(destino)
    arquivos = arquivos_origem(origem)
    controles = [Path(relatorios) / "relatorio_consolidacao.csv", Path(relatorios) / "schema_consolidacao.json"]
    if any(not p.is_file() for p in controles):
        raise ErroPersistencia("Relatório/schema da Etapa 5 ausentes.")
    todos = arquivos + controles
    antes = {p: hash_arquivo(p) for p in todos}
    with controles[0].open(encoding="utf-8", newline="") as f:
        total = next((r for r in csv.DictReader(f) if r["ano"] == "TOTAL"), {})
    if total.get("publicado", "").lower() != "true" or total.get("status") not in ("ok", "aviso"):
        raise ErroPersistencia("Etapa 5 sem publicação válida: conferir TOTAL.publicado e status.")
    manifesto = {"arquivos": [], "publicacao_etapa5": total, "versao_produtora": "desconhecida",
                 "avisos": [total.get("observacao", "")] if total["status"] == "aviso" else []}
    for p in todos:
        relativo = p.relative_to(origem) if p in arquivos else Path("controles") / p.name
        copia = destino / relativo
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, copia)
        if hash_arquivo(copia) != antes[p]:
            raise ErroPersistencia("Origem mudou durante a captura.")
        stat = p.stat()
        try:
            caminho = p.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            caminho = relativo.as_posix()
        manifesto["arquivos"].append({"caminho": caminho, "tamanho": stat.st_size,
                                      "modificacao": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                                      "sha256": antes[p]})
    if arquivos_origem(origem) != arquivos or any(hash_arquivo(p) != antes[p] for p in todos):
        raise ErroPersistencia("Origem mudou durante a captura; execute fora da publicação da Etapa 5.")
    # O contrato do schema JSON é guardado integralmente com a captura.
    manifesto["schema_etapa5"] = json.loads((destino / "controles/schema_consolidacao.json").read_text(encoding="utf-8"))
    registrados = manifesto["schema_etapa5"].get("schemas", {})
    for arquivo in arquivos_origem(destino):
        nome = arquivo.relative_to(destino).as_posix()
        schema = {c.name: str(c.type) for c in pq.ParquetFile(arquivo).schema_arrow}
        if registrados.get(nome) != schema:
            raise ErroPersistencia("Schema publicado diverge do Parquet: " + nome)
    anos, linhas = [], 0
    for p in (destino / "taxas").rglob("*.parquet"):
        ano = ano_particao(p)
        anos.append(ano)
        linhas += pq.ParquetFile(p).metadata.num_rows
    anos = sorted(set(anos))
    if linhas <= 0:
        raise ErroPersistencia("Primeira carga/base analítica vazia não permitida.")
    if linhas != int(total["linhas_analiticas"]) or anos != sorted(map(int, total["anos_processados"].split(";"))):
        raise ErroPersistencia("Contagens/anos dos Parquets divergem do relatório da Etapa 5.")
    manifesto.update(anos=anos, ano_minimo=min(anos), ano_maximo=max(anos), quantidade_linhas=linhas,
                     quantidade_escolas=pq.ParquetFile(destino / "dim_escolas.parquet").metadata.num_rows,
                     quantidade_municipios=pq.ParquetFile(destino / "dim_municipios.parquet").metadata.num_rows,
                     quantidade_metricas=54,
                     quantidade_metricas_catalogo=pq.ParquetFile(destino / "dim_metricas.parquet").metadata.num_rows)
    return manifesto


def ano_particao(caminho):
    correspondencias = [re.fullmatch(r"ano=(\d{4})", p) for p in Path(caminho).parts]
    anos = [int(m[1]) for m in correspondencias if m]
    if len(anos) != 1:
        raise ErroPersistencia("Partição Hive inválida: ano obrigatório e único.")
    return anos[0]


def validar_schema(schema, esperado):
    if set(schema.names) != set(esperado.names) or len(schema.names) != len(esperado.names):
        raise ErroPersistencia("Schema/métrica inesperada ou ausente no Parquet.")
    for campo in esperado:
        recebido = schema.field(campo.name).type
        texto_equivalente = pa.types.is_string(campo.type) and (pa.types.is_string(recebido) or pa.types.is_large_string(recebido))
        if recebido != campo.type and not texto_equivalente:
            raise ErroPersistencia(f"Tipo incompatível no Parquet: {campo.name}; códigos devem permanecer texto.")


def validar_lote(lote):
    """Arrow NULL vira None; NaN válido e infinito são erros, sem correção silenciosa."""
    for nome in COLUNAS_METRICAS:
        if nome in lote.schema.names:
            for valor in lote.column(nome).to_pylist():
                if valor is not None and (not math.isfinite(valor) or not 0 <= valor <= 100):
                    raise ErroPersistencia(f"Taxa inválida em {nome}: requer NULL ou valor finito em [0,100].")


def digest_linhas(digest, linhas):
    for linha in linhas:
        digest.update(json.dumps(linha, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        digest.update(b"\n")


def carregar_parquet(conexao, tabela, arquivos):
    nomes = COLUNAS[tabela].copy()
    if tabela == "fato_rendimento_escolar":
        nomes += EXTRAS_FATO
    nomes_copia = ["_ord", *[n for n in nomes if not (tabela == "dim_escola" and n == "id_municipio")]]
    esperado = (SCHEMA_ANALITICO if tabela == "fato_rendimento_escolar" else
                pa.schema([(c, pa.int64() if c in ("ano_inicio", "ano_fim") else pa.string())
                           for c in nomes_copia if c != "_ord"]))
    digest, contador = hashlib.sha256(), 0
    comando = sql.SQL("COPY {} ({}) FROM STDIN").format(sql.Identifier("stg_" + tabela),
                         sql.SQL(",").join(map(sql.Identifier, nomes_copia)))
    with conexao.cursor() as cursor, cursor.copy(comando) as copia:
        for arquivo in arquivos:
            parquet = pq.ParquetFile(arquivo)
            validar_schema(parquet.schema_arrow, esperado)
            ano = ano_particao(arquivo) if tabela == "fato_rendimento_escolar" else None
            LOGGER.info("COPY %s: %s", tabela, arquivo.name if ano is None else f"ano={ano}")
            for lote in parquet.iter_batches(batch_size=TAMANHO_LOTE):
                validar_lote(lote)
                if ano is not None:
                    lote = lote.append_column("ano", pa.array([ano] * lote.num_rows, type=pa.int32()))
                valores = [lote.column(c).to_pylist() for c in nomes_copia[1:]]
                for linha in zip(*valores, strict=True):
                    contador += 1
                    copia.write_row((contador, *linha))
                    digest_linhas(digest, [linha])
    conexao.execute(sql.SQL("CREATE UNIQUE INDEX ON {} (_ord)").format(sql.Identifier("stg_" + tabela)))
    conexao.execute(sql.SQL("ANALYZE {}").format(sql.Identifier("stg_" + tabela)))
    # Comparação tipada de toda a transferência, na ordem original, sem carregar a fato em memória.
    recebido = hashlib.sha256()
    with conexao.cursor(name="fidelidade_" + tabela) as cursor:
        cursor.execute(sql.SQL("SELECT {} FROM {} ORDER BY _ord").format(
            sql.SQL(",").join(map(sql.Identifier, nomes_copia[1:])), sql.Identifier("stg_" + tabela)))
        while linhas := cursor.fetchmany(TAMANHO_LOTE):
            digest_linhas(recebido, linhas)
    if digest.digest() != recebido.digest():
        raise ErroPersistencia("Divergência de conteúdo Parquet–staging: " + tabela)
    return {"linhas": contador, "sha256_conteudo": digest.hexdigest(), "fidelidade": True}


def criar_staging(conexao):
    for tabela in TABELAS:
        # CTAS conserva tipos, mas permite verificar dados antes das constraints definitivas.
        conexao.execute(sql.SQL("CREATE TEMP TABLE {} ON COMMIT PRESERVE ROWS AS SELECT * FROM public.{} WITH NO DATA").format(
            sql.Identifier("stg_" + tabela), sql.Identifier(tabela)))
        conexao.execute(sql.SQL("ALTER TABLE {} ADD COLUMN _ord bigint").format(sql.Identifier("stg_" + tabela)))
    for campo in EXTRAS_FATO:
        conexao.execute(sql.SQL("ALTER TABLE stg_fato_rendimento_escolar ADD COLUMN {} text").format(sql.Identifier(campo)))


def exigir_zero(conexao, consulta, nome, validacoes):
    quantidade = conexao.execute(consulta).fetchone()[0]
    validacoes[nome] = quantidade
    if quantidade:
        raise ErroPersistencia(f"Validação {nome}: {quantidade} divergências.")


def validar_staging(conexao, manifesto, validacoes):
    for tabela in TABELAS:
        stg = "stg_" + tabela
        chaves = CHAVES[tabela]
        agrupamento = ",".join(chaves)
        exigir_zero(conexao, f"SELECT count(*) FROM (SELECT {agrupamento} FROM {stg} GROUP BY {agrupamento} HAVING count(*)>1) d",
                    "duplicidade_" + tabela, validacoes)
        obrigatorias = chaves + (["co_entidade"] if tabela == "dim_escola" else [])
        if tabela == "dim_municipio":
            obrigatorias += ["co_municipio"]
        if tabela == "fato_rendimento_escolar":
            obrigatorias += ["id_escola"]
        if tabela == "catalogo_metricas":
            obrigatorias = COLUNAS[tabela]
        exigir_zero(conexao, f"SELECT count(*) FROM {stg} WHERE " + " OR ".join(f"{c} IS NULL" for c in obrigatorias),
                    "nulos_" + tabela, validacoes)
        for c in (n for n in COLUNAS[tabela] if n.startswith("id_")):
            exigir_zero(conexao, f"SELECT count(*) FROM {stg} WHERE {c} IS NOT NULL AND {c} !~ '^[0-9a-f]{{64}}$'",
                        "hash_" + tabela + "_" + c, validacoes)
    # Tuple join index handles nullable historical attributes without a Cartesian join.
    conexao.execute("CREATE INDEX ON stg_dim_municipio (co_municipio)")
    geo = " AND ".join(f"e.{c} IS NOT DISTINCT FROM m.{c}" for c in ATRIBUTOS_MUNICIPIO)
    exigir_zero(conexao, f"SELECT count(*) FROM (SELECT e._ord FROM stg_dim_escola e LEFT JOIN stg_dim_municipio m ON e.co_municipio=m.co_municipio AND {geo} WHERE e.co_municipio IS NOT NULL GROUP BY e._ord HAVING count(m.id_municipio)<>1) d",
                "correspondencia_municipal_escola", validacoes)
    conexao.execute(f"UPDATE stg_dim_escola e SET id_municipio=m.id_municipio FROM stg_dim_municipio m WHERE e.co_municipio=m.co_municipio AND {geo}")
    for tabela in ("dim_escola", "dim_municipio"):
        chave = CHAVES[tabela][0]
        conexao.execute(f"CREATE UNIQUE INDEX ON stg_{tabela} ({chave})")
        colunas = [c for c in COLUNAS[tabela] if c != "id_municipio" or tabela == "dim_municipio"]
        comparacao = " OR ".join(f"s.{c} IS DISTINCT FROM p.{c}" for c in colunas)
        exigir_zero(conexao, f"SELECT count(*) FROM stg_{tabela} s JOIN public.{tabela} p USING ({chave}) WHERE {comparacao}",
                    "hash_conteudo_anterior_" + tabela, validacoes)
    exigir_zero(conexao, "SELECT count(*) FROM stg_dim_escola e LEFT JOIN stg_dim_municipio m USING(id_municipio) WHERE e.id_municipio IS NOT NULL AND m.id_municipio IS NULL",
                "fk_municipio_escola", validacoes)
    exigir_zero(conexao, "SELECT count(*) FROM stg_fato_rendimento_escolar f LEFT JOIN stg_dim_escola e USING(id_escola) WHERE e.id_escola IS NULL",
                "fk_escola_fato", validacoes)
    exigir_zero(conexao, "SELECT count(*) FROM stg_fato_rendimento_escolar f LEFT JOIN stg_dim_municipio m USING(id_municipio) WHERE f.id_municipio IS NOT NULL AND m.id_municipio IS NULL",
                "fk_municipio_fato", validacoes)
    comparacoes = ["co_entidade", "id_municipio", *EXTRAS_FATO]
    exigir_zero(conexao, "SELECT count(*) FROM stg_fato_rendimento_escolar f JOIN stg_dim_escola e USING(id_escola) WHERE " +
                " OR ".join(f"f.{c} IS DISTINCT FROM e.{c}" for c in comparacoes), "atributos_fato_escola", validacoes)
    condicoes = " OR ".join(f"({c} IS NOT NULL AND NOT ({c}>=0 AND {c}<=100))" for c in COLUNAS_METRICAS)
    exigir_zero(conexao, "SELECT count(*) FROM stg_fato_rendimento_escolar WHERE " + condicoes, "taxas_fora_faixa", validacoes)
    registros = conexao.execute("SELECT " + ",".join(COLUNAS["catalogo_metricas"]) + " FROM stg_catalogo_metricas").fetchall()
    esperado = list(dimensao_metricas().itertuples(index=False, name=None))
    if sorted(registros) != sorted(esperado):
        raise ErroPersistencia("Catálogo incompatível com aliases, períodos ou descrições do contrato atual.")
    validacoes["catalogo_incompativel"] = 0
    contagens = contagens_banco(conexao, "stg_")
    for chave in ("quantidade_linhas", "quantidade_escolas", "quantidade_municipios", "quantidade_metricas_catalogo", "ano_minimo", "ano_maximo"):
        if contagens[chave] != manifesto[chave]:
            raise ErroPersistencia("Contagem staging divergente: " + chave)
    anos = [r[0] for r in conexao.execute("SELECT DISTINCT ano FROM stg_fato_rendimento_escolar ORDER BY ano")]
    if anos != manifesto["anos"]:
        raise ErroPersistencia("Anos staging divergentes.")
    anterior = conexao.execute("SELECT manifesto_origem FROM public.controle_carga WHERE carga_ativa").fetchone()
    if anterior:
        antigo = anterior[0]
        if not set(antigo.get("anos", [])).issubset(anos) or any(contagens[c] < antigo.get(c, 0) for c in ("quantidade_linhas", "quantidade_escolas", "quantidade_municipios")):
            raise ErroPersistencia("Redução de período/contagens: revise explicitamente a origem antes de substituir a publicação.")
    validacoes["staging"] = contagens
    validacoes["por_ano"] = dict(conexao.execute("SELECT ano,count(*) FROM stg_fato_rendimento_escolar GROUP BY ano ORDER BY ano").fetchall())
    validacoes["nulos_metricas"] = dict(zip(COLUNAS_METRICAS, conexao.execute("SELECT " + ",".join(f"count(*) FILTER(WHERE {c} IS NULL)" for c in COLUNAS_METRICAS) + " FROM stg_fato_rendimento_escolar").fetchone()))
    return contagens


def contagens_banco(conexao, prefixo="public."):
    resultado = {}
    for tabela, chave in zip(TABELAS, ("quantidade_municipios", "quantidade_escolas", "quantidade_metricas_catalogo", "quantidade_linhas"), strict=True):
        resultado[chave] = conexao.execute(f"SELECT count(*) FROM {prefixo}{tabela}").fetchone()[0]
    resultado["quantidade_codigos_escola"] = conexao.execute(f"SELECT count(DISTINCT co_entidade) FROM {prefixo}dim_escola").fetchone()[0]
    resultado["quantidade_codigos_municipio"] = conexao.execute(f"SELECT count(DISTINCT co_municipio) FROM {prefixo}dim_municipio").fetchone()[0]
    resultado["ano_minimo"], resultado["ano_maximo"] = conexao.execute(f"SELECT min(ano),max(ano) FROM {prefixo}fato_rendimento_escolar").fetchone()
    return resultado


def publicar(conexao, id_execucao, contagens, validacoes):
    """Chamador mantém todos os DELETE/INSERT/validações/controle na mesma transação."""
    for tabela in reversed(TABELAS):
        conexao.execute(f"DELETE FROM public.{tabela}")
    for tabela in TABELAS:
        campos = ",".join(COLUNAS[tabela])
        conexao.execute(f"INSERT INTO public.{tabela} ({campos}) SELECT {campos} FROM stg_{tabela}")
        iguais = " AND ".join(f"p.{c}=s.{c}" for c in CHAVES[tabela])
        diferente = " OR ".join(f"p.{c} IS DISTINCT FROM s.{c}" for c in COLUNAS[tabela])
        exigir_zero(conexao, f"SELECT count(*) FROM public.{tabela} p FULL JOIN stg_{tabela} s ON {iguais} WHERE {diferente}",
                    "conteudo_publicado_" + tabela, validacoes)
    observado = contagens_banco(conexao)
    if observado != contagens:
        raise ErroPersistencia("Contagens definitivas divergem da staging.")
    validacoes["postgresql"] = observado
    conexao.execute("UPDATE public.controle_carga SET carga_ativa=false WHERE carga_ativa")
    conexao.execute("""UPDATE public.controle_carga SET status='sucesso', carga_ativa=true, fim=clock_timestamp(),
        quantidade_linhas=%s,quantidade_escolas=%s,quantidade_municipios=%s,
        quantidade_codigos_escola=%s,quantidade_codigos_municipio=%s,quantidade_metricas_catalogo=%s,
        validacoes=%s WHERE id_execucao=%s""", tuple(contagens[c] for c in (
            "quantidade_linhas", "quantidade_escolas", "quantidade_municipios", "quantidade_codigos_escola",
            "quantidade_codigos_municipio", "quantidade_metricas_catalogo")) + (Jsonb(validacoes), id_execucao))


def erro_seguro(erro):
    if isinstance(erro, psycopg.Error):
        return f"PostgreSQL: {type(erro).__name__}; SQLSTATE={erro.sqlstate or 'indisponível'}. Confira conexão, permissões e constraints."
    if isinstance(erro, ErroPersistencia):
        return str(erro)
    if isinstance(erro, PermissionError):
        return "Acesso negado a um produto/relatório local. Execute com acesso aos arquivos da Etapa 5."
    return f"Falha {type(erro).__name__} durante a persistência; publicação anterior preservada se não houve COMMIT."


def executar_persistencia(origem=DASHBOARD_DIR, relatorios=RELATORIOS_DIR, arquivo_env=None):
    inicio = datetime.now(timezone.utc)
    cronometro = time.perf_counter()
    identificador = uuid.uuid4()
    resultado = {"id_execucao": str(identificador), "status": "em_execucao", "inicio": inicio.isoformat(),
                 "validacoes": {}, "divergencias": [], "versao_pipeline": VERSAO, **identidade_git()}
    conexao, registrado, confirmado = None, False, False
    try:
        config = configuracao(arquivo_env)
        with tempfile.TemporaryDirectory(prefix="inep-etapa6-") as pasta:
            captura = Path(pasta)
            manifesto = capturar_origem(origem, captura, relatorios)
            resultado["manifesto_origem"] = manifesto
            conexao = psycopg.connect(**config, autocommit=True)
            if conexao.execute("SELECT current_database(),current_user").fetchone() != (config["dbname"], config["user"]):
                raise ErroPersistencia("Identidade do banco/usuário difere da configuração.")
            if not conexao.execute("SELECT pg_try_advisory_lock(%s)", (LOCK,)).fetchone()[0]:
                raise ErroPersistencia("Outra carga está em execução; aguarde seu término.")
            with conexao.transaction():
                conexao.execute("UPDATE public.controle_carga SET status='interrompida',fim=clock_timestamp(),mensagem_erro='Execução anterior abandonada; lock obtido por nova sessão.' WHERE status='em_execucao'")
                conexao.execute("""INSERT INTO public.controle_carga
                    (id_execucao,inicio,status,carga_ativa,versao_pipeline,commit_pipeline,codigo_modificado,manifesto_origem)
                    VALUES (%s,%s,'em_execucao',false,%s,%s,%s,%s)""",
                    (identificador, inicio, VERSAO, resultado["commit_pipeline"], resultado["codigo_modificado"], Jsonb(manifesto)))
            registrado = True
            with conexao.transaction():
                criar_staging(conexao)
                fontes = {"dim_municipio": [captura / "dim_municipios.parquet"],
                          "dim_escola": [captura / "dim_escolas.parquet"],
                          "catalogo_metricas": [captura / "dim_metricas.parquet"],
                          "fato_rendimento_escolar": sorted((captura / "taxas").rglob("*.parquet"))}
                resultado["validacoes"]["transferencia"] = {t: carregar_parquet(conexao, t, fontes[t]) for t in TABELAS}
                contagens = validar_staging(conexao, manifesto, resultado["validacoes"])
            LOGGER.info("Staging validada; iniciando publicação transacional.")
            with conexao.transaction():
                publicar(conexao, identificador, contagens, resultado["validacoes"])
            confirmado = True
            resultado.update(status="sucesso", **contagens)
            resultado["controle_carga"] = {"id_execucao": str(identificador), "status": "sucesso", "carga_ativa": True}
    except Exception as erro:
        resultado.update(status="falha", mensagem_erro=erro_seguro(erro))
        if registrado:
            try:
                # Nova conexão resolve também perda de resposta ao COMMIT; lock espera a sessão anterior encerrar.
                if conexao:
                    conexao.close()
                with psycopg.connect(**config, autocommit=True) as recuperacao:
                    recuperacao.execute("SELECT pg_advisory_lock(%s)", (LOCK,))
                    estado = recuperacao.execute("SELECT status,validacoes FROM public.controle_carga WHERE id_execucao=%s", (identificador,)).fetchone()
                    if estado and estado[0] == "sucesso":
                        confirmado = True
                        resultado.update(status="sucesso", validacoes=estado[1], aviso="COMMIT confirmado por reconciliação.")
                        resultado.update(estado[1]["postgresql"])
                        resultado.pop("mensagem_erro", None)
                        resultado["controle_carga"] = {"id_execucao": str(identificador), "status": "sucesso", "carga_ativa": "consultar banco"}
                    else:
                        recuperacao.execute("UPDATE public.controle_carga SET status='falha',fim=clock_timestamp(),validacoes=%s,mensagem_erro=%s WHERE id_execucao=%s AND status='em_execucao'",
                                            (Jsonb(resultado["validacoes"]), resultado["mensagem_erro"], identificador))
            except Exception:
                resultado.update(status="indeterminado", mensagem_erro="Não foi possível reconciliar o controle; consulte o UUID no banco antes de repetir a carga.")
        if resultado["status"] != "sucesso":
            resultado["divergencias"].append(resultado.get("mensagem_erro", ""))
    finally:
        if conexao:
            conexao.close()
        resultado.update(fim=datetime.now(timezone.utc).isoformat(), duracao_segundos=round(time.perf_counter() - cronometro, 3),
                         commit_confirmado=confirmado)
        destino = Path(relatorios)
        destino.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(resultado, ensure_ascii=False, indent=2, default=str)
        (destino / f"persistencia_{identificador}.json").write_text(texto, encoding="utf-8")
        (destino / "relatorio_persistencia_postgresql.json").write_text(texto, encoding="utf-8")
    return resultado
