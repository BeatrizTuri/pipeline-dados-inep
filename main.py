from src.pipeline.config import MANIFESTO_ARQUIVOS, PROJECT_ROOT, RAW_TAXAS_RENDIMENTO_DIR
from src.pipeline.descoberta_arquivos import gerar_manifesto_arquivos


def caminho_relativo(caminho):
    return caminho.resolve().relative_to(PROJECT_ROOT)


def main() -> None:
    registros = gerar_manifesto_arquivos()
    total_ok = sum(1 for registro in registros if registro["status"] == "ok")
    total_avisos = sum(1 for registro in registros if registro["status"] == "aviso")
    total_erros = sum(1 for registro in registros if registro["status"] == "erro")

    print("Etapa 1 - Configuração e descoberta de arquivos")
    print(f"Diretório pesquisado: {caminho_relativo(RAW_TAXAS_RENDIMENTO_DIR)}")
    print(f"Manifesto gerado: {caminho_relativo(MANIFESTO_ARQUIVOS)}")
    print(f"Arquivos relevantes: {total_ok}")
    print(f"Avisos: {total_avisos}")
    print(f"Erros: {total_erros}")


if __name__ == "__main__":
    main()
