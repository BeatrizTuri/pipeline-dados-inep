# Dicionário de dados

Este dicionário descreve os campos canônicos anuais, a base histórica e a camada analítica das Taxas de Rendimento Escolar por escola.

## Campos de identificação

| Campo canônico | Nomes encontrados | Observação |
| --- | --- | --- |
| `ano` | `Ano`, `NU_ANO_CENSO` | Ano de referência da informação. |
| `no_regiao` | `Região`, `NO_REGIAO` | Região geográfica. Em arquivos antigos, também pode estar implícita na aba. |
| `sg_uf` | `UF`, `SG_UF` | Sigla da unidade federativa. |
| `co_municipio` | `Código do Município`, `CO_MUNICIPIO` | Código do município. Deve ser preservado como texto na ingestão. |
| `no_municipio` | `Nome do Município`, `NO_MUNICIPIO` | Nome do município. |
| `co_entidade` | `Código da Escola`, `CO_ENTIDADE` | Código da escola. Deve ser preservado como texto na ingestão. |
| `no_entidade` | `Nome da Escola`, `NO_ENTIDADE` | Nome da escola. |
| `tipoloca` | `Localização`, `TIPOLOCA`, `NO_CATEGORIA` | Localização da escola. |
| `dependad` | `Rede`, `DEPENDAD`, `Dependência Administrativa`, `NO_DEPENDENCIA` | Dependência administrativa/rede. |

## Famílias de taxas

| Família | Padrões encontrados | Interpretação |
| --- | --- | --- |
| Aprovação | `TAP_*`, `Taxa de Aprovação*`, `1_*` | Percentual de aprovação. |
| Reprovação | `TRE_*`, `Taxa de Reprovação*`, `2_*` | Percentual de reprovação. |
| Abandono | `TAB_*`, `Taxa de Abandono*`, `3_*` | Percentual de abandono. |

## Observações de auditoria

- Os arquivos de 2007 a 2011 estão organizados por abas regionais; a consolidação desses anos deve combinar as abas regionais antes de gerar uma base anual.
- A partir de 2012, a maior parte dos arquivos possui aba `ESCOLAS`.
- Os nomes das colunas mudam ao longo do tempo, então a limpeza deve mapear aliases para nomes canônicos antes da consolidação.
- A Etapa 3 ainda não converte tipos, não trata valores ausentes e não calcula indicadores.

## Saída da Etapa 4

- A Etapa 4 gera arquivos anuais padronizados em `data/interim/taxas_rendimento_escolar_padronizada/`.
- Cada arquivo anual preserva os campos canônicos de identificação, as colunas de taxa padronizadas por família e os metadados `fonte_arquivo`, `fonte_caminho` e `fonte_aba`.
- As famílias de taxas são padronizadas com os prefixos `tap_`, `tre_` e `tab_`.
- Valores textuais usados como ausentes nas planilhas, como `--`, são convertidos para valor ausente na base intermediária.
- A Etapa 4 ainda não empilha todos os anos em uma base histórica única; isso fica reservado para a Etapa 5.

## Saída da Etapa 5

- A Etapa 5 gera a base histórica consolidada em `data/processed/taxas_rendimento_escolar_consolidada.parquet`.
- A base consolidada cobre o período de 2007 a 2024.
- A consolidação preserva os campos de identificação, as colunas de taxas e os metadados de rastreabilidade.
- Como as estruturas das taxas variam entre períodos, a base consolidada contém a união das colunas padronizadas dos arquivos anuais.
- Colunas que não existem em determinado ano ficam com valor ausente nesse ano.
- Registros sem `co_entidade` são preservados no histórico e excluídos somente da camada analítica escolar, com contagem no relatório.

## Tipos e integridade da Etapa 5

| Campo | Tipo Parquet | Regra |
| --- | --- | --- |
| `ano` | int32 | Obrigatório; deve concordar com o nome do arquivo. |
| `co_entidade`, `co_municipio` | string | Sem conversão numérica; zeros à esquerda preservados. Entradas numéricas não nulas são rejeitadas. |
| `tap_*`, `tre_*`, `tab_*` | double | Percentuais; ausentes continuam nulos. Vírgula decimal aceita. |
| Identificação, proveniência e outros metadados escalares | string | União das colunas recebidas; estruturas aninhadas não são convertidas silenciosamente. |
| `taxas_textuais_origem` | string (JSON) | Preserva textos não numéricos de taxas em linhas sem escola, como cabeçalhos auxiliares. A célula numérica correspondente fica nula. |

Textos não numéricos em taxas de escolas identificadas bloqueiam a publicação. Percentuais numéricos fora de [0, 100] e infinitos são contabilizados, preservados no histórico e anulados na camada analítica. Ausência nunca é convertida em zero. UFs ausentes também entram na contagem de UFs inválidas.

## Métricas harmonizadas da camada analítica

A tabela analítica permanece wide: 54 colunas numéricas, três famílias (`tap`: aprovação, `tre`: reprovação, `tab`: abandono) para 18 recortes. Os sufixos são:

- `fun`, `fun_ai`, `fun_af`: fundamental total, anos iniciais e anos finais.
- `fun_01` a `fun_09`: anos do fundamental, conforme correspondências série/ano dos cabeçalhos de cada período.
- `med`, `med_01` a `med_04`, `med_ns`: médio total, séries e não seriado.

Total, segmentos e anos/séries são recortes sobrepostos: não devem ser somados. A harmonização de nomes não constitui garantia de comparabilidade metodológica entre períodos nem identifica modalidades ausentes na fonte.

| Período | Layout de origem |
| --- | --- |
| 2007–2010 | Nomes descritivos; séries do regime de oito anos e anos do regime de nove anos aparecem associados nos cabeçalhos. |
| 2011–2014 | Nomes descritivos com `ens_fundamental`, `anos_iniciais_1o_ao_5o_ano`, `1o_ano` etc. |
| 2015–2017 | `fun`, `f14`, `f58`, `f00`–`f08`, `med`, `m01`–`m04`, `mns`. |
| 2018–2020 | Cabeçalhos locais associam `f04` a anos finais, `f58` ao 1º ano e `f00`–`f03` ao 2º–5º ano; `f05`–`f08` continuam 6º–9º ano. |
| 2021–2024 | `fun`, `fun_ai`, `fun_af`, `fun_01`–`fun_09`, `med`, `med_01`–`med_04`, `med_ns`. |

O catálogo executável está em `src/pipeline/metricas.py`. A dimensão de métricas tem 270 registros (54 por layout), com `codigo_original`, `coluna_analitica`, `ano_inicio`, `ano_fim`, `tipo_taxa`, `etapa_ensino`, `detalhamento`, `descricao` e `observacao`. Ela inclui métricas previstas pelo layout mesmo quando um arquivo não contém todas as colunas. Métricas desconhecidas ficam no histórico e são listadas no relatório, sem associação presumida.

## Dimensões e filtros

`dim_escolas` contém `id_escola`, códigos, nomes, município, UF, região, localização e dependência. `dim_municipios` contém `id_municipio`, código, nome, UF e região. Os IDs são hashes SHA-256 do conjunto de atributos: duas versões de uma escola podem compartilhar `co_entidade`, mas terão IDs diferentes quando os atributos mudarem. Não juntar a dimensão apenas pelo código da escola, pois isso pode multiplicar linhas. A tabela analítica referencia a versão observada naquele ano; nenhuma versão mais recente é retroativamente aplicada.

Na camada analítica, `Particular` é harmonizado para `Privada`; o texto original permanece no histórico. Os nomes canônicos existentes `no_regiao`, `tipoloca` e `dependad` são mantidos. A dimensão municipal pode ter mais de uma versão por código.

O campo `ano` é armazenado no caminho Hive da partição; ao ler o dataset completo, usar `partitioning="hive"`. Um arquivo individual não contém a coluna física `ano`. Não há partições por UF.

## Relatório e schema

O CSV registra uma linha por arquivo e uma linha `TOTAL`, com anos, arquivos encontrados/processados, linhas, escolas e municípios únicos, UFs, ausências, taxas inválidas/textuais, colunas ausentes/desconhecidas, duplicidades e status. As duplicidades são contadas como ocorrências excedentes; `duplicatas_exatas` compara o conteúdo sem proveniência e `conflitos_ano_escola` compara o conteúdo de uma chave repetida com sua primeira ocorrência. Chaves repetidas de escolas identificadas bloqueiam a publicação, sem deduplicação arbitrária.

`publicado=False` indica que as saídas anteriores não foram atualizadas: contagens eventualmente presentes se referem à tentativa de processamento, não a uma nova base disponível. Lacunas entre o menor e o maior ano encontrado geram aviso; não há uma lista de anos obrigatórios imposta à entrada. O JSON registra os schemas finais e a convenção de particionamento. O relatório de falha pode ser mais recente que o schema e as bases da última execução bem-sucedida.

## Contrato para consumo externo

O contrato vigente cobre os layouts de 2007–2024. Todos os Parquets anuais encontrados são inspecionados; anos fora dos layouts conhecidos bloqueiam a publicação até revisão do catálogo. Os anos efetivamente publicados constam em `TOTAL.anos_processados`.

| Produto | Granularidade e chaves | Tipos e nulabilidade |
| --- | --- | --- |
| Histórico | Todas as linhas anuais, inclusive auxiliares; não impor chave primária escolar ao histórico inteiro. | `ano` int32 não nulo; códigos e metadados string; taxas double. Demais campos podem ser nulos. |
| `taxas/` | Uma linha por (`ano`, `co_entidade`); referências por `id_escola` e `id_municipio`. | 64 colunas físicas: oito campos de identificação string, dois IDs string e 54 taxas double. `ano` int32 é recuperado da partição, totalizando 65 colunas lógicas. Escola e seu ID são obrigatórios; município e seu ID podem ser nulos em conjunto. Taxas e demais atributos admitem nulos. |
| `dim_escolas` | Uma versão por `id_escola`, único e não nulo. `co_entidade` pode repetir entre versões. | Nove colunas string: `id_escola`, `co_entidade`, `no_entidade`, `co_municipio`, `no_municipio`, `sg_uf`, `no_regiao`, `tipoloca`, `dependad`. Código escolar obrigatório; outros atributos podem ser nulos. |
| `dim_municipios` | Uma versão por `id_municipio`, único e não nulo. `co_municipio` pode repetir entre versões. | Cinco colunas string: `id_municipio`, `co_municipio`, `no_municipio`, `sg_uf`, `no_regiao`. Código municipal obrigatório; demais atributos podem ser nulos. |
| `dim_metricas` | Catálogo de aliases; chave (`ano_inicio`, `codigo_original`). | `ano_inicio` e `ano_fim` int64; demais sete campos textuais, descritos acima (`large_string` no schema Arrow do ambiente validado; conferir o JSON). O catálogo gerado não contém nulos. |

`dim_metricas` não é uma dimensão ligada por ID a cada linha da fato wide: descreve as colunas de taxas por período. Não fazer junção apenas por `coluna_analitica`, que se repete nos cinco layouts.

Os IDs são o SHA-256 hexadecimal do JSON UTF-8 dos atributos ordenados, sem espaços separadores, com caracteres Unicode preservados e ausências representadas por `null`. Para escola, a ordem é `co_entidade`, `no_entidade`, `co_municipio`, `no_municipio`, `sg_uf`, `no_regiao`, `tipoloca`, `dependad`; para município, `co_municipio`, `no_municipio`, `sg_uf`, `no_regiao`. A harmonização de `Particular` ocorre antes do cálculo. Esses IDs representam conjuntos de atributos, não intervalos de vigência: o mesmo conjunto que reaparece reutiliza o ID.

Antes de publicar, a pipeline relê os IDs e códigos nos Parquets: exige unicidade e ausência de nulos nas chaves dimensionais, correspondência dos códigos e existência de todas as referências não nulas. Referência escolar nula ou nulabilidade municipal inconsistente bloqueia a publicação. O sucesso fica registrado em `TOTAL.relacionamentos_validados=True`. Junções por esses IDs são muitos-para-um e não multiplicam registros.

`codigos_escola_invalidos` conta códigos não nulos que não tenham oito dígitos ASCII; `codigos_municipio_invalidos` aplica sete dígitos. São verificações de formato, não consultas a cadastros oficiais. Geram aviso e preservam os textos nas duas camadas, sem completar zeros, substituir ou excluir registros. Ausentes têm contadores próprios. `colunas_desconhecidas` lista toda coluna fora da identificação, proveniência e catálogo do ano, inclusive taxas desconhecidas; essas colunas permanecem no histórico e geram aviso.

Exemplo de leitura de um ano, preservando tipos e recuperando a coluna de partição:

```python
import pyarrow.dataset as ds

taxas = ds.dataset("data/processed/dashboard/taxas", format="parquet", partitioning="hive")
ano_2024 = taxas.to_table(filter=ds.field("ano") == 2024)
```

O consumidor deve conferir `TOTAL.publicado`, `TOTAL.status` e os avisos; o schema JSON descreve os tipos físicos efetivamente publicados. Status `aviso` permite consumo com as ressalvas registradas, enquanto `erro` indica tentativa não publicada. As saídas protegidas por restauração em erros de I/O não constituem transação resistente a desligamento abrupto; executar uma publicação por vez. A Etapa 4 reutiliza arquivos anuais existentes por padrão: mudanças na fonte exigem sua regeneração explícita antes de executar a Etapa 5.
