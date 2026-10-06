# Diário técnico — Etapa 6

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
