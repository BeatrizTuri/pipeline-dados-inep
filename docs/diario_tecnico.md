# Diário técnico

## 2026-05-14 - Etapa 1: configuração e descoberta de arquivos

- Arquivos alterados: `src/pipeline/config.py`, `src/pipeline/descoberta_arquivos.py`, `main.py`, `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`.
- Objetivo: criar a base inicial da pipeline para localizar arquivos brutos relevantes de Taxas de Rendimento Escolar por escola.
- Resultado: implementada descoberta recursiva de arquivos `.xlsx` e `.xls`, ignorando arquivos auxiliares e gerando `outputs/relatorios/inventario_arquivos.csv`.
- Pendências: validar o inventário gerado com os arquivos reais disponíveis em `data/raw/taxas_rendimento_escolar/`.
- Próximo passo: após aprovação, iniciar a Etapa 2 de ingestão dos arquivos Excel.

## 2026-05-19 - Etapa 2: ingestão dos arquivos Excel

- Arquivos alterados: `src/pipeline/config.py`, `src/pipeline/descoberta_arquivos.py`, `src/pipeline/ingestao.py`, `main.py`, `requirements.txt`, `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`.
- Objetivo: abrir os arquivos Excel encontrados no inventário e registrar informações básicas da leitura.
- Resultado: implementada leitura dos arquivos `.xlsx` e `.xls`, seleção da aba mais provável, detecção automática da linha de cabeçalho e geração de `outputs/relatorios/relatorio_ingestao.csv`.
- Pendências: validar a execução em ambiente com `pandas`, `openpyxl` e `xlrd` instalados.
- Próximo passo: após aprovação, iniciar a Etapa 3 de auditoria dos dados.

## 2026-06-08 - Ajustes e Etapa 3: auditoria estrutural dos arquivos

- Arquivos alterados: `src/pipeline/config.py`, `src/pipeline/descoberta_arquivos.py`, `src/pipeline/ingestao.py`, `src/pipeline/auditoria.py`, `main.py`, `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`.
- Objetivo: corrigir a identificação do ano em arquivos com data de atualização no nome, validar a ingestão com dependências instaladas e iniciar a auditoria estrutural.
- Resultado: criado ambiente `.venv`, instaladas dependências, corrigida extração do ano de 2010, otimizada a coleta de metadados da ingestão e implementado `outputs/relatorios/relatorio_auditoria.csv`.
- Validação: `main.py` executado com sucesso, com 18 arquivos relevantes, 18 leituras de ingestão sem erro e auditoria gerada.
- Pendências: decidir como tratar anos antigos organizados por abas regionais antes da consolidação histórica.
- Próximo passo: usar o relatório de auditoria para definir a regra de ingestão/combinação das abas regionais na etapa seguinte.

## 2026-06-08 - Continuação da Etapa 3: auditoria por aba e dicionário inicial

- Arquivos alterados: `src/pipeline/config.py`, `src/pipeline/auditoria.py`, `main.py`, `docs/dicionario_dados.md`, `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`.
- Objetivo: detalhar a auditoria dos arquivos antigos organizados por abas regionais e registrar um dicionário inicial de dados.
- Resultado: implementada geração de `outputs/relatorios/relatorio_auditoria_abas.csv`, com contagem de linhas, colunas, colunas de identificação e colunas de taxas por aba.
- Resultado adicional: criado dicionário inicial com campos canônicos, aliases encontrados e famílias de taxas.
- Pendência: definir, na próxima etapa, se a ingestão consolidada deve combinar automaticamente as abas regionais de 2007 a 2011.

## 2026-06-08 - Fechamento da Etapa 3

- Arquivos alterados: `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`.
- Objetivo: encerrar formalmente a etapa de auditoria antes de iniciar limpeza e padronização.
- Resultado: Etapa 3 considerada concluída para o recorte 2007 a 2024.
- Evidências geradas: `outputs/relatorios/relatorio_auditoria.csv`, `outputs/relatorios/relatorio_auditoria_abas.csv` e `docs/dicionario_dados.md`.
- Validação registrada: 18 arquivos relevantes, 18 arquivos lidos com sucesso, 43 abas auditadas, 30 abas regionais auditadas e 0 erros de auditoria.
- Decisão: os anos 2007 a 2011 deverão ter todas as abas regionais lidas na etapa posterior; a Etapa 3 não executa essa combinação.
- Próximo passo: iniciar a Etapa 4 de limpeza e padronização.

## 2026-08-20 - Etapa 4: limpeza e padronização

- Arquivos alterados: `src/pipeline/config.py`, `src/pipeline/limpeza.py`, `src/pipeline/auditoria.py`, `main.py`, `docs/dicionario_dados.md`, `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`.
- Objetivo: criar uma base intermediária anual com campos de identificação e taxas padronizados, sem consolidar ainda a série histórica final.
- Resultado: implementada geração de arquivos Parquet anuais em `data/interim/taxas_rendimento_escolar_padronizada/`.
- Resultado: implementada geração de `outputs/relatorios/relatorio_limpeza.csv`.
- Resultado: os anos 2007 a 2011 passaram a combinar todas as abas regionais dentro de cada arquivo anual padronizado.
- Ajuste técnico: a limpeza foi tornada idempotente, reutilizando Parquets anuais já existentes quando `sobrescrever=False`.
- Validação registrada: 18 arquivos padronizados, 0 erros, 2.588.399 linhas padronizadas e 54 colunas de taxas por ano.
- Próximo passo: iniciar a Etapa 5 de consolidação histórica da base padronizada.

## 2026-08-22 - Etapa 5: consolidação histórica

- Arquivos alterados: `src/pipeline/config.py`, `src/pipeline/consolidacao.py`, `main.py`, `docs/decisoes_metodologicas.md`, `docs/diario_tecnico.md`, `docs/dicionario_dados.md`, `docs/guia_estrutura_projeto.md`.
- Objetivo: reunir os arquivos anuais padronizados em uma base histórica única, preservando rastreabilidade.
- Resultado: implementada geração de `data/processed/taxas_rendimento_escolar_consolidada.parquet`.
- Resultado: implementada geração de `outputs/relatorios/relatorio_consolidacao.csv`.
- Decisão técnica: a consolidação usa a união das colunas de taxas entre períodos, porque os nomes padronizados ainda variam conforme o layout original de cada grupo de anos.
- Decisão técnica: registros sem `co_entidade` são descartados da base consolidada, pois não representam escolas identificáveis.
- Validação registrada: 18 anos consolidados, 2.588.399 linhas de entrada, 75 linhas descartadas, 2.588.324 linhas consolidadas, 219 colunas finais, 207 colunas de taxas, 0 duplicidades por `ano + co_entidade` e 0 erros.
- Próximo passo: iniciar etapa posterior de análise exploratória da base consolidada e definição metodológica dos indicadores.

## 2026-09-24 - Consolidação histórica e preparação da camada analítica

- Escopo aprovado: preparar dados para dashboard futuro, sem implementar interface, índice de vulnerabilidade ou indicadores compostos.
- A Etapa 5 passa a escrever o histórico tipado em lotes e derivar uma tabela analítica wide com 54 métricas, partições anuais e dimensões de escolas, municípios e métricas.
- Adicionados catálogo de aliases por período, validações de integridade e preservação de textos auxiliares em registros sem escola.
- Mantidos os módulos das etapas 1 a 4. O `main.py` continua coordenando a pipeline e permite executar somente a Etapa 5 com `--etapa 5`.
- Acrescentados testes artificiais para múltiplos anos, zeros à esquerda, ausências, schemas, duplicidades, valores inválidos, períodos de métricas, dimensões temporais, partições, reexecução e proteção das saídas anteriores.
- A decisão de agosto sobre descarte de linhas sem escola foi substituída pela preservação histórica documentada em `decisoes_metodologicas.md`.
- Validação automatizada: 24 testes passaram com dados artificiais (`python -m pytest -q`).
- Validação real: execução da Etapa 5 sobre os 18 Parquets anuais de 2007–2024, com 2.588.399 linhas históricas, 220 colunas históricas e 2.588.324 linhas analíticas em 18 partições. Nenhuma linha foi descartada do histórico.
- Qualidade observada: 75 linhas sem escola, 1.758 células textuais auxiliares preservadas em JSON, oito taxas negativas próximas de -0,1 em 2007, zero duplicidades por ano/escola identificada e 48 ocorrências excedentes de registros auxiliares com conteúdo repetido. Status final `aviso`, sem erros de execução.
- Dimensões publicadas: 515.873 versões de atributos escolares (227.868 códigos de escola distintos), 11.245 versões de atributos municipais (5.570 códigos distintos) e 270 aliases de métricas por período. As referências das 2.588.324 linhas analíticas às dimensões foram verificadas, assim como a leitura com filtro Hive por ano.

## 2026-10-01 - Fechamento da etapa de consolidação histórica e preparação da camada analítica

- Revisados todos os módulos da pipeline, o ponto de entrada, testes e documentação. Mantidos a arquitetura, as etapas 1 a 4 e o catálogo de métricas. Os relatórios locais anteriores das etapas 1 a 4 não registram erros; essas etapas não foram reexecutadas integralmente nesta revisão.
- Arquivos alterados: `src/pipeline/validacao_consolidacao.py`, `src/pipeline/consolidacao.py`, `src/pipeline/camada_analitica.py`, `tests/test_consolidacao.py`, `tests/test_camada_analitica.py`, `README.md`, `docs/dicionario_dados.md`, `docs/decisoes_metodologicas.md`, `docs/guia_estrutura_projeto.md` e este diário.
- Acrescentadas contagens de códigos malformados, listagem de colunas desconhecidas e validação dos relacionamentos nos Parquets antes da publicação. Dados suspeitos não são corrigidos nem descartados por essas verificações.
- O contrato documenta granularidade, chaves, tipos, nulabilidade, versões de atributos, catálogo de métricas, partições e regras para consumo externo. Nenhum banco de persistência, dashboard ou indicador foi implementado.
- Testes: 24 casos existentes passaram antes das alterações; 34 passaram depois, incluindo falhas de integridade dimensional com preservação das saídas, códigos inválidos e igualdade dos IDs entre reexecuções. Executado `.venv/Scripts/python.exe -m pytest -q`, pois o executável `python` global não estava acessível.
- Cabeçalhos: os 18 arquivos brutos apresentaram os 54 aliases esperados na aba inspecionada de cada arquivo. Conferidos também os cabeçalhos descritivos de 2015 e 2018, confirmando a mudança semântica de F04/F58 já representada no catálogo.
- Ajuste de desempenho da validação nova: uma busca vetorial nos 515.873 IDs escolares levou cerca de 4 segundos por lote; foi substituída por consulta em dicionário construído uma vez por dimensão, mantendo as mesmas regras. A função final validou integralmente os Parquets preparados em 15,27 segundos, e os 34 testes passaram novamente. Essa medição é específica do ambiente local.
- Execução real: `.venv/Scripts/python.exe main.py --etapa 5` terminou com código 0, `TOTAL.publicado=True`, `TOTAL.relacionamentos_validados=True` e status `aviso`. Essa execução principal já estava em andamento com a consulta vetorial anterior; a função otimizada foi validada separadamente sobre todos os mesmos Parquets antes de sua publicação.
- Resultado: 18 anos (2007–2024), 2.588.399 linhas históricas, 220 colunas históricas (207 de taxas), zero descarte histórico e 2.588.324 linhas analíticas em 18 partições, com 54 métricas harmonizadas. Dimensões: 515.873 versões escolares, 11.245 municipais e 270 aliases de métricas. Nenhuma divergência em relação ao registro de setembro.
- Reexecução: os hashes SHA-256 dos 22 Parquets publicados (histórico, 18 partições e três dimensões) são idênticos aos anteriores. Confirmada leitura Hive com 65 colunas lógicas, `ano` int32 e filtro de 2024 retornando 128.096 linhas.
- Qualidade: zero códigos malformados, zero duplicidades/conflitos de ano e escola identificada, nenhuma coluna desconhecida ou métrica esperada ausente, e todas as referências dimensionais válidas. Permanecem 75 linhas sem escola/município/UF, 1.758 células textuais auxiliares, oito taxas inválidas em 2007 e 48 ocorrências excedentes de registros auxiliares repetidos. Os 17 avisos anuais são aceitáveis para este fechamento porque os problemas são reportados, preservados no histórico e tratados conforme o contrato: linhas sem escola não entram na analítica e taxas fora da faixa ficam nulas nela, sem fabricar valores válidos.
- Conclusão: encerrada a etapa de processamento, consolidação histórica e preparação da camada analítica para o recorte e layouts validados. Os produtos estão prontos para futura persistência e consumo externo, observadas as regras de qualidade documentadas. Não foi iniciada integração com banco de dados ou Power BI. A restauração por exceções de I/O continua sem garantia transacional contra desligamento abrupto durante a publicação.
