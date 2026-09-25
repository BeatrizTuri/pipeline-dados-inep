import argparse
import logging
from pathlib import Path

from src.pipeline.config import (
    BASE_TAXAS_RENDIMENTO_CONSOLIDADA,
    DASHBOARD_DIR,
    INVENTARIO_ARQUIVOS,
    PROJECT_ROOT,
    RAW_TAXAS_RENDIMENTO_DIR,
    RELATORIO_AUDITORIA,
    RELATORIO_AUDITORIA_ABAS,
    RELATORIO_CONSOLIDACAO,
    RELATORIO_INGESTAO,
    RELATORIO_LIMPEZA,
)
from src.pipeline.auditoria import gerar_relatorio_auditoria, gerar_relatorio_auditoria_abas
from src.pipeline.consolidacao import gerar_base_consolidada
from src.pipeline.descoberta_arquivos import gerar_inventario_arquivos
from src.pipeline.ingestao import gerar_relatorio_ingestao
from src.pipeline.limpeza import gerar_base_padronizada


def caminho_relativo(caminho: Path) -> Path:
    return caminho.resolve().relative_to(PROJECT_ROOT)


def executar_etapas_iniciais() -> None:
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

    relatorio_auditoria = gerar_relatorio_auditoria()
    relatorio_auditoria_abas = gerar_relatorio_auditoria_abas()
    total_auditoria_ok = sum(1 for registro in relatorio_auditoria if registro["status"] == "ok")
    total_auditoria_avisos = sum(1 for registro in relatorio_auditoria if registro["status"] == "aviso")
    total_auditoria_erros = sum(1 for registro in relatorio_auditoria if registro["status"] == "erro")
    total_abas_regionais = sum(
        1 for registro in relatorio_auditoria_abas if registro["tipo_aba"] == "regional"
    )

    print()
    print("Etapa 3 - Auditoria estrutural dos arquivos")
    print(f"Relatório gerado: {caminho_relativo(RELATORIO_AUDITORIA)}")
    print(f"Auditoria por aba gerada: {caminho_relativo(RELATORIO_AUDITORIA_ABAS)}")
    print(f"Arquivos sem apontamentos: {total_auditoria_ok}")
    print(f"Avisos: {total_auditoria_avisos}")
    print(f"Erros de auditoria: {total_auditoria_erros}")
    print(f"Abas auditadas: {len(relatorio_auditoria_abas)}")
    print(f"Abas regionais auditadas: {total_abas_regionais}")

    relatorio_limpeza = gerar_base_padronizada()
    total_limpeza_ok = sum(1 for registro in relatorio_limpeza if registro["status"] == "ok")
    total_limpeza_erros = sum(1 for registro in relatorio_limpeza if registro["status"] == "erro")
    total_linhas_padronizadas = sum(
        int(registro["quantidade_linhas"] or 0)
        for registro in relatorio_limpeza
        if registro["status"] == "ok"
    )

    print()
    print("Etapa 4 - Limpeza e padronização")
    print(f"Relatório gerado: {caminho_relativo(RELATORIO_LIMPEZA)}")
    print(f"Arquivos padronizados: {total_limpeza_ok}")
    print(f"Erros de padronização: {total_limpeza_erros}")
    print(f"Linhas padronizadas: {total_linhas_padronizadas}")


def executar_etapa_5() -> bool:
    relatorio_consolidacao = gerar_base_consolidada()
    registros_anuais = [registro for registro in relatorio_consolidacao if registro["ano"] != "TOTAL"]
    registro_total = next(
        (registro for registro in relatorio_consolidacao if registro["ano"] == "TOTAL"),
        {},
    )
    total_consolidacao_ok = sum(1 for registro in registros_anuais if registro["status"] == "ok")
    total_consolidacao_avisos = sum(1 for registro in registros_anuais if registro["status"] == "aviso")
    total_consolidacao_erros = sum(1 for registro in registros_anuais if registro["status"] == "erro")

    print()
    print("Etapa 5 - Consolidação histórica e preparação da camada analítica")
    print(f"Status: {registro_total.get('status', 'erro')}")
    if registro_total.get("publicado"):
        print(f"Base gerada: {caminho_relativo(BASE_TAXAS_RENDIMENTO_CONSOLIDADA)}")
        print(f"Camada analítica: {caminho_relativo(DASHBOARD_DIR)}")
    else:
        print(f"Saídas não publicadas: {registro_total.get('observacao', '')}")
    print(f"Relatório gerado: {caminho_relativo(RELATORIO_CONSOLIDACAO)}")
    print(f"Anos consolidados sem apontamentos: {total_consolidacao_ok}")
    print(f"Avisos: {total_consolidacao_avisos}")
    print(f"Erros de consolidação: {total_consolidacao_erros}")
    print(f"Linhas de entrada: {registro_total.get('quantidade_linhas_entrada', '0')}")
    print(f"Linhas descartadas: {registro_total.get('quantidade_linhas_descartadas', '0')}")
    print(f"Linhas consolidadas: {registro_total.get('quantidade_linhas_consolidadas', '0')}")
    print(f"Colunas consolidadas: {registro_total.get('quantidade_colunas_consolidadas', '0')}")
    print(f"Linhas analíticas: {registro_total.get('linhas_analiticas', '0')}")
    return registro_total.get("status") != "erro"


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de dados educacionais do INEP")
    parser.add_argument("--etapa", choices=["5"], help="Executa somente a Etapa 5 sobre os Parquets anuais existentes.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.etapa != "5":
        executar_etapas_iniciais()
    if not executar_etapa_5():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
