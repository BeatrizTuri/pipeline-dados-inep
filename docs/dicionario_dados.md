# Dicionário de dados

Este dicionário registra a leitura inicial das bases de Taxas de Rendimento Escolar por escola. Ele ainda não representa uma base final padronizada; serve como apoio para auditoria, limpeza e consolidação.

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
| `tipoloca` | `Localização`, `TIPOLOCA` | Localização da escola. Não aparece em todos os anos mais recentes. |
| `dependad` | `Rede`, `DEPENDAD`, `NO_DEPENDENCIA` | Dependência administrativa/rede. |

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
