# Modelo do banco

O banco guarda as taxas escolares preparadas pela pipeline. O histórico completo também permanece nos arquivos Parquet.

## O que cada tabela guarda

| Tabela | Conteúdo |
| --- | --- |
| `fato_rendimento_escolar` | Uma linha por escola e ano, com as taxas de aprovação, reprovação e abandono. |
| `dim_escola` | Nome, localização, rede e município da escola, preservando suas versões históricas. |
| `dim_municipio` | Código, nome, UF e região do município, preservando os nomes encontrados ao longo dos anos. |
| `catalogo_metricas` | Significado das colunas de taxas em cada período. |
| `controle_carga` | Resultado de cada execução da carga no banco. |

A fato aponta para a versão de escola e município usada naquela observação. Os campos `id_escola` e `id_municipio` fazem essas ligações.

Os códigos `co_entidade` e `co_municipio` identificam a escola e o município. São texto para preservar zeros à esquerda. Um código pode ter vários IDs históricos quando seus atributos mudam.

## Por que há dois cadastros de municípios?

A tabela histórica preserva o que veio da fonte. Assim, o mesmo código pode ter nomes como “SAO PAULO” e “São Paulo”.

Para os gráficos, a consulta salva `dim_municipio_canonica` oferece **uma linha por código municipal**, usando a representação observada no ano mais recente. Em empate, usa a mais frequente nesse ano; persistindo o empate, usa a ordem do identificador técnico. Versões sem ano observado ficam depois das datadas. Se nenhuma tiver ano, vale a ordem do identificador.

Isso reúne as observações do mesmo município sem apagar os nomes antigos. Municípios diferentes com o mesmo nome continuam distintos pelo código.

A outra consulta salva, `vw_fato_rendimento_escolar`, apresenta a fato com `co_municipio`, facilitando a ligação com o cadastro canônico. Ela mantém a mesma quantidade de observações da fato.

## Como os dados são atualizados

A Etapa 6 confere a entrada em uma área temporária e, depois, substitui a publicação em uma transação: confirma o conjunto completo ou desfaz as alterações se houver erro antes da confirmação.

Repetir a mesma carga não acumula duplicatas. O controle recebe um novo registro de execução para auditoria. Reduções de período ou de contagens são bloqueadas para revisão.

Em um banco novo, [schema.sql](../src/pipeline/banco/schema.sql) cria as tabelas. A Etapa 6 instala as duas consultas de [canonica.sql](../src/pipeline/banco/canonica.sql). Os comandos estão no [README](../README.md#5-executar-a-persistência--etapa-6).

## Power BI

Use esta relação, com filtro em uma única direção:

```text
dim_municipio_canonica[co_municipio] (1)
                  ↓
vw_fato_rendimento_escolar[co_municipio] (*)
```

- Use Município, UF e Região da dimensão canônica nos filtros.
- Na categoria municipal, inclua nome, UF e código para distinguir homônimos.
- Conte escolas pelo código `co_entidade` da fato, sem contar versões de `dim_escola`.
- Não crie outro caminho ativo da dimensão canônica até a fato passando pela escola.

Exemplo de medida; adapte o nome da tabela ao seu relatório:

```dax
Numero de escolas = DISTINCTCOUNT(vw_fato_rendimento_escolar[co_entidade])
```

Com filtro de ano, a medida conta as escolas daquele recorte. Sem filtro, conta escolas distintas em todo o período.

Atualizar o Power BI recarrega suas fontes existentes: não importa as novas consultas nem troca sozinho os campos dos gráficos. Faça a atualização após a conclusão da carga.

Os tipos e significados dos campos estão no [dicionário](dicionario_dados.md). As taxas são percentuais; a base não contém quantidades de alunos.
