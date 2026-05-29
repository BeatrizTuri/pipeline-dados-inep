import csv
import re
from pathlib import Path

from src.pipeline.config import INVENTARIO_ARQUIVOS, PROJECT_ROOT, RAW_TAXAS_RENDIMENTO_DIR


EXTENSOES_EXCEL = {".xlsx", ".xls"}
EXTENSOES_IGNORADAS = {".txt", ".md5", ".ods", ".pdf", ".zip"}
PADRAO_ANO = re.compile(r"(?:19|20)\d{2}")


def caminho_relativo(caminho: Path) -> str:
    try:
        return caminho.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return caminho.as_posix()


def extrair_ano(caminho: Path) -> str:
    anos = PADRAO_ANO.findall(caminho.as_posix())
    if not anos:
        return ""
    return anos[-1]


def eh_arquivo_relevante(caminho: Path) -> bool:
    extensao = caminho.suffix.lower()
    if extensao in EXTENSOES_IGNORADAS:
        return False
    if extensao not in EXTENSOES_EXCEL:
        return False

    texto_caminho = caminho.as_posix().lower()
    tem_rendimento = "rend" in texto_caminho
    tem_escola = "escola" in texto_caminho
    return tem_rendimento and tem_escola


def descobrir_arquivos_brutos(diretorio_base: Path = RAW_TAXAS_RENDIMENTO_DIR) -> list[dict[str, str]]:
    if not diretorio_base.exists():
        return [
            {
                "ano": "",
                "nome_arquivo": "",
                "caminho": caminho_relativo(diretorio_base),
                "extensao": "",
                "status": "erro",
                "observacao": "Diretório de dados brutos não encontrado.",
            }
        ]

    registros = []
    for caminho in sorted(diretorio_base.rglob("*")):
        if not caminho.is_file() or not eh_arquivo_relevante(caminho):
            continue

        ano = extrair_ano(caminho)
        registros.append(
            {
                "ano": ano,
                "nome_arquivo": caminho.name,
                "caminho": caminho_relativo(caminho),
                "extensao": caminho.suffix.lower(),
                "status": "ok" if ano else "aviso",
                "observacao": "Ano identificado." if ano else "Ano não identificado no nome ou caminho.",
            }
        )

    if not registros:
        registros.append(
            {
                "ano": "",
                "nome_arquivo": "",
                "caminho": caminho_relativo(diretorio_base),
                "extensao": "",
                "status": "aviso",
                "observacao": "Nenhum arquivo Excel relevante encontrado.",
            }
        )

    return registros


def gerar_inventario_arquivos(
    diretorio_base: Path = RAW_TAXAS_RENDIMENTO_DIR,
    caminho_saida: Path = INVENTARIO_ARQUIVOS,
) -> list[dict[str, str]]:
    registros = descobrir_arquivos_brutos(diretorio_base)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    colunas = ["ano", "nome_arquivo", "caminho", "extensao", "status", "observacao"]
    with caminho_saida.open("w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(registros)

    return registros
