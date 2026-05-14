# Diário técnico

## 2026-05-14 - Etapa 1: configuração e descoberta de arquivos

- Arquivos alterados: `src/pipeline/config.py`, `src/pipeline/descoberta_arquivos.py`, `main.py`, `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`.
- Objetivo: criar a base inicial da pipeline para localizar arquivos brutos relevantes de Taxas de Rendimento Escolar por escola.
- Resultado: implementada descoberta recursiva de arquivos `.xlsx` e `.xls`, ignorando arquivos auxiliares e gerando `outputs/relatorios/manifesto_arquivos.csv`.
- Pendências: validar o manifesto gerado com os arquivos reais disponíveis em `data/raw/taxas_rendimento_escolar/`.
- Próximo passo: após aprovação, iniciar a Etapa 2 de ingestão dos arquivos Excel.
