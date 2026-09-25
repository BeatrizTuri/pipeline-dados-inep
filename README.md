# Pipeline de Dados Educacionais do INEP

Este projeto é desenvolvido como parte de um Trabalho de Conclusão de Curso em Engenharia da Computação.

O objetivo principal é desenvolver uma pipeline computacional para processamento e análise de dados públicos educacionais do INEP, com foco em ingestão, auditoria, limpeza, padronização, consolidação e geração de bases analíticas.

A pipeline é a contribuição central do TCC. Sua principal saída é a base histórica consolidada, da qual é derivada uma camada analítica para um futuro dashboard interativo. O dashboard ainda não está implementado.

O índice de vulnerabilidade escolar está fora do escopo atual. Indicadores derivados poderão ser incorporados futuramente, desde que tenham metodologia academicamente validada.

## Fonte dos dados

Os dados utilizados são obtidos manualmente a partir do portal oficial do INEP, especialmente a base de Taxas de Rendimento Escolar em nível de escola.

A pipeline não realiza web scraping nem download automático dos dados.

## Organização dos dados

Os arquivos oficiais baixados devem ser colocados em:

```text
data/raw/taxas_rendimento_escolar/
```

## Estrutura simplificada

Para entender o projeto rapidamente, consulte:

- `docs/guia_estrutura_projeto.md`
- `docs/diario_tecnico.md`
- `docs/decisoes_metodologicas.md`

As partes principais do projeto são:

```text
src/pipeline/    código das etapas da pipeline
docs/            documentação do TCC
data/            dados brutos e intermediários
outputs/         relatórios gerados
main.py          execução da pipeline
```

## Fluxo e saídas

Dados brutos → descoberta → ingestão → auditoria → limpeza e padronização anual → **consolidação histórica e preparação da camada analítica** → dashboard futuro.

- A Etapa 4 mantém a representação canônica anual em `data/interim/taxas_rendimento_escolar_padronizada/`.
- A Etapa 5 gera `data/processed/taxas_rendimento_escolar_consolidada.parquet`, preservando linhas, colunas de origem e rastreabilidade.
- `data/processed/dashboard/taxas/ano=<ano>/taxas.parquet` contém as taxas escolares harmonizadas em formato wide, com partições anuais.
- `dim_escolas.parquet`, `dim_municipios.parquet` e `dim_metricas.parquet`, na pasta `dashboard/`, apoiam filtros e interpretação dos campos.
- `outputs/relatorios/relatorio_consolidacao.csv` registra contagens, validações e status; `schema_consolidacao.json` descreve os schemas publicados.

Não são calculadas taxas municipais, ponderações ou indicadores compostos. Os aliases das taxas são interpretados por período, conforme os cabeçalhos dos arquivos locais de 2007 a 2024; novos períodos exigem revisão do catálogo.

## Execução

Com as dependências de `requirements.txt` instaladas no ambiente Python:

```sh
python main.py             # todas as etapas
python main.py --etapa 5   # somente consolidação e camada analítica
python -m pytest -q        # testes com dados artificiais
```

A Etapa 5 processa lotes, sem concatenar toda a série em memória. As saídas são preparadas em diretório temporário e substituídas após validação. Uma falha mantém os produtos anteriores e gera status `erro` no relatório; o comando retorna código de saída 1. Consulte sempre `TOTAL.publicado` antes de usar os arquivos como resultado da última execução.
