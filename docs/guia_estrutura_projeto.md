# Guia da estrutura do projeto

Este projeto segue uma estrutura simples: código da pipeline, documentação do TCC, dados e saídas geradas.

## Pastas principais

```text
pipeline-dados-inep/
├── src/pipeline/      Código da pipeline
├── docs/              Documentação técnica e metodológica do TCC
├── notebooks/         Explorações manuais e estudos complementares
├── data/              Dados brutos e bases intermediárias
├── outputs/           Relatórios, tabelas e gráficos gerados
├── main.py            Executa as etapas da pipeline
├── requirements.txt   Dependências do projeto
└── README.md          Visão geral e instruções rápidas
```

## O que olhar primeiro

Para entender o andamento do TCC, leia nesta ordem:

1. `docs/diario_tecnico.md`
2. `docs/decisoes_metodologicas.md`
3. `docs/dicionario_dados.md`
4. `main.py`
5. arquivos em `src/pipeline/`

## Etapas da pipeline

| Etapa | Arquivo principal | Saída principal |
| --- | --- | --- |
| 1. Descoberta | `src/pipeline/descoberta_arquivos.py` | `outputs/relatorios/inventario_arquivos.csv` |
| 2. Ingestão | `src/pipeline/ingestao.py` | `outputs/relatorios/relatorio_ingestao.csv` |
| 3. Auditoria | `src/pipeline/auditoria.py` | `outputs/relatorios/relatorio_auditoria.csv` |
| 4. Limpeza e padronização | `src/pipeline/limpeza.py` | `outputs/relatorios/relatorio_limpeza.csv` |
| 5. Consolidação | `src/pipeline/consolidacao.py` | ainda não implementada |

## Pastas que podem parecer confusas

- `.venv/`: ambiente Python local. É necessário para rodar o projeto, mas não faz parte do código do TCC.
- `__pycache__/` e `.pytest_cache/`: caches automáticos do Python e do pytest. Podem ser apagados sem afetar o projeto.
- `data/raw/`: arquivos originais do INEP. Não devem ser editados manualmente pela pipeline.
- `data/interim/`: bases intermediárias geradas pela pipeline.
- `outputs/`: relatórios e saídas geradas automaticamente.
- `references/`: pasta opcional para referências bibliográficas; está vazia no momento.
- `tests/`: pasta reservada para testes automatizados; está vazia no momento.

## Regra prática

Para desenvolver o TCC, concentre-se em:

```text
src/pipeline/
docs/
main.py
```

As pastas `data/` e `outputs/` são importantes para execução e validação, mas são geradas ou preenchidas a partir dos dados locais.
