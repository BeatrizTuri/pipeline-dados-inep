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
## 2026-06-08 - Ajuste da Etapa 1 e Etapa 3: auditoria estrutural

- A extração do ano passou a considerar o primeiro ano encontrado no caminho do arquivo, evitando classificar arquivos como `tx_rendimento_escolas_2010_19082011.xls` pelo ano da data de atualização do arquivo.
- A geração do relatório de ingestão passou a coletar dimensões das planilhas sem carregar todas as linhas em memória, mantendo a etapa mais rápida e adequada para arquivos grandes.
- A Etapa 3 foi definida como auditoria estrutural, sem limpeza, padronização, consolidação ou cálculo de indicadores.
- A auditoria verifica abas disponíveis, aba efetivamente usada, linha de cabeçalho, colunas mínimas de identificação, colunas de taxas e arquivos possivelmente divididos por abas regionais.
- Arquivos antigos sem aba `ESCOLAS`, especialmente aqueles organizados por regiões, recebem status de aviso para evitar consolidação histórica incorreta.
- O resultado da etapa é `outputs/relatorios/relatorio_auditoria.csv`.

## 2026-06-08 - Continuação da Etapa 3: auditoria por aba

- A auditoria estrutural passou a gerar também `outputs/relatorios/relatorio_auditoria_abas.csv`, com uma linha por aba auditada.
- Para arquivos com abas regionais, a auditoria por aba avalia todas as abas regionais, não apenas a primeira aba do arquivo.
- Arquivos sem abas regionais continuam sendo auditados por suas abas disponíveis, normalmente a aba `ESCOLAS`.
- Esta decisão ainda não consolida as abas; ela apenas cria evidência para definir a regra de combinação dos anos 2007 a 2011.
- O dicionário de dados inicial foi documentado em `docs/dicionario_dados.md`, registrando campos canônicos, aliases encontrados e famílias de taxas.
