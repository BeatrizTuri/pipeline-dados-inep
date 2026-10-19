# Modelo do banco e uso no Power BI

O histórico completo fica em Parquet. O PostgreSQL recebe os produtos analíticos publicados pela Etapa 5, sem recalcular taxas.

## Tabelas

As colunas e restrições executáveis estão em [schema.sql](../src/pipeline/banco/schema.sql). O significado dos campos está no [dicionário](dicionario_dados.md).

| Tabela | Uma linha representa | Chave |
| --- | --- | --- |
| `dim_escola` | Uma versão dos atributos escolares. | `id_escola` |
| `dim_municipio` | Uma versão dos atributos municipais. | `id_municipio` |
| `fato_rendimento_escolar` | Uma escola em um ano, com 54 taxas. | `ano, co_entidade` |
| `catalogo_metricas` | Um alias de taxa em um período de layout. | `ano_inicio, codigo_original` |
| `controle_carga` | Uma tentativa de carga, com resultado e evidências. | `id_execucao` |

A fato referencia a versão escolar e a municipal. A escola também referencia o município. O carregador verifica a coerência entre essas referências; as chaves estrangeiras, sozinhas, não garantem que todos os atributos coincidam.

Códigos INEP e identificadores permanecem texto. Os IDs são hashes do conteúdo: identificam versões, não intervalos de vigência. Por isso, não há unicidade de `co_entidade` ou `co_municipio` nas dimensões históricas. As taxas são valores de precisão dupla ou NULL.

A dimensão escolar mantém os atributos municipais da origem, inclusive quando falta o código. A carga deriva seu `id_municipio` por correspondência única dos quatro atributos: código, nome, UF e região. Ausência de código pode resultar em referência nula, sem apagar os atributos restantes.

O catálogo não deve ser ligado diretamente à fato somente pelo nome da métrica: há vários aliases e períodos para a mesma coluna, e essa junção multiplicaria linhas.

## Município histórico e canônico

`co_municipio` é a identidade do município; `id_municipio` identifica uma representação histórica. Usar o nome histórico como categoria fragmentava o mesmo código em nomes como `SAO PAULO` e `São Paulo`.

As duas views são definidas uma única vez em [canonica.sql](../src/pipeline/banco/canonica.sql):

- `dim_municipio_canonica`: uma linha por código, com nome, UF, região, ID da versão escolhida e ano de referência.
- `vw_fato_rendimento_escolar`: todas as colunas da fato e o código municipal, obtido pela referência histórica. O LEFT JOIN preserva observações sem município e não multiplica linhas.

A representação canônica é escolhida por:

1. Maior ano observado na fato.
2. Maior número de observações da versão nesse ano, se houver empate.
3. Menor hash em ordenação binária (`COLLATE "C"`), se o empate persistir.

Versões sem observação ficam após as datadas. Se nenhuma tiver observação, vence o menor hash e o ano fica nulo. Atributos nulos são preservados. A regra é independente da ordem dos arquivos e não transforma grafia em identidade. Ela representa o nome mais recente disponível na base escolar, não uma certificação oficial da denominação vigente.

## Instalação e carga

Em banco novo, execute `schema.sql` para criar as tabelas. A Etapa 6 instala as views de `canonica.sql` dentro da transação de publicação. Não execute novamente o schema inteiro em um banco existente.

Para instalar somente as views em um banco já carregado, execute o conteúdo de `canonica.sql` no editor SQL dentro de uma transação (`BEGIN` e `COMMIT`), fora da janela de carga. Na execução habitual, basta `python main.py --etapa 6`.

A carga segue quatro passos:

1. Captura os Parquets e controles da Etapa 5 e confere hashes, schemas, anos e contagens.
2. Transfere os dados em lotes por COPY para tabelas temporárias de staging e compara o conteúdo recebido.
3. Valida chaves, referências, atributos, taxas, catálogo e contagens.
4. Em uma transação, instala as views, substitui os dados por DELETE/INSERT, compara com a staging e ativa o registro de sucesso.

Uma falha antes do commit reverte a substituição e preserva a publicação anterior. O diagnóstico é registrado separadamente. Se a resposta ao commit for perdida, o carregador consulta o controle pelo UUID para confirmar o resultado; se não conseguir, informa status indeterminado.

Repetir a origem mantém o mesmo conteúdo analítico, com novo registro de controle. Somente uma carga pode estar ativa. Um advisory lock impede cargas simultâneas que utilizem esse mesmo mecanismo. Reduções de anos ou de contagens em relação à carga ativa são bloqueadas para revisão.

Não publique a Etapa 5 durante a captura de seus arquivos. Consumidores de várias consultas, como uma atualização do Power BI, devem ser coordenados fora da publicação da carga: transação de escrita não garante sozinha uma fotografia única para consultas separadas.

## Conferir no PostgreSQL

As duas primeiras contagens devem ser iguais; nulos e duplicidades devem ser zero:

```sql
SELECT count(*) AS linhas,
       count(DISTINCT co_municipio) AS codigos_distintos,
       count(*) FILTER (WHERE co_municipio IS NULL) AS nulos
FROM public.dim_municipio_canonica;

SELECT co_municipio, count(*)
FROM public.dim_municipio_canonica
GROUP BY co_municipio HAVING count(*) > 1;
```

Compare nomes históricos e a escolha canônica:

```sql
SELECT c.co_municipio, c.no_municipio AS nome_canonico, c.ano_referencia,
       array_agg(DISTINCT h.no_municipio) AS nomes_historicos
FROM public.dim_municipio_canonica c
JOIN public.dim_municipio h USING (co_municipio)
GROUP BY c.co_municipio, c.no_municipio, c.ano_referencia
HAVING count(*) > 1
ORDER BY c.co_municipio;
```

A view da fato deve ter a mesma quantidade de linhas da tabela:

```sql
SELECT (SELECT count(*) FROM public.fato_rendimento_escolar) AS fato,
       (SELECT count(*) FROM public.vw_fato_rendimento_escolar) AS view_fato;
```

Os resultados reais e períodos validados estão no [diário técnico](diario_tecnico.md), não são quantidades fixas impostas ao modelo.

## Power BI

Use `dim_municipio_canonica[co_municipio]` (1) → `vw_fato_rendimento_escolar[co_municipio]` (*), com filtro em direção única e códigos como texto. A consulta da fato existente pode passar a ler a view mantendo o nome da consulta; confira as medidas e relacionamentos após a troca.

Os filtros de Município, UF e Região devem usar a dimensão canônica. No eixo municipal, inclua nome, UF e código na categoria para distinguir também municípios homônimos. Nomes históricos ficam disponíveis para auditoria. Não crie um caminho ativo alternativo da dimensão canônica até a fato através da escola.

Para contar escolas, use contagem distinta do código escolar na fato:

```dax
Numero de escolas = DISTINCTCOUNT(vw_fato_rendimento_escolar[co_entidade])
```

Adapte o nome da tabela ao modelo. Com filtro de ano, a medida conta escolas daquele recorte; sem filtro, conta escolas distintas de todo o período, não a soma das contagens anuais. Não conte versões de `dim_escola` como escolas.

Atualize o Power BI depois da carga. A atualização dos dados não importa views novas nem troca automaticamente os campos antigos dos gráficos.
