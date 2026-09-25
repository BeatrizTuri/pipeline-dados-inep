from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_TAXAS_RENDIMENTO_DIR = RAW_DIR / "taxas_rendimento_escolar"
INTERIM_DIR = DATA_DIR / "interim"
INTERIM_TAXAS_RENDIMENTO_DIR = INTERIM_DIR / "taxas_rendimento_escolar_padronizada"
PROCESSED_DIR = DATA_DIR / "processed"
BASE_TAXAS_RENDIMENTO_CONSOLIDADA = PROCESSED_DIR / "taxas_rendimento_escolar_consolidada.parquet"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RELATORIOS_DIR = OUTPUTS_DIR / "relatorios"
INVENTARIO_ARQUIVOS = RELATORIOS_DIR / "inventario_arquivos.csv"
RELATORIO_INGESTAO = RELATORIOS_DIR / "relatorio_ingestao.csv"
RELATORIO_AUDITORIA = RELATORIOS_DIR / "relatorio_auditoria.csv"
RELATORIO_AUDITORIA_ABAS = RELATORIOS_DIR / "relatorio_auditoria_abas.csv"
RELATORIO_LIMPEZA = RELATORIOS_DIR / "relatorio_limpeza.csv"
RELATORIO_CONSOLIDACAO = RELATORIOS_DIR / "relatorio_consolidacao.csv"

DASHBOARD_DIR = PROCESSED_DIR / "dashboard"
SCHEMA_CONSOLIDACAO = RELATORIOS_DIR / "schema_consolidacao.json"
TAMANHO_LOTE = 16_384
COMPRESSAO_PARQUET = "snappy"
UF_VALIDAS = frozenset("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())
TAXA_MINIMA = 0.0
TAXA_MAXIMA = 100.0
