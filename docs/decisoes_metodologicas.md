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

## 2026-06-08 - Fechamento da Etapa 3

- A Etapa 3 fica encerrada como etapa de auditoria estrutural das bases de Taxas de Rendimento Escolar por escola no recorte de 2007 a 2024.
- Os produtos finais da etapa são `outputs/relatorios/relatorio_auditoria.csv`, `outputs/relatorios/relatorio_auditoria_abas.csv` e o dicionário inicial em `docs/dicionario_dados.md`.
- A auditoria confirmou que os arquivos de 2007 a 2011 estão organizados por abas regionais e devem ser tratados com leitura de todas essas abas na etapa posterior.
- A auditoria confirmou variações de nomenclatura entre anos, incluindo campos de identificação e famílias de taxas com padrões diferentes.
- A Etapa 3 não modifica dados brutos, não gera base padronizada, não consolida anos e não calcula indicadores.
- A próxima etapa definida é a Etapa 4: limpeza e padronização, usando os aliases e achados documentados nesta auditoria.

## 2026-08-20 - Etapa 4: limpeza e padronização

- A Etapa 4 lê o inventário validado e gera uma base intermediária padronizada por ano em `data/interim/taxas_rendimento_escolar_padronizada/`.
- Para os anos de 2007 a 2011, todas as abas regionais identificadas pela auditoria são lidas e combinadas dentro do arquivo anual correspondente.
- Para os demais anos, a etapa lê a aba principal escolhida pela regra de ingestão, normalmente `ESCOLAS`.
- Os campos de identificação são renomeados para nomes canônicos, como `co_entidade`, `no_entidade`, `tipoloca` e `dependad`.
- As colunas de taxas são padronizadas por família com os prefixos `tap_`, `tre_` e `tab_`, preservando o formato amplo da base.
- Marcadores textuais de ausência, como `--`, são convertidos para valor ausente na base intermediária.
- A etapa gera `outputs/relatorios/relatorio_limpeza.csv` para registrar linhas, colunas, abas lidas, arquivo de saída e status por ano.
- A Etapa 4 não gera a base histórica única; a consolidação de todos os anos fica definida como responsabilidade da Etapa 5.

## 2026-08-22 - Etapa 5: consolidação histórica

- A Etapa 5 usa os arquivos Parquet anuais padronizados da Etapa 4 como entrada.
- A saída consolidada é `data/processed/taxas_rendimento_escolar_consolidada.parquet`.
- O relatório da etapa é `outputs/relatorios/relatorio_consolidacao.csv`.
- Como as colunas de taxas variam entre períodos, a consolidação usa a união das colunas padronizadas e preenche com valor ausente as colunas não existentes em determinado ano.
- Linhas sem `co_entidade` são descartadas da base consolidada, pois a unidade de análise definida é a escola.
- A base consolidada preserva os campos de rastreabilidade `fonte_arquivo`, `fonte_caminho` e `fonte_aba`.
- A etapa valida quantidade de linhas por ano, quantidade de escolas, abas de origem e duplicidades por `ano + co_entidade`.
- A Etapa 5 não calcula indicadores; análises e indicadores ficam para etapa posterior.

## 2026-09-24 - Mudança de escopo e camada analítica

- A pipeline e a base histórica são a contribuição central do TCC. Um dashboard interativo será a aplicação futura. O índice de vulnerabilidade está suspenso; qualquer indicador derivado dependerá de metodologia validada.
- A Etapa 5 passa a se chamar **Consolidação histórica e preparação da camada analítica**. As etapas 1 a 4 mantêm suas responsabilidades e sua implementação.
- A decisão anterior de descartar linhas sem escola é substituída: todas as linhas anuais permanecem no histórico. As 75 linhas sem escola observadas na entrada são excluídas somente da camada analítica escolar. Textos de taxas dessas linhas são preservados em `taxas_textuais_origem`, pois há cabeçalhos auxiliares entre elas.
- Histórico e camada analítica são wide. Um melt das 207 colunas históricas geraria 535.798.593 linhas incluindo ausentes; mesmo 54 métricas harmonizadas poderiam gerar 139.773.546. A camada wide mantém aproximadamente 2,59 milhões de registros e permite projetar somente as colunas necessárias.
- As correspondências são específicas por período. Os cabeçalhos locais de 2018–2020 associam `f04` a anos finais e `f58` ao 1º ano, diferentemente de 2015–2017. Não interpretar códigos isoladamente nem por sua ordem física no Parquet.
- São preservados os recortes de fundamental total, segmentos, anos/séries, médio total, séries e não seriado. Eles se sobrepõem e não são somáveis. Não inferir outras modalidades a partir dessas colunas.
- Ano é inteiro, taxas são double e códigos são strings. Taxas fora da faixa e infinitos permanecem no histórico, mas ficam nulos na analítica. Textos inesperados em taxas de escolas identificadas bloqueiam a publicação.
- A camada analítica normaliza `Particular` para `Privada`. As dimensões usam versões por conjunto de atributos, sem retroagir os atributos mais recentes. Os códigos e valores originais permanecem no histórico.
- O particionamento é somente por ano, com um arquivo por partição. Particionar também por UF produziria até 486 combinações no recorte atual, sem evidência de benefício para consultas ainda não implementadas.
- Não são produzidas agregações municipais, ponderações, indicadores compostos ou médias apresentadas como taxas oficiais.
- Duplicatas e conflitos são reportados, sem deduplicação automática. Repetições de ano/escola identificada bloqueiam a publicação. Registros sem escola não participam dessa chave.
- A escrita usa lotes e arquivos temporários; as dimensões são deduplicadas em SQLite temporário. Há restauração das saídas anteriores em exceções de publicação, mas não garantia transacional contra interrupção abrupta do sistema durante a troca de vários arquivos.
- O CSV existente é ampliado; um JSON separado documenta os schemas. Uma tentativa com erro não publica uma base parcial e mantém o status de falha no relatório.
