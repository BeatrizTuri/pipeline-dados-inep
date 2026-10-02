"""Camada wide escolar e catálogos de filtros, derivados da base histórica."""

import hashlib
import json
import logging
import sqlite3
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.pipeline.config import COMPRESSAO_PARQUET, TAMANHO_LOTE
from src.pipeline.metricas import COLUNAS_METRICAS, dimensao_metricas, mapa_metricas
from src.pipeline.validacao_consolidacao import IDENTIFICACAO, mascara_taxas_invalidas

LOGGER = logging.getLogger(__name__)
ATRIBUTOS_MUNICIPIO = ["co_municipio", "no_municipio", "sg_uf", "no_regiao"]
ATRIBUTOS_ESCOLA = ["co_entidade", "no_entidade"] + ATRIBUTOS_MUNICIPIO + ["tipoloca", "dependad"]
SCHEMA_ANALITICO = pa.schema(
    [(c, pa.string()) for c in IDENTIFICACAO if c != "ano"]
    + [("id_escola", pa.string()), ("id_municipio", pa.string())]
    + [(c, pa.float64()) for c in COLUNAS_METRICAS])


def registrar_dimensao(dados: pd.DataFrame, colunas: list[str], nome: str,
                      conexao: sqlite3.Connection) -> list[str | None]:
    """Chave de versão estável pelo conteúdo; deduplicação em disco."""
    linhas = dados[colunas].astype(object).where(dados[colunas].notna(), None)
    ids, registros = [], []
    for valores in linhas.itertuples(index=False, name=None):
        if valores[0] is None:
            ids.append(None)
            continue
        conteudo = json.dumps(valores, ensure_ascii=False, separators=(",", ":"))
        chave = hashlib.sha256(conteudo.encode()).hexdigest()
        ids.append(chave)
        registros.append((chave, *valores))
    placeholders = ",".join("?" for _ in range(len(colunas) + 1))
    conexao.executemany(f"INSERT OR IGNORE INTO {nome} VALUES ({placeholders})", registros)
    return ids


def transformar_lote(dados: pd.DataFrame, ano: int, colunas_origem: list[str]) -> pd.DataFrame:
    """Harmoniza apenas aliases disponíveis no arquivo daquele ano."""
    dados = dados.loc[dados.co_entidade.notna()].reset_index(drop=True)
    saida = dados[IDENTIFICACAO[1:]].copy()
    saida["dependad"] = saida.dependad.replace({"Particular": "Privada"})
    mapa = mapa_metricas(ano)
    for destino in COLUNAS_METRICAS:
        origens = [c for c in colunas_origem if mapa.get(c) == destino]
        if len(origens) > 1:
            raise ValueError(f"Aliases conflitantes para {destino} em {ano}.")
        saida[destino] = dados[origens[0]] if origens else float("nan")
    saida[COLUNAS_METRICAS] = saida[COLUNAS_METRICAS].mask(mascara_taxas_invalidas(saida[COLUNAS_METRICAS]))
    return saida


def exportar_dimensao(conexao: sqlite3.Connection, nome: str, colunas: list[str], destino: Path) -> None:
    schema = pa.schema([(f"id_{nome}", pa.string())] + [(c, pa.string()) for c in colunas])
    with pq.ParquetWriter(destino, schema, compression=COMPRESSAO_PARQUET) as escritor:
        for lote in pd.read_sql_query(f"SELECT * FROM {nome} ORDER BY id_{nome}", conexao, chunksize=TAMANHO_LOTE):
            escritor.write_table(pa.Table.from_pandas(lote, schema=schema, preserve_index=False))


def validar_relacionamentos(destino: Path) -> None:
    """Confere os Parquets fechados antes da publicação, sem carregar a fato inteira."""
    for nome, codigo in (("escola", "co_entidade"), ("municipio", "co_municipio")):
        chave = f"id_{nome}"
        dimensao = pq.ParquetFile(destino / f"dim_{nome}s.parquet").read(columns=[chave, codigo]).to_pandas()
        if dimensao[chave].isna().any() or not dimensao[chave].is_unique or dimensao[codigo].isna().any():
            raise ValueError(f"Dimensão {nome}: chave nula/duplicada ou código ausente.")
        codigos = dict(zip(dimensao[chave], dimensao[codigo], strict=True))
        for arquivo in sorted((destino / "taxas").rglob("*.parquet")):
            for lote in pq.ParquetFile(arquivo).iter_batches(batch_size=TAMANHO_LOTE, columns=[chave, codigo]):
                dados = lote.to_pandas()
                ids, origem = dados[chave], dados[codigo]
                if (nome == "escola" and ids.isna().any()) or not ids.isna().equals(origem.isna()):
                    raise ValueError(f"Referência nula inconsistente: {chave} em {arquivo.parent.name}.")
                presentes = ids.notna()
                for identificador, valor in dados.loc[presentes].itertuples(index=False, name=None):
                    if identificador not in codigos:
                        raise ValueError(f"Referência inválida: {chave} em {arquivo.parent.name}.")
                    if codigos[identificador] != valor:
                        raise ValueError(f"Código divergente da dimensão: {chave} em {arquivo.parent.name}.")


def gerar_camada_analitica(historico: Path, destino: Path,
                          colunas_por_ano: dict[int, list[str]]) -> dict[int, int]:
    """Lê o histórico uma vez e escreve um arquivo por ano, sem melt."""
    destino.mkdir(parents=True, exist_ok=True)
    banco = destino / "dimensoes.sqlite"
    escritores: dict[int, pq.ParquetWriter] = {}
    contagens = {ano: 0 for ano in colunas_por_ano}
    anos_iniciados: set[int] = set()
    conexao = sqlite3.connect(banco)
    try:
        for nome, cols in (("escola", ATRIBUTOS_ESCOLA), ("municipio", ATRIBUTOS_MUNICIPIO)):
            campos = ", ".join(f"{c} TEXT" for c in cols)
            conexao.execute(f"CREATE TABLE {nome} (id_{nome} TEXT PRIMARY KEY, {campos})")
        for ano in colunas_por_ano:
            pasta = destino / "taxas" / f"ano={ano}"
            pasta.mkdir(parents=True)
            escritores[ano] = pq.ParquetWriter(pasta / "taxas.parquet", SCHEMA_ANALITICO, compression=COMPRESSAO_PARQUET)
        colunas = sorted(set(IDENTIFICACAO).union(*(set(mapa_metricas(a)).intersection(cols)
                                                for a, cols in colunas_por_ano.items())))
        for lote in pq.ParquetFile(historico).iter_batches(batch_size=TAMANHO_LOTE, columns=colunas):
            for ano, dados in lote.to_pandas().groupby("ano"):
                ano = int(ano)
                if ano not in anos_iniciados:
                    LOGGER.info("Preparando camada analítica do ano %s", ano)
                    anos_iniciados.add(ano)
                saida = transformar_lote(dados, ano, colunas_por_ano[ano])
                saida["id_escola"] = registrar_dimensao(saida, ATRIBUTOS_ESCOLA, "escola", conexao)
                saida["id_municipio"] = registrar_dimensao(saida, ATRIBUTOS_MUNICIPIO, "municipio", conexao)
                escritores[ano].write_table(pa.Table.from_pandas(saida, schema=SCHEMA_ANALITICO, preserve_index=False))
                contagens[ano] += len(saida)
        conexao.commit()
        LOGGER.info("Exportando dimensões de escolas, municípios e métricas")
        exportar_dimensao(conexao, "escola", ATRIBUTOS_ESCOLA, destino / "dim_escolas.parquet")
        exportar_dimensao(conexao, "municipio", ATRIBUTOS_MUNICIPIO, destino / "dim_municipios.parquet")
        dimensao_metricas().to_parquet(destino / "dim_metricas.parquet", index=False)
    finally:
        for escritor in escritores.values():
            escritor.close()
        conexao.close()
        banco.unlink(missing_ok=True)
    return contagens
