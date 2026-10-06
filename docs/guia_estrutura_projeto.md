# Guia da estrutura do projeto

Este guia apresenta os módulos, as responsabilidades de cada etapa e os produtos disponíveis. As instruções de instalação e execução estão no [README](../README.md).

## Pastas principais

```text
pipeline-dados-inep/
|-- src/pipeline/       Codigo da pipeline
|-- docs/               Documentacao explicativa do projeto
|-- data/               Dados brutos, intermediarios e processados
|-- outputs/relatorios/ Relatorios gerados pela pipeline
|-- main.py             Executa as etapas da pipeline
|-- requirements.txt    Dependencias do projeto
`-- README.md           Visao geral e instrucoes rapidas
```

## O que olhar primeiro

- `main.py`: ponto de entrada. E o arquivo que executa as etapas ja implementadas.
- `src/pipeline/`: onde ficam os modulos da pipeline.
- [Metodologia](metodologia.md): regras de processamento, preservação e qualidade.
- [Dicionário de dados](dicionario_dados.md): campos, tipos e relacionamentos das saídas.
- [Fontes](fontes_dados.md): organização dos arquivos de entrada.

## Etapas implementadas

1. Descoberta dos arquivos
   - Codigo: `src/pipeline/descoberta_arquivos.py`
   - Saida: `outputs/relatorios/inventario_arquivos.csv`

2. Ingestao
   - Codigo: `src/pipeline/ingestao.py`
   - Saida: `outputs/relatorios/relatorio_ingestao.csv`

3. Auditoria
   - Codigo: `src/pipeline/auditoria.py`
   - Saidas:
     - `outputs/relatorios/relatorio_auditoria.csv`
     - `outputs/relatorios/relatorio_auditoria_abas.csv`

4. Limpeza e padronizacao
   - Codigo: `src/pipeline/limpeza.py`
   - Saidas:
     - `data/interim/taxas_rendimento_escolar_padronizada/`
     - `outputs/relatorios/relatorio_limpeza.csv`

5. Consolidacao historica e preparacao da camada analitica
   - Codigo: `src/pipeline/consolidacao.py`
   - Saidas:
     - `data/processed/taxas_rendimento_escolar_consolidada.parquet`
     - `outputs/relatorios/relatorio_consolidacao.csv`
     - `data/processed/dashboard/taxas/ano=<ano>/taxas.parquet`
     - `data/processed/dashboard/dim_escolas.parquet`
     - `data/processed/dashboard/dim_municipios.parquet`
     - `data/processed/dashboard/dim_metricas.parquet`
     - `outputs/relatorios/schema_consolidacao.json`
   - Apoio: `metricas.py` (catalogo por periodo), `validacao_consolidacao.py` (tipos e integridade) e `camada_analitica.py` (tabela escolar e dimensoes).
   - `main.py --etapa 5` executa somente esta etapa, usando os Parquets anuais existentes.
   - O contrato para consumo externo está em `docs/dicionario_dados.md`; conferir também `TOTAL.publicado`, status e avisos no relatório. As referências às dimensões são validadas antes da publicação.
   - A pasta `dashboard/` contém somente Parquets. A Etapa 6 persiste esses dados; Power BI é uma etapa futura.

## Etapa 6 — persistência PostgreSQL

- [Modelo do banco](modelo_banco_dados.md): tabelas, tipos, chaves, índices e estratégia de carga.
- `src/pipeline/banco/schema.sql`: criação inicial das cinco tabelas PostgreSQL, constraints e índices.
- `.env.example`: modelo de configuração local para PostgreSQL, sem senha real. As instruções estão no README.
- `src/pipeline/persistencia.py`: captura e manifesto, leitura em lotes, COPY para staging temporária, validações e publicação transacional com rollback e controle de carga.
- `main.py --etapa 6`: consome os produtos existentes da Etapa 5 sem executar as etapas anteriores.
- `outputs/relatorios/relatorio_persistencia_postgresql.json` e `persistencia_<UUID>.json`: resultado atual e histórico local por execução.
- `tests/test_persistencia.py` e `pytest.ini` (somente no ambiente local): testes de entrada e testes opcionais com PostgreSQL em schemas descartáveis, incluindo idempotência e rollback.
- O histórico completo permanece somente em Parquet. O PostgreSQL recebe exclusivamente a camada analítica. Power BI é uma etapa futura.
- A execução das etapas 1–5 não depende do PostgreSQL.

## Pastas que podem parecer confusas

- `.venv/`: ambiente virtual local do Python. Nao faz parte da analise do TCC.
- `data/raw/`: dados originais baixados manualmente. Devem ser preservados.
- `data/interim/`: dados intermediarios gerados pela pipeline.
- `data/processed/`: bases finais processadas pela pipeline.
- `outputs/relatorios/`: relatorios de controle, auditoria e validacao.
- `tests/`, `pytest.ini` e `scripts/`: recursos locais de desenvolvimento ignorados pelo Git e não distribuídos com o repositório. Os caches e arquivos temporários do pytest também são ignorados.

## Regra pratica

Para entender o projeto, leia nesta ordem:

1. `README.md`
2. `docs/guia_estrutura_projeto.md`
3. `main.py`
4. [Metodologia](metodologia.md)
5. [Dicionário de dados](dicionario_dados.md)
6. [Modelo do banco](modelo_banco_dados.md)
