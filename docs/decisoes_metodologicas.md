# Decisões metodológicas

## 2026-05-14 - Etapa 1: descoberta de arquivos brutos

- A pipeline preserva `data/raw/` como área somente de entrada. A Etapa 1 apenas lê os caminhos e não move, edita ou sobrescreve arquivos brutos.
- A descoberta usa `pathlib` e busca recursiva em `data/raw/taxas_rendimento_escolar/`, porque os arquivos do INEP podem estar dentro de subpastas extraídas.
- Nesta etapa, apenas arquivos `.xlsx` e `.xls` são candidatos a processamento futuro.
- Arquivos auxiliares como `.txt`, `.md5`, `.ods`, `.pdf` e `.zip` são ignorados no manifesto inicial.
- Um arquivo é considerado relevante quando o caminho indica rendimento escolar por escola, usando a presença de termos relacionados a `rend` e `escola`.
- O ano é extraído por padrão numérico de quatro dígitos no nome ou caminho do arquivo. Quando não for encontrado, o registro entra no manifesto com status de aviso.
- A saída da etapa é um manifesto em `outputs/relatorios/manifesto_arquivos.csv`, com caminhos relativos ao repositório, mantendo rastreabilidade sem iniciar ingestão nem limpeza.
