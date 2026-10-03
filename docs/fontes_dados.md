# Fontes e preparação da entrada

O projeto utiliza os arquivos públicos de **Taxas de Rendimento Escolar em nível de escola**, obtidos manualmente no portal oficial do INEP. O recorte de layouts validado pela pipeline é 2007–2024.

## Organização local

Coloque os arquivos Excel extraídos em `data/raw/taxas_rendimento_escolar/`. A descoberta percorre subpastas e seleciona arquivos `.xls` e `.xlsx` cujo caminho indica rendimento escolar por escola. O ano é identificado pelo primeiro ano encontrado no caminho; preserve nomes e organização que permitam essa identificação.

Arquivos ZIP não são extraídos automaticamente. A pipeline não realiza download, scraping nem modificação dos arquivos brutos. Arquivos auxiliares, como PDF e arquivos de verificação, não são entradas de processamento.

As bases não são distribuídas pelo repositório: `data/raw/`, `data/interim/`, `data/processed/` e `outputs/` são ignorados pelo Git. Quem reproduzir o processamento deverá fornecer os arquivos de entrada.

## Conferência antes da execução

Confira `outputs/relatorios/inventario_arquivos.csv` após a descoberta: ano, caminho, status e observações devem corresponder aos arquivos fornecidos. Os relatórios de ingestão e auditoria registram abas, cabeçalhos e diferenças estruturais. Não presuma que qualquer planilha do INEP possui o layout esperado.

Novos anos ou layouts exigem revisão do catálogo de métricas. O procedimento de execução está no [README](../README.md); as regras de processamento estão na [metodologia](metodologia.md).
