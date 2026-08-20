import csv
from pathlib import Path

import pandas as pd

from src.pipeline.config import (
    INVENTARIO_ARQUIVOS,
    RELATORIO_AUDITORIA,
    RELATORIO_AUDITORIA_ABAS,
)
from src.pipeline.ingestao import (
    PREFIXOS_TAXAS,
    carregar_inventario,
    caminho_absoluto,
    detectar_linha_cabecalho,
    detectar_dimensoes_planilha,
    escolher_aba,
    normalizar_texto,
)


ABAS_REGIONAIS = {
    "norte",
    "nordeste",
    "sudeste",
    "sul",
    "centro-oeste",
    "centro oeste",
    "centro_oeste",
}

COLUNAS_IDENTIFICACAO_ALIASES = {
    "ano": {"ano", "nu_ano_censo"},
    "no_regiao": {"no_regiao", "regiao"},
    "sg_uf": {"sg_uf", "uf"},
    "co_municipio": {"co_municipio", "codigo_do_municipio"},
    "no_municipio": {"no_municipio", "nome_do_municipio"},
    "co_entidade": {"co_entidade", "codigo_da_escola"},
    "no_entidade": {"no_entidade", "nome_da_escola"},
    "tipoloca": {"tipoloca", "localizacao", "no_categoria"},
    "dependad": {"dependad", "rede", "dependencia_administrativa", "no_dependencia"},
}


def normalizar_coluna(coluna: object) -> str:
    return normalizar_texto(coluna).replace(" ", "_")


def listar_colunas_planilha(caminho: Path, aba: str, linha_cabecalho: int) -> list[str]:
    if caminho.suffix.lower() == ".xls":
        import xlrd

        workbook = xlrd.open_workbook(caminho, on_demand=True)
        try:
            planilha = workbook.sheet_by_name(aba)
            colunas = planilha.row_values(linha_cabecalho)
        finally:
            workbook.release_resources()

        return [normalizar_coluna(coluna) for coluna in colunas if normalizar_coluna(coluna)]

    dados = pd.read_excel(caminho, sheet_name=aba, header=linha_cabecalho, nrows=0, dtype=str)
    return [normalizar_coluna(coluna) for coluna in dados.columns if normalizar_coluna(coluna)]


def identificar_abas_regionais(abas: list[str]) -> list[str]:
    abas_regionais = []
    for aba in abas:
        nome_normalizado = normalizar_texto(aba)
        if any(nome_normalizado.startswith(regiao) for regiao in ABAS_REGIONAIS):
            abas_regionais.append(aba)
    return abas_regionais


def eh_aba_regional(aba: str) -> bool:
    nome_normalizado = normalizar_texto(aba)
    return any(nome_normalizado.startswith(regiao) for regiao in ABAS_REGIONAIS)


def identificar_colunas_referencia(colunas: set[str]) -> tuple[list[str], list[str]]:
    presentes = []
    ausentes = []

    for coluna_referencia, aliases in COLUNAS_IDENTIFICACAO_ALIASES.items():
        if aliases.intersection(colunas):
            presentes.append(coluna_referencia)
        else:
            ausentes.append(coluna_referencia)

    return sorted(presentes), sorted(ausentes)


def eh_coluna_taxa(coluna: str) -> bool:
    if coluna.startswith(PREFIXOS_TAXAS):
        return True
    if coluna.startswith(("1_", "2_", "3_")):
        return True
    termos_taxa = (
        "taxa_de_aprovacao",
        "taxa_de_reprovacao",
        "taxa_de_abandono",
    )
    return any(termo in coluna for termo in termos_taxa)


def auditar_arquivo(registro: dict[str, str]) -> dict[str, str]:
    caminho = caminho_absoluto(registro["caminho"])
    linha_auditoria = {
        "ano": registro.get("ano", ""),
        "nome_arquivo": registro.get("nome_arquivo", ""),
        "caminho": registro.get("caminho", ""),
        "aba_utilizada": "",
        "linha_cabecalho": "",
        "quantidade_abas": "",
        "abas_regionais": "",
        "quantidade_colunas_identificacao": "",
        "colunas_identificacao_ausentes": "",
        "quantidade_colunas_taxas": "",
        "status": "ok",
        "observacao": "",
    }

    try:
        arquivo_excel = pd.ExcelFile(caminho)
        aba, observacao_aba = escolher_aba(arquivo_excel.sheet_names)
        linha_cabecalho, observacao_cabecalho = detectar_linha_cabecalho(caminho, aba)
        colunas = set(listar_colunas_planilha(caminho, aba, linha_cabecalho))
        abas_regionais = identificar_abas_regionais(arquivo_excel.sheet_names)

        colunas_identificacao, colunas_ausentes = identificar_colunas_referencia(colunas)
        colunas_taxas = sorted(coluna for coluna in colunas if eh_coluna_taxa(coluna))

        observacoes = [observacao_aba, observacao_cabecalho]
        status = "ok"

        if colunas_ausentes:
            status = "aviso"
            observacoes.append("Há colunas de identificação ausentes.")

        if not colunas_taxas:
            status = "aviso"
            observacoes.append("Nenhuma coluna de taxa foi identificada.")

        if eh_aba_regional(aba):
            status = "aviso"
            observacoes.append(
                "Arquivo parece estar dividido por abas regionais; a aba utilizada não representa necessariamente o arquivo completo."
            )

        linha_auditoria.update(
            {
                "aba_utilizada": aba,
                "linha_cabecalho": str(linha_cabecalho + 1),
                "quantidade_abas": str(len(arquivo_excel.sheet_names)),
                "abas_regionais": ";".join(abas_regionais),
                "quantidade_colunas_identificacao": str(len(colunas_identificacao)),
                "colunas_identificacao_ausentes": ";".join(colunas_ausentes),
                "quantidade_colunas_taxas": str(len(colunas_taxas)),
                "status": status,
                "observacao": " ".join(observacoes),
            }
        )
    except Exception as erro:
        linha_auditoria["status"] = "erro"
        linha_auditoria["observacao"] = f"Falha ao auditar arquivo: {erro}"

    return linha_auditoria


def auditar_aba(registro: dict[str, str], aba: str) -> dict[str, str]:
    caminho = caminho_absoluto(registro["caminho"])
    linha_auditoria = {
        "ano": registro.get("ano", ""),
        "nome_arquivo": registro.get("nome_arquivo", ""),
        "caminho": registro.get("caminho", ""),
        "aba": aba,
        "tipo_aba": "regional" if eh_aba_regional(aba) else "principal",
        "linha_cabecalho": "",
        "quantidade_linhas": "",
        "quantidade_colunas": "",
        "quantidade_colunas_identificacao": "",
        "colunas_identificacao_ausentes": "",
        "quantidade_colunas_taxas": "",
        "status": "ok",
        "observacao": "",
    }

    try:
        linha_cabecalho, observacao_cabecalho = detectar_linha_cabecalho(caminho, aba)
        total_linhas, total_colunas = detectar_dimensoes_planilha(caminho, aba)
        linhas_dados = max(total_linhas - linha_cabecalho - 1, 0)
        colunas = set(listar_colunas_planilha(caminho, aba, linha_cabecalho))
        colunas_identificacao, colunas_ausentes = identificar_colunas_referencia(colunas)
        colunas_taxas = sorted(coluna for coluna in colunas if eh_coluna_taxa(coluna))

        observacoes = [observacao_cabecalho]
        status = "ok"

        if linhas_dados == 0:
            status = "aviso"
            observacoes.append("Aba sem linhas de dados.")

        if colunas_ausentes:
            status = "aviso"
            observacoes.append("Há colunas de identificação ausentes.")

        if not colunas_taxas:
            status = "aviso"
            observacoes.append("Nenhuma coluna de taxa foi identificada.")

        linha_auditoria.update(
            {
                "linha_cabecalho": str(linha_cabecalho + 1),
                "quantidade_linhas": str(linhas_dados),
                "quantidade_colunas": str(total_colunas),
                "quantidade_colunas_identificacao": str(len(colunas_identificacao)),
                "colunas_identificacao_ausentes": ";".join(colunas_ausentes),
                "quantidade_colunas_taxas": str(len(colunas_taxas)),
                "status": status,
                "observacao": " ".join(observacoes),
            }
        )
    except Exception as erro:
        linha_auditoria["status"] = "erro"
        linha_auditoria["observacao"] = f"Falha ao auditar aba: {erro}"

    return linha_auditoria


def auditar_abas_arquivo(registro: dict[str, str]) -> list[dict[str, str]]:
    caminho = caminho_absoluto(registro["caminho"])
    arquivo_excel = pd.ExcelFile(caminho)

    abas_regionais = identificar_abas_regionais(arquivo_excel.sheet_names)
    abas_para_auditar = abas_regionais or arquivo_excel.sheet_names

    return [auditar_aba(registro, aba) for aba in abas_para_auditar]


def gerar_relatorio_auditoria(
    caminho_inventario: Path = INVENTARIO_ARQUIVOS,
    caminho_saida: Path = RELATORIO_AUDITORIA,
) -> list[dict[str, str]]:
    registros = carregar_inventario(caminho_inventario)
    relatorio = []

    for registro in registros:
        if registro.get("status") != "ok":
            continue
        relatorio.append(auditar_arquivo(registro))

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    colunas = [
        "ano",
        "nome_arquivo",
        "caminho",
        "aba_utilizada",
        "linha_cabecalho",
        "quantidade_abas",
        "abas_regionais",
        "quantidade_colunas_identificacao",
        "colunas_identificacao_ausentes",
        "quantidade_colunas_taxas",
        "status",
        "observacao",
    ]

    with caminho_saida.open("w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(relatorio)

    return relatorio


def gerar_relatorio_auditoria_abas(
    caminho_inventario: Path = INVENTARIO_ARQUIVOS,
    caminho_saida: Path = RELATORIO_AUDITORIA_ABAS,
) -> list[dict[str, str]]:
    registros = carregar_inventario(caminho_inventario)
    relatorio = []

    for registro in registros:
        if registro.get("status") != "ok":
            continue

        try:
            relatorio.extend(auditar_abas_arquivo(registro))
        except Exception as erro:
            relatorio.append(
                {
                    "ano": registro.get("ano", ""),
                    "nome_arquivo": registro.get("nome_arquivo", ""),
                    "caminho": registro.get("caminho", ""),
                    "aba": "",
                    "tipo_aba": "",
                    "linha_cabecalho": "",
                    "quantidade_linhas": "",
                    "quantidade_colunas": "",
                    "quantidade_colunas_identificacao": "",
                    "colunas_identificacao_ausentes": "",
                    "quantidade_colunas_taxas": "",
                    "status": "erro",
                    "observacao": f"Falha ao listar abas do arquivo: {erro}",
                }
            )

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    colunas = [
        "ano",
        "nome_arquivo",
        "caminho",
        "aba",
        "tipo_aba",
        "linha_cabecalho",
        "quantidade_linhas",
        "quantidade_colunas",
        "quantidade_colunas_identificacao",
        "colunas_identificacao_ausentes",
        "quantidade_colunas_taxas",
        "status",
        "observacao",
    ]

    with caminho_saida.open("w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(relatorio)

    return relatorio
