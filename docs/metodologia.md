# Metodologia de processamento

Este documento explica as regras atuais da pipeline de Taxas de Rendimento Escolar do INEP. O recorte validado é 2007–2024, com dados em nível de escola. O projeto prepara dados para consulta e análise; não calcula indicadores derivados.

## Da fonte à base anual

A descoberta identifica arquivos Excel relevantes e registra seus caminhos no inventário. A ingestão inspeciona as planilhas e identifica abas e cabeçalhos. A auditoria registra diferenças estruturais antes da limpeza.

Na padronização, os arquivos de 2007–2011 combinam suas abas regionais; os demais usam a aba principal selecionada pela pipeline. Os campos de identificação recebem nomes canônicos, e os códigos são lidos como texto. Marcadores de ausência são convertidos em nulos, sem preenchimento com zero.

As bases anuais incluem `fonte_arquivo`, `fonte_caminho` e `fonte_aba`. A limpeza remove linhas cujo campo de ano não corresponde ao padrão admitido, como cabeçalhos auxiliares. A garantia de preservação integral da Etapa 5 se refere às linhas dos Parquets anuais recebidos, não a toda célula de cada planilha bruta.

A Etapa 4 reutiliza Parquets anuais existentes por padrão. Uma fonte corrigida exige regeneração explícita da base anual correspondente antes de consolidar novamente.

## Histórico e camada analítica

O histórico reúne a união das colunas anuais. Campos que não existem em determinado layout ficam nulos naquele ano. Todas as linhas intermediárias, inclusive as sem escola identificada, permanecem no histórico.

A camada analítica tem uma linha por `ano + co_entidade` e 54 métricas em colunas. Somente registros sem código escolar são excluídos dessa camada, com contagem no relatório. Duplicidades de ano/escola identificada bloqueiam a publicação; não há escolha automática de uma ocorrência.

O histórico completo permanece em Parquet. A persistência PostgreSQL se destina à camada analítica e ainda não possui carga implementada.

## Harmonização das taxas

As famílias são aprovação (`tap`), reprovação (`tre`) e abandono (`tab`). Cada família possui 18 recortes de fundamental e médio. Os aliases são interpretados por período em [metricas.py](../src/pipeline/metricas.py); um mesmo código pode mudar de significado entre layouts.

Não somar recortes sobrepostos nem tratar a harmonização de nomes como garantia de comparabilidade metodológica entre anos. A pipeline não calcula médias municipais, taxas agregadas, ponderações ou índice de vulnerabilidade. A descrição dos recortes está no [dicionário de dados](dicionario_dados.md).

## Versões históricas das dimensões

Escolas e municípios recebem IDs SHA-256 calculados a partir do conjunto de atributos observado. Um código pode ter várias versões, enquanto um conjunto idêntico reutiliza o mesmo ID. Os atributos mais recentes não são aplicados retroativamente.

As junções devem usar `id_escola` e `id_municipio`, não apenas os códigos INEP. Na camada analítica, `Particular` é harmonizado para `Privada`; o histórico preserva a representação anterior.

## Qualidade e limites dos dados

| Ocorrência | Tratamento |
| --- | --- |
| Ano inválido ou divergente do arquivo | Bloqueia a publicação da Etapa 5. |
| Código recebido como número | Bloqueia a publicação, pois zeros anteriores não podem ser recuperados. |
| Código textual fora do formato esperado | Aviso e preservação, sem correção automática. |
| Taxa textual inesperada em escola identificada | Bloqueia a publicação. |
| Taxa textual em linha sem escola | Texto preservado em JSON no histórico; valor numérico nulo. |
| Taxa fora de [0,100] ou infinita | Preservada e contabilizada no histórico; nula na analítica. |
| Coluna desconhecida | Preservada no histórico e reportada; sem interpretação presumida na analítica. |
| Métrica esperada ausente | Aviso; a métrica harmonizada fica nula. |
| Duplicidade de ano/escola | Bloqueia a publicação, sem deduplicação arbitrária. |
| Referência dimensional inválida | Bloqueia a publicação. |

Na base validada, as 2.588.399 linhas históricas resultam em 2.588.324 linhas analíticas: a diferença corresponde a 75 linhas sem escola identificada. Foram registrados 1.758 valores textuais auxiliares, oito taxas inválidas em 2007 e 48 ocorrências excedentes de registros auxiliares repetidos. Não foram identificadas duplicidades de ano/escola. Esses números descrevem a publicação validada; não são metas impostas ao processamento.

O status `aviso` significa publicação com ocorrências registradas. `erro` significa tentativa sem nova publicação. Conferir sempre a linha `TOTAL` do relatório, em especial `publicado`, e o schema JSON junto aos produtos.

## Reexecução e proteção das saídas

A Etapa 5 prepara arquivos temporários e valida as duas camadas antes de substituí-las. Reexecutar não acrescenta a nova base à anterior. Falhas de publicação por exceção de I/O provocam restauração dos produtos anteriores; essa troca de arquivos não oferece garantia transacional contra desligamento abrupto.

O rollback transacional planejado para PostgreSQL é uma responsabilidade futura e distinta. Consulte o [modelo do banco](modelo_banco_dados.md).
