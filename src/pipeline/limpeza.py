import csv
import re
from pathlib import Path

import pandas as pd

from src.pipeline.auditoria import identificar_abas_regionais, normalizar_coluna
from src.pipeline.config import (
    INTERIM_TAXAS_RENDIMENTO_DIR,
    INVENTARIO_ARQUIVOS,
    RELATORIO_LIMPEZA,
)
from src.pipeline.ingestao import (
    carregar_inventario,
    caminho_absoluto,
    detectar_linha_cabecalho,
    escolher_aba,
    normalizar_texto,
)


COLUNAS_IDENTIFICACAO = [
    "ano",
    "no_regiao",
    "sg_uf",
    "co_municipio",
    "no_municipio",
    "co_entidade",
    "no_entidade",
    "tipoloca",
    "dependad",
]

ALIASES_IDENTIFICACAO = {
    "ano": "ano",
    "nu_ano_censo": "ano",
    "regiao": "no_regiao",
    "no_regiao": "no_regiao",
    "uf": "sg_uf",
    "sg_uf": "sg_uf",
    "codigo_do_municipio": "co_municipio",
    "co_municipio": "co_municipio",
    "nome_do_municipio": "no_municipio",
    "no_municipio": "no_municipio",
    "codigo_da_escola": "co_entidade",
    "co_entidade": "co_entidade",
    "nome_da_escola": "no_entidade",
    "no_entidade": "no_entidade",
    "localizacao": "tipoloca",
    "tipoloca": "tipoloca",
    "no_categoria": "tipoloca",
    "rede": "dependad",
    "dependad": "dependad",
    "dependencia_administrativa": "dependad",
    "no_dependencia": "dependad",
}

PREFIXOS_TAXAS_NUMERICOS = {
    "1_cat_": "tap_",
    "2_cat_": "tre_",
    "3_cat_": "tab_",
}

MARCADORES_AUSENTES = {"", "--", "-", "nan", "none", "null"}
PADRAO_ANO = re.compile(r"^(?:19|20)\d{2}$")


def limpar_valor_texto(valor: object) -> object:
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip()
    if normalizar_texto(texto) in MARCADORES_AUSENTES:
        return pd.NA

    return texto


def normalizar_sufixo_taxa(texto: str, indice: int) -> str:
    sufixo = normalizar_coluna(texto)
    sufixo = sufixo.replace("aprovacaona_", "aprovacao_")
    sufixo = sufixo.replace("reprovacaona_", "reprovacao_")
    remover = (
        "taxa_de_",
        "aprovacao_",
        "reprovacao_",
        "abandono_",
        "total_",
        "no_",
        "na_",
        "de_",
        "do_",
        "da_",
    )
    for trecho in remover:
        sufixo = sufixo.replace(trecho, "")

    sufixo = re.sub(r"[^a-z0-9_]+", "_", sufixo)
    sufixo = re.sub(r"_+", "_", sufixo).strip("_")
    return sufixo or f"coluna_{indice:02d}"


def identificar_coluna_taxa(nome_coluna: str, texto_cabecalho: str, indice: int) -> str:
    nome_normalizado = normalizar_coluna(nome_coluna)
    texto_normalizado = normalizar_coluna(texto_cabecalho)

    if nome_normalizado.startswith(("tap_", "tre_", "tab_")):
        return nome_normalizado

    for prefixo_original, prefixo_padronizado in PREFIXOS_TAXAS_NUMERICOS.items():
        if nome_normalizado.startswith(prefixo_original):
            return prefixo_padronizado + nome_normalizado.removeprefix(prefixo_original)

    if "aprovacao" in texto_normalizado:
        return "tap_" + normalizar_sufixo_taxa(texto_cabecalho, indice)
    if "reprovacao" in texto_normalizado:
        return "tre_" + normalizar_sufixo_taxa(texto_cabecalho, indice)
    if "abandono" in texto_normalizado:
        return "tab_" + normalizar_sufixo_taxa(texto_cabecalho, indice)

    return ""


def preencher_cabecalho(valores: list[object]) -> list[str]:
    preenchidos = []
    ultimo_valor = ""

    for valor in valores:
        texto = normalizar_coluna(valor)
        if texto and not texto.startswith("unnamed"):
            ultimo_valor = texto
        preenchidos.append(ultimo_valor)

    return preenchidos


def montar_mapa_colunas(caminho: Path, aba: str, linha_cabecalho: int) -> dict[int, str]:
    previa = pd.read_excel(
        caminho,
        sheet_name=aba,
        header=None,
        nrows=linha_cabecalho + 2,
        dtype=str,
    )
    cabecalho = previa.iloc[linha_cabecalho].tolist()
    subcabecalho = (
        previa.iloc[linha_cabecalho + 1].tolist()
        if linha_cabecalho + 1 < len(previa)
        else []
    )
    cabecalho_preenchido = preencher_cabecalho(cabecalho)

    mapa = {}
    for indice, valor in enumerate(cabecalho):
        nome_coluna = normalizar_coluna(valor)
        nome_padrao = ALIASES_IDENTIFICACAO.get(nome_coluna)
        if nome_padrao:
            mapa[indice] = nome_padrao
            continue

        texto_taxa = nome_coluna
        if indice < len(subcabecalho) and normalizar_coluna(subcabecalho[indice]):
            texto_taxa = normalizar_coluna(subcabecalho[indice])
        elif indice < len(cabecalho_preenchido):
            texto_taxa = cabecalho_preenchido[indice]

        nome_taxa = identificar_coluna_taxa(nome_coluna, texto_taxa, indice)
        if nome_taxa:
            mapa[indice] = nome_taxa

    return mapa


def tornar_colunas_unicas(colunas: list[str]) -> list[str]:
    contadores = {}
    resultado = []

    for coluna in colunas:
        contadores[coluna] = contadores.get(coluna, 0) + 1
        if contadores[coluna] == 1:
            resultado.append(coluna)
        else:
            resultado.append(f"{coluna}_{contadores[coluna]}")

    return resultado


def abas_para_limpeza(caminho: Path) -> list[str]:
    arquivo_excel = pd.ExcelFile(caminho)
    abas_regionais = identificar_abas_regionais(arquivo_excel.sheet_names)
    if abas_regionais:
        return abas_regionais

    aba, _ = escolher_aba(arquivo_excel.sheet_names)
    return [aba]


def carregar_aba_padronizada(registro: dict[str, str], aba: str) -> pd.DataFrame:
    caminho = caminho_absoluto(registro["caminho"])
    linha_cabecalho, _ = detectar_linha_cabecalho(caminho, aba)
    dados = pd.read_excel(caminho, sheet_name=aba, header=linha_cabecalho, dtype=str)
    mapa_colunas = montar_mapa_colunas(caminho, aba, linha_cabecalho)

    colunas_padronizadas = []
    for indice, coluna_original in enumerate(dados.columns):
        colunas_padronizadas.append(mapa_colunas.get(indice, normalizar_coluna(coluna_original)))

    dados.columns = tornar_colunas_unicas(colunas_padronizadas)
    colunas_taxas = [coluna for coluna in dados.columns if coluna.startswith(("tap_", "tre_", "tab_"))]
    colunas_saida = COLUNAS_IDENTIFICACAO + colunas_taxas

    for coluna in COLUNAS_IDENTIFICACAO:
        if coluna not in dados.columns:
            dados[coluna] = pd.NA

    dados = dados[colunas_saida].copy()
    dados["ano"] = dados["ano"].fillna(registro.get("ano", ""))
    dados["fonte_arquivo"] = registro.get("nome_arquivo", "")
    dados["fonte_caminho"] = registro.get("caminho", "")
    dados["fonte_aba"] = aba

    # Remove linhas de cabeçalho auxiliar e observações que aparecem dentro das planilhas.
    dados["ano"] = dados["ano"].map(limpar_valor_texto)
    dados = dados[dados["ano"].astype("string").str.match(PADRAO_ANO, na=False)].copy()

    for coluna in dados.columns:
        dados[coluna] = dados[coluna].map(limpar_valor_texto)

    return dados


def padronizar_arquivo(registro: dict[str, str]) -> tuple[pd.DataFrame, dict[str, str]]:
    caminho = caminho_absoluto(registro["caminho"])
    abas = abas_para_limpeza(caminho)
    partes = [carregar_aba_padronizada(registro, aba) for aba in abas]
    dados = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    colunas_taxas = [coluna for coluna in dados.columns if coluna.startswith(("tap_", "tre_", "tab_"))]

    relatorio = {
        "ano": registro.get("ano", ""),
        "nome_arquivo": registro.get("nome_arquivo", ""),
        "caminho": registro.get("caminho", ""),
        "abas_lidas": ";".join(abas),
        "quantidade_abas_lidas": str(len(abas)),
        "quantidade_linhas": str(len(dados)),
        "quantidade_colunas": str(len(dados.columns)),
        "quantidade_colunas_taxas": str(len(colunas_taxas)),
        "arquivo_saida": "",
        "status": "ok",
        "observacao": "Arquivo padronizado.",
    }
    return dados, relatorio


def relatorio_arquivo_existente(registro: dict[str, str], caminho_saida: Path) -> dict[str, str]:
    import pyarrow.parquet as pq

    arquivo_parquet = pq.ParquetFile(caminho_saida)
    colunas = arquivo_parquet.schema.names
    colunas_taxas = [coluna for coluna in colunas if coluna.startswith(("tap_", "tre_", "tab_"))]
    abas = []

    if "fonte_aba" in colunas:
        abas = sorted(pd.read_parquet(caminho_saida, columns=["fonte_aba"])["fonte_aba"].dropna().unique())

    return {
        "ano": registro.get("ano", ""),
        "nome_arquivo": registro.get("nome_arquivo", ""),
        "caminho": registro.get("caminho", ""),
        "abas_lidas": ";".join(abas),
        "quantidade_abas_lidas": str(len(abas)),
        "quantidade_linhas": str(arquivo_parquet.metadata.num_rows),
        "quantidade_colunas": str(len(colunas)),
        "quantidade_colunas_taxas": str(len(colunas_taxas)),
        "arquivo_saida": caminho_saida.as_posix(),
        "status": "ok",
        "observacao": "Arquivo padronizado existente reutilizado.",
    }


def gerar_base_padronizada(
    caminho_inventario: Path = INVENTARIO_ARQUIVOS,
    diretorio_saida: Path = INTERIM_TAXAS_RENDIMENTO_DIR,
    caminho_relatorio: Path = RELATORIO_LIMPEZA,
    sobrescrever: bool = False,
) -> list[dict[str, str]]:
    registros = carregar_inventario(caminho_inventario)
    relatorio = []
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    for registro in registros:
        if registro.get("status") != "ok":
            continue

        caminho_saida = diretorio_saida / f"taxas_rendimento_{registro.get('ano', '')}.parquet"
        if caminho_saida.exists() and not sobrescrever:
            relatorio.append(relatorio_arquivo_existente(registro, caminho_saida))
            continue

        try:
            dados, linha_relatorio = padronizar_arquivo(registro)
            dados.to_parquet(caminho_saida, index=False)
            linha_relatorio["arquivo_saida"] = caminho_saida.as_posix()
        except Exception as erro:
            linha_relatorio = {
                "ano": registro.get("ano", ""),
                "nome_arquivo": registro.get("nome_arquivo", ""),
                "caminho": registro.get("caminho", ""),
                "abas_lidas": "",
                "quantidade_abas_lidas": "",
                "quantidade_linhas": "",
                "quantidade_colunas": "",
                "quantidade_colunas_taxas": "",
                "arquivo_saida": "",
                "status": "erro",
                "observacao": f"Falha ao padronizar arquivo: {erro}",
            }

        relatorio.append(linha_relatorio)

    caminho_relatorio.parent.mkdir(parents=True, exist_ok=True)
    colunas = [
        "ano",
        "nome_arquivo",
        "caminho",
        "abas_lidas",
        "quantidade_abas_lidas",
        "quantidade_linhas",
        "quantidade_colunas",
        "quantidade_colunas_taxas",
        "arquivo_saida",
        "status",
        "observacao",
    ]

    with caminho_relatorio.open("w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(relatorio)

    return relatorio
