from pathlib import Path

from src.pipeline.config import (
    INVENTARIO_ARQUIVOS,
    PROJECT_ROOT,
    RAW_TAXAS_RENDIMENTO_DIR,
    RELATORIO_INGESTAO,
)
from src.pipeline.descoberta_arquivos import gerar_inventario_arquivos
from src.pipeline.ingestao import gerar_relatorio_ingestao


def caminho_relativo(caminho: Path) -> Path:
    return caminho.resolve().relative_to(PROJECT_ROOT)


def main() -> None:
    registros = gerar_inventario_arquivos()
    total_ok = sum(1 for registro in registros if registro["status"] == "ok")
    total_avisos = sum(1 for registro in registros if registro["status"] == "aviso")
    total_erros = sum(1 for registro in registros if registro["status"] == "erro")

    print("Etapa 1 - Configuração e descoberta de arquivos")
    print(f"Diretório pesquisado: {caminho_relativo(RAW_TAXAS_RENDIMENTO_DIR)}")
    print(f"Inventário gerado: {caminho_relativo(INVENTARIO_ARQUIVOS)}")
    print(f"Arquivos relevantes: {total_ok}")
    print(f"Avisos: {total_avisos}")
    print(f"Erros: {total_erros}")

    relatorio_ingestao = gerar_relatorio_ingestao()
    total_ingestao_ok = sum(1 for registro in relatorio_ingestao if registro["status"] == "ok")
    total_ingestao_erros = sum(1 for registro in relatorio_ingestao if registro["status"] == "erro")

    print()
    print("Etapa 2 - Ingestão dos arquivos Excel")
    print(f"Relatório gerado: {caminho_relativo(RELATORIO_INGESTAO)}")
    print(f"Arquivos lidos com sucesso: {total_ingestao_ok}")
    print(f"Erros de leitura: {total_ingestao_erros}")


if __name__ == "__main__":
    main()
