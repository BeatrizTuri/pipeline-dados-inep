from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_TAXAS_RENDIMENTO_DIR = RAW_DIR / "taxas_rendimento_escolar"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RELATORIOS_DIR = OUTPUTS_DIR / "relatorios"
INVENTARIO_ARQUIVOS = RELATORIOS_DIR / "inventario_arquivos.csv"
RELATORIO_INGESTAO = RELATORIOS_DIR / "relatorio_ingestao.csv"
