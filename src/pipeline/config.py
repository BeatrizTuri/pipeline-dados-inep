from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_TAXAS_RENDIMENTO_DIR = RAW_DIR / "taxas_rendimento_escolar"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RELATORIOS_DIR = OUTPUTS_DIR / "relatorios"
MANIFESTO_ARQUIVOS = RELATORIOS_DIR / "manifesto_arquivos.csv"
