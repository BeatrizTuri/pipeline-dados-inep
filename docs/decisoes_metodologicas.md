# Decisões metodológicas

## 2026-05-14 - Etapa 1: descoberta de arquivos brutos

- A pipeline preserva `data/raw/` como área somente de entrada. A Etapa 1 apenas lê os caminhos e não move, edita ou sobrescreve arquivos brutos.
- A descoberta usa `pathlib` e busca recursiva em `data/raw/taxas_rendimento_escolar/`, porque os arquivos do INEP podem estar dentro de subpastas extraídas.
- Nesta etapa, apenas arquivos `.xlsx` e `.xls` são candidatos a processamento futuro.
- Arquivos auxiliares como `.txt`, `.md5`, `.ods`, `.pdf` e `.zip` são ignorados no inventário inicial.
- Um arquivo é considerado relevante quando o caminho indica rendimento escolar por escola, usando a presença de termos relacionados a `rend` e `escola`.
- O ano é extraído por padrão numérico de quatro dígitos no nome ou caminho do arquivo. Quando não for encontrado, o registro entra no inventário com status de aviso.
- A saída da etapa é um inventário em `outputs/relatorios/inventario_arquivos.csv`, com caminhos relativos ao repositório, mantendo rastreabilidade sem iniciar ingestão nem limpeza.

## 2026-05-19 - Etapa 2: ingestão dos arquivos Excel

- A ingestão usa o inventário da Etapa 1 como fonte dos arquivos a serem lidos.
- A pipeline tenta usar preferencialmente a aba `ESCOLAS`. Quando ela não existe, usa uma aba com termo relacionado a escola; se também não existir, usa a primeira aba disponível e registra a decisão no relatório.
- A linha de cabeçalho é detectada automaticamente por pontuação simples, procurando colunas de identificação e prefixos de taxas (`tap_`, `tre_`, `tab_`).
- Os dados são carregados como texto (`dtype=str`) para evitar perda de códigos de município ou escola antes da etapa de limpeza.
- A Etapa 2 não faz limpeza pesada, padronização, consolidação histórica nem cálculo de indicador.
- O resultado da etapa é um relatório de ingestão em `outputs/relatorios/relatorio_ingestao.csv`.
