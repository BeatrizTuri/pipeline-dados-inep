# Diário técnico — Etapa 6

## 19 de outubro de 2026 — remoção de duplicações

A segunda revisão removeu o leitor de planilhas sem uso, reutilizou os aliases de identificação na limpeza e a regra de abas regionais na auditoria, concentrou a contagem de status em `main.py` e retirou dependências de desenvolvimento sem uso. O schema SQL teve apenas linhas em branco reduzidas. Metodologia e dicionário passaram a remeter aos documentos específicos em vez de repetir a explicação da carga. Validação: **82 testes aprovados**, mais comparação de 14 cenários simulados dos comandos, sem mudança nas mensagens ou códigos de saída e sem carga de produção.

As views passaram a ter uma única definição em `banco/canonica.sql`; `schema.sql` mantém somente as tabelas. Foram retirados os três scripts auxiliares, com as consultas necessárias incorporadas ao modelo do banco, e o documento separado de revisão organizacional. Os registros locais antigos continuam preservados; as decisões de versionar testes e separar dependências permanecem vigentes.

README, estrutura, modelo e guia dos testes foram reduzidos para evitar explicações repetidas. As explicações individuais dos testes permanecem no código. Foi removido somente o teste que comparava as duas cópias do SQL. Validação completa com integração: **82 aprovados**. Não houve recarga de dados de produção.

## 19 de outubro de 2026 — suporte ao arquivo de 2025

A entrada local de 2025 já havia sido padronizada pela Etapa 4, mas a Etapa 5 bloqueava a publicação porque o catálogo encerrava em 2024. Foram conferidas as linhas 6–9 do cabeçalho do Excel `tx_rend_escolas_2025.xlsx`, aba `ESCOLAS`: as três famílias mantêm os mesmos 18 recortes semânticos e códigos do período iniciado em 2021. Os Parquets de 2024 e 2025 possuem as mesmas colunas; a entrada de 2025 contém 126.685 registros.

O período 2021–2024 foi estendido até 2025 em `metricas.py`, preservando as 54 métricas analíticas e os 270 registros de catálogo. Anos a partir de 2026 continuam bloqueados até revisão. Não foram alteradas a limpeza, as fontes brutas, as regras históricas de 2007–2024, as transações ou a regra municipal canônica. A Etapa 5 precisa ser republicada antes da Etapa 6 para que o catálogo Parquet corresponda ao contrato atualizado.

Testes: **83 aprovados**, com integração PostgreSQL habilitada em schemas descartáveis. Foram adicionadas verificações do mapa de 2025, preservação dos períodos anteriores, rejeição de 2026, duas consolidações 2024–2025 com todas as 54 métricas e códigos textuais, e publicação PostgreSQL com catálogo e ano canônico de 2025. As evidências de cargas anteriores deste diário continuam datadas e não incluem automaticamente o novo ano.

A execução integral da Etapa 5 publicou 19 anos (2007–2025), com **2.715.084 linhas históricas**, **2.715.008 linhas analíticas**, 220 colunas históricas e zero erros. O status final é `aviso`, com `publicado=True` e relacionamentos validados. Em 2025, uma linha sem código escolar permanece apenas no histórico; as 126.684 escolas identificadas representam 5.571 códigos municipais. A publicação anterior de 2007–2024 tinha 5.570 códigos; essa quantidade não é constante do modelo.

A primeira execução teve acesso negado ao substituir o relatório CSV existente, embora os Parquets já tivessem sido publicados. O arquivo tinha acesso restrito ao grupo Administradores. A Etapa 5 foi repetida integralmente com acesso autorizado, concluindo a gravação do relatório pelo fluxo normal, sem alteração manual dos controles ou das permissões. A carga de produção no PostgreSQL não foi executada nesta atualização; o comando seguinte é `python main.py --etapa 6`.

## 16 de outubro de 2026 — identidade e representação municipal canônica

Inspecionados `camada_analitica.py`, `persistencia.py`, `schema.sql`, `config.py`, modelo e testes. A dimensão existente preserva versões dos atributos municipais pelo hash de conteúdo. O problema analítico decorre de usar o nome histórico como categoria, confundindo versão com identidade.

Adicionadas as views `dim_municipio_canonica` e `vw_fato_rendimento_escolar`, sem modificar os produtos da Etapa 5. A representação canônica usa o último ano observado na fato, desempate por frequência nesse ano e depois pelo menor hash em collation `C`. A investigação anterior à implementação encontrou zero empates no último ano e zero versões sem fato. A política para códigos sem observação e os relacionamentos Power BI estão documentados no modelo.

A instalação local aditiva foi confirmada em transação, sob o lock da carga. Resultado: 5.570 linhas canônicas, 5.570 códigos distintos, zero códigos nulos; 11.245 versões históricas preservadas e 2.588.324 linhas tanto na fato quanto na view. Exemplos conferidos: São Paulo (SAO PAULO / São Paulo), Embu das Artes (EMBU / Embu das Artes / EMBU DAS ARTES) e Campo Grande (Augusto Severo / AUGUSTO SEVERO / Campo Grande). Não foi necessária recarga de dados.

Testes adicionados em `test_persistencia.py`: caixa/acentuação, três mudanças de denominação, ano mais recente, frequência, hash, código textual com zero, nulos, cardinalidade da view, preservação histórica, instalação repetida e rollback. Os testes existentes continuam cobrindo fidelidade Parquet–staging, publicação repetida e falhas transacionais. A definição no schema inicial é conferida contra a migração. Suíte completa com integração habilitada: **77 aprovados**. Nenhum commit ou push realizado; alterações locais anteriores foram preservadas.

## 6 de outubro de 2026 — persistência da camada analítica

Implementado `src/pipeline/persistencia.py` e integrado o comando `python main.py --etapa 6`. A carga utiliza exclusivamente os produtos publicados da Etapa 5 e a configuração local `.env`, com usuário da aplicação. O schema SQL e os Parquets de origem permanecem preservados.

O carregador captura uma cópia temporária dos arquivos, verificando hashes SHA-256 antes/depois, schemas, anos e contagens do relatório de consolidação. O manifesto registra arquivos, tamanhos, datas, hashes, período, contagens, avisos da origem e identidade Git do carregador. A versão produtora dos Parquets é desconhecida; o commit atual não é atribuído retroativamente a eles.

`psycopg` 3 usa COPY para quatro tabelas temporárias por sessão. A staging conserva os atributos redundantes da fato para conferi-los antes da projeção relacional. A dimensão escolar recebe a referência municipal por correspondência única de código, nome, UF e região, com comparação que preserva NULLs. Os códigos INEP e hashes são texto; métricas float64 não são arredondadas. NULL Arrow vira NULL SQL; NaN não nulo, infinito ou taxa fora de [0,100] bloqueiam a carga.

A transferência inteira é conferida por digest de linhas tipadas lidas de volta da staging. Antes da publicação, são validados unicidade, obrigatoriedade, hashes, FKs, atributos históricos, catálogo integral, contagens totais/anuais e nulos por métrica. A publicação substitui os dados por DELETE/INSERT numa única transação, respeitando as FKs. FULL JOIN por chaves únicas e não nulas, comparação de todas as colunas com IS DISTINCT FROM e contagens finais iguais verificam a fidelidade staging–definitivas antes do COMMIT.

O advisory lock serializa carregadores. Cada execução recebe UUID; `em_execucao` é confirmado separadamente, e a ativação do sucesso ocorre na transação dos dados. Falhas revertem a publicação e registram diagnóstico em nova transação. Uma resposta perdida ao COMMIT é reconciliada consultando o UUID, sem sobrescrever sucesso confirmado. Sem acesso ao banco, o resultado fica indeterminado. Reexecuções não duplicam dados e preservam o histórico de controles.

Pré-condições e limites: o schema precisa existir; a captura deve ocorrer fora da publicação da Etapa 5; o usuário precisa de permissões para carga e staging; deve haver espaço para snapshot, staging, dados e WAL. Reduções de período/contagens em relação à carga ativa são bloqueadas para revisão explícita da origem. O commit e o indicador de alterações locais descrevem o carregador utilizado.

## Testes

- `python -m pytest -q`: **54 aprovados, 18 pulados**; os pulados exigem PostgreSQL.
- Com `INEP_TEST_INTEGRATION=1`: **72 aprovados**, incluindo os 34 testes anteriores; última execução da suíte completa em 8,77 segundos.
- Integração em schemas descartáveis: duplicidades, FKs, divergência municipal inclusive NULL, atributos históricos, taxas inválidas, catálogo incompatível e hashes inválidos.
- Duas publicações idênticas mantêm contagens e uma única carga ativa; uma falha injetada após DELETE e inserções dimensionais reverte todos os dados.
- O fluxo completo registra falha após rollback em transação separada. A simulação de resposta perdida após COMMIT recupera sucesso pelo UUID.
- O lock impede dois carregadores simultâneos. Códigos com zeros e geografia parcial sem município são preservados.

Os testes opcionais criam e removem somente schemas de teste; não publicam dados nas tabelas analíticas reais.

## Cargas completas e conferência independente

A primeira carga desta sessão foi confirmada com UUID `07336d70-9a26-44e3-896d-1baa8a6e850c`, status `sucesso` e duração total de **530,679 segundos** (8 min 50,679 s). A validação integral Parquet–staging e staging–definitivas não encontrou divergências.

| Produto | Parquet | PostgreSQL confirmado após duas cargas |
| --- | ---: | ---: |
| Linhas da fato | 2.588.324 | 2.588.324 |
| Versões escolares | 515.873 | 515.873 |
| Versões municipais | 11.245 | 11.245 |
| Registros do catálogo | 270 | 270 |
| Colunas de métricas | 54 | 54 |
| Período | 2007–2024 | 2007–2024 |

O banco confirmou 227.868 códigos escolares distintos e 5.570 códigos municipais distintos. As validações de duplicidades, chaves obrigatórias, hashes, FKs, município da escola/fato, atributos redundantes, catálogo e taxas retornaram zero divergências. O commit do carregador foi `186394bc2acf568552214ce086534ee53c811965`, com alterações locais (`codigo_modificado=true`).

Já havia histórico de controles e publicação ativa no banco antes desta sessão; esse histórico foi preservado.

A segunda carga completa foi confirmada com UUID `6207236f-481d-4d50-8f93-bb094e65902e`, status `sucesso` e duração total de **569,995 segundos** (9 min 29,995 s). Os digests da transferência dos quatro produtos são idênticos aos da primeira carga; as contagens e o período também. Os UUIDs são distintos e somente o segundo permanece com `carga_ativa=true`; o primeiro continua no histórico como sucesso inativo.

Uma conferência independente, em transação de leitura Repeatable Read, confirmou as contagens da tabela acima e os dois controles. Foram executadas consultas de COUNT(*) nas quatro tabelas, MIN/MAX de ano, duplicidades por ano/escola, FKs órfãs, coerência de município fato/escola, coerência de códigos e geografia escola/município e taxas inválidas/NaN/infinito. Todas as consultas de divergências retornaram **zero**. Os nomes das 54 métricas também foram conferidos contra os schemas Parquet e PostgreSQL. Hashes de todos os arquivos capturados, incluindo os controles da Etapa 5, continuaram iguais após as duas cargas.

A evidência independente está em `outputs/relatorios/verificacao_persistencia_postgresql.json`, com comparação lado a lado, contagens anuais, estado dos controles, idempotência de conteúdo e preservação da origem. O controle ativo registra início `2026-10-06 13:23:11.139498-03:00`, fim `2026-10-06 13:32:41.102568-03:00`, versão `etapa6-v1`, o commit já informado e `codigo_modificado=true`; manifesto e validações estão no banco e no relatório local.

Avisos: a publicação de origem da Etapa 5 possui status `aviso`, preservado no manifesto; nenhuma divergência foi encontrada nesta carga. A versão produtora dos Parquets permanece desconhecida e o carregador possui alterações locais identificadas no controle. Nenhuma credencial foi incluída nas evidências.

**Etapa 6 concluída:** implementação, testes, duas cargas completas, idempotência, rollback testado, comparação independente e documentação finalizados. Power BI permanece como trabalho futuro.

Os relatórios locais por UUID ficam em `outputs/relatorios/persistencia_<UUID>.json`; o resultado mais recente está em `relatorio_persistencia_postgresql.json`. Nenhum deles inclui credenciais.

## 6 de outubro de 2026 — revisão documental e reprodutibilidade

Após o fechamento da etapa 6, foi realizada revisão restrita à documentação, organização e dependências. O método e o modelo passaram a descrever a solução implementada no presente. A restrição municipal foi alinhada ao schema: FK preenchida exige código preenchido, mas FK nula não exige código nulo. O critério mais restritivo de correspondência única aplicado pelo carregador foi documentado separadamente.

A decisão anterior de manter testes exclusivamente locais, registrada no diário histórico em `docs/registros_locais/diario_tecnico.md`, foi substituída nesta revisão por sua inclusão no conjunto versionável do projeto. `tests/`, `pytest.ini` e o diagnóstico de conexão então existente deixaram de ser ignorados. As duas cópias de testes em `scripts/` foram removidas após comparação textual com os originais preservados em `tests/`; não continham casos adicionais. Os registros antigos e o manifesto CSV de descoberta foram preservados localmente.

As dependências foram separadas entre execução (`requirements.txt`) e desenvolvimento (`requirements-dev.txt`, incluindo o conjunto de execução). Foram mantidas pandas, NumPy, openpyxl, xlrd, PyArrow, psycopg e python-dotenv na execução. Pytest, matplotlib, Jupyter e ipykernel ficaram no conjunto de desenvolvimento. Os resultados das cargas anteriores permanecem como evidências datadas; não foi realizada nova carga no banco nesta revisão.

Validação desta revisão: `python -m pytest -q` coletou 72 testes e terminou com **54 aprovados e 18 de integração pulados**, em **5,75 segundos**. A integração não foi habilitada para preservar o banco nesta tarefa. Os imports da pipeline e os leitores Excel foram conferidos no ambiente existente, e o conjunto de execução cobre as dependências identificadas. Código funcional, schema, dados e evidências das cargas anteriores foram preservados; não foi criado commit nem implementado Power BI.
