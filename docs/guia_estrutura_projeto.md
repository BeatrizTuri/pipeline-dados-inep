# Guia da estrutura do projeto

Este projeto segue uma estrutura simples: codigo da pipeline, documentacao do TCC, dados e saidas geradas.

## Pastas principais

```text
pipeline-dados-inep/
|-- src/pipeline/       Codigo da pipeline
|-- docs/               Documentacao tecnica e metodologica do TCC
|-- data/               Dados brutos, intermediarios e processados
|-- outputs/relatorios/ Relatorios gerados pela pipeline
|-- main.py             Executa as etapas da pipeline
|-- requirements.txt    Dependencias do projeto
`-- README.md           Visao geral e instrucoes rapidas
```

## O que olhar primeiro

- `main.py`: ponto de entrada. E o arquivo que executa as etapas ja implementadas.
- `src/pipeline/`: onde ficam os modulos da pipeline.
- `docs/decisoes_metodologicas.md`: registro das decisoes tomadas durante o desenvolvimento.
- `docs/diario_tecnico.md`: historico tecnico do que foi feito em cada etapa.
- `docs/dicionario_dados.md`: explicacao dos campos e saidas do projeto.

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
   - A pasta `dashboard/` contém somente Parquets. Persistência em banco e Power BI são etapas futuras.

## Etapa 6 — planejamento, ainda sem implementação

- `docs/modelo_banco_dados.md`: proposta de tabelas, tipos, chaves, índices, staging, validação e rollback para persistir a camada analítica em PostgreSQL.
- O histórico completo continuará somente em Parquet. A integração PostgreSQL e o consumo por Power BI ainda não existem.
- O planejamento não altera comandos, código, dependências ou produtos da Etapa 5.

## Pastas que podem parecer confusas

- `.venv/`: ambiente virtual local do Python. Nao faz parte da analise do TCC.
- `data/raw/`: dados originais baixados manualmente. Devem ser preservados.
- `data/interim/`: dados intermediarios gerados pela pipeline.
- `data/processed/`: bases finais processadas pela pipeline.
- `outputs/relatorios/`: relatorios de controle, auditoria e validacao.
- `notebooks/`: nao existe mais no momento; recriar somente se houver analise exploratoria real.
- `tests/`: testes automatizados da Etapa 5, com dados artificiais e diretorios temporarios. Executar com `python -m pytest -q`.

## Regra pratica

Para entender o projeto, leia nesta ordem:

1. `README.md`
2. `docs/guia_estrutura_projeto.md`
3. `main.py`
4. `docs/diario_tecnico.md`
5. `docs/decisoes_metodologicas.md`
