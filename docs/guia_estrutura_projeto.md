# Estrutura do projeto

O percurso dos dados é:

```text
Excel do INEP → bases anuais padronizadas → histórico e camada analítica
             → PostgreSQL → Power BI
```

`main.py` escolhe as etapas. Sem argumentos, executa 1–5; com `--etapa 6`, executa somente a carga no banco.

## Código: ordem de leitura

Todos os módulos abaixo estão em `src/pipeline/`.

| Etapa | Arquivo | Responsabilidade |
| --- | --- | --- |
| 1 | `descoberta_arquivos.py` | Localiza as planilhas e identifica os anos. |
| 2 | `ingestao.py` | Confere a leitura, a aba e o cabeçalho. |
| 3 | `auditoria.py` | Examina as colunas e abas disponíveis. |
| 4 | `limpeza.py` | Padroniza campos e gera um Parquet por ano. |
| 5 | `consolidacao.py` | Reúne os anos, valida e publica os produtos. |
| 6 | `persistencia.py` | Confere e carrega a publicação no PostgreSQL. |

Na etapa 5, `metricas.py` interpreta as taxas por período, `validacao_consolidacao.py` confere tipos e integridade e `camada_analitica.py` prepara as taxas escolares e dimensões. `config.py` centraliza caminhos e parâmetros.

Em `banco/`, `schema.sql` cria as tabelas de um banco novo; `canonica.sql` define as views usadas pela Etapa 6. Cada estrutura SQL é definida uma única vez.

## Pastas

| Pasta | Conteúdo |
| --- | --- |
| `data/raw/` | Planilhas originais, obtidas manualmente. |
| `data/interim/` | Parquets anuais padronizados. |
| `data/processed/` | Histórico e Parquets analíticos em `dashboard/`. |
| `outputs/relatorios/` | Ocorrências e resultados das execuções. |
| `tests/` | Testes automatizados com exemplos controlados. |
| `docs/` | Método, modelo, campos e registros do trabalho. |

Dados, relatórios, `.env`, ambiente virtual e caches não acompanham o Git. O arquivo `.env.example` mostra os campos de configuração, sem credenciais.

## Onde procurar explicações

- [README](../README.md): instalação e comandos.
- [Metodologia](metodologia.md): transformações e critérios de qualidade.
- [Dicionário](dicionario_dados.md): campos e significado das métricas.
- [Modelo do banco](modelo_banco_dados.md): tabelas, município canônico e Power BI.
- [Testes](guia_testes.md): como executar e interpretar as verificações.
- [Diário técnico](diario_tecnico.md): decisões e resultados datados; não é um manual de leitura do código.
