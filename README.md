# Pipeline de Dados Educacionais do INEP

Projeto de Trabalho de Conclusão de Curso em Engenharia da Computação para processamento de Taxas de Rendimento Escolar do INEP, em nível de escola. A pipeline descobre, inspeciona, audita, padroniza e consolida os dados; depois publica a camada analítica no PostgreSQL.

As etapas 1–6 estão implementadas. O recorte de layouts validado é **2007–2024**. Power BI é uma etapa futura. A pipeline não calcula médias municipais, ponderações, indicadores compostos ou índice de vulnerabilidade escolar.

## Como funciona

```text
Excel do INEP
  → 1. Descoberta dos arquivos
  → 2. Ingestão e inspeção das planilhas
  → 3. Auditoria estrutural
  → 4. Limpeza e padronização anual
  → 5. Consolidação histórica e preparação da camada analítica
  → 6. Persistência da camada analítica no PostgreSQL
  → Consultas aos dados
```

| Etapa | Resultado principal |
| --- | --- |
| 1 | Inventário dos arquivos encontrados, anos e caminhos. |
| 2 | Relatório de leitura, abas e cabeçalhos das planilhas. |
| 3 | Relatórios das diferenças estruturais entre arquivos e abas. |
| 4 | Parquets anuais padronizados em `data/interim/`. |
| 5 | Histórico consolidado e camada analítica em `data/processed/`. |
| 6 | Dados publicados no PostgreSQL, controle de carga e relatório de execução. |

**O fluxo completo usa dois comandos sequenciais:** `python main.py` executa as etapas 1–5; depois, `python main.py --etapa 6` publica os resultados no banco. Aguarde o término de cada comando e confira seu resultado antes de continuar.

## 1. Preparar o ambiente Python

Os exemplos abaixo usam **PowerShell no Windows**, com o terminal aberto na raiz do projeto, onde está `main.py`. O ambiente local foi validado com Python 3.12 e PostgreSQL 18.

Se ainda não existir um ambiente virtual, crie-o:

```powershell
py -3.12 -m venv .venv
```

Instale as dependências:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Os exemplos usam diretamente o Python da `.venv`, dispensando sua ativação. Em um terminal com o ambiente já ativado, você pode substituir `.\.venv\Scripts\python.exe` por `python`.

## 2. Preparar os arquivos do INEP

Obtenha manualmente os arquivos oficiais de **Taxas de Rendimento Escolar em nível de escola** e extraia os Excel em:

```text
data/raw/taxas_rendimento_escolar/
```

A descoberta percorre subpastas e seleciona `.xls` e `.xlsx` cujo caminho indica rendimento escolar por escola. Preserve nomes e organização que permitam identificar o ano. Uma organização possível é:

```text
data/raw/taxas_rendimento_escolar/
  2007/    arquivos Excel oficiais extraídos
  ...
  2024/    arquivos Excel oficiais extraídos
```

A pipeline não realiza download, web scraping ou extração automática de ZIPs. Não modifica os arquivos brutos. Novos anos ou layouts exigem revisão do catálogo de métricas antes do processamento.

**Os dados não acompanham o repositório.** `data/raw/`, `data/interim/`, `data/processed/` e `outputs/` são ignorados pelo Git. Em uma instalação nova, será necessário fornecer os arquivos de entrada e gerar os produtos. Consulte [fontes e preparação da entrada](docs/fontes_dados.md).

## 3. Executar o processamento — etapas 1–5

```powershell
.\.venv\Scripts\python.exe main.py
```

O terminal apresenta o resumo das etapas. Os relatórios detalhados são gravados em `outputs/relatorios/`:

| Arquivo | O que conferir |
| --- | --- |
| `inventario_arquivos.csv` | Arquivos selecionados, caminhos, anos e status. |
| `relatorio_ingestao.csv` | Leitura dos arquivos e erros encontrados. |
| `relatorio_auditoria.csv` e `relatorio_auditoria_abas.csv` | Diferenças estruturais e observações das abas. |
| `relatorio_limpeza.csv` | Bases anuais padronizadas e erros. |
| `relatorio_consolidacao.csv` | Publicação, período, contagens e qualidade do histórico e da camada analítica. |
| `schema_consolidacao.json` | Campos, tipos físicos e organização dos produtos publicados. |

Antes de usar os resultados, abra `relatorio_consolidacao.csv` e confira a linha **`TOTAL`**:

- `publicado=True`: os produtos foram publicados nessa execução.
- `status=ok`: execução sem apontamentos; `status=aviso`: publicação com ocorrências que precisam ser lidas nas observações.
- `status=erro` ou `publicado=False`: não use a tentativa como uma nova publicação; os produtos anteriores podem continuar presentes.
- Confira também os anos processados, as contagens e `relacionamentos_validados`.

As etapas iniciais registram erros por arquivo nos seus relatórios. Por isso, confira também esses relatórios para verificar se todos os arquivos esperados foram processados.

A etapa 5 processa lotes, prepara saídas temporárias e valida antes de substituir os produtos. Erros de publicação por exceção de I/O restauram as saídas anteriores; essa troca de arquivos não oferece garantia transacional contra desligamento abrupto. Falha da etapa 5 retorna código de saída 1.

### Onde estão os dados processados?

| Produto | Caminho | Uso |
| --- | --- | --- |
| Bases anuais padronizadas | `data/interim/taxas_rendimento_escolar_padronizada/` | Entrada da consolidação. |
| Histórico completo | `data/processed/taxas_rendimento_escolar_consolidada.parquet` | Análise histórica e rastreabilidade; permanece somente em Parquet. |
| Taxas analíticas por ano | `data/processed/dashboard/taxas/ano=<ano>/taxas.parquet` | Uma linha por ano e código escolar, com 54 métricas harmonizadas. |
| Dimensões e catálogo | `data/processed/dashboard/dim_escolas.parquet`, `dim_municipios.parquet` e `dim_metricas.parquet` | Atributos históricos de escolas/municípios e interpretação das métricas. |

A pasta `dashboard/` contém dados preparados para consumo, não uma aplicação de dashboard.

## 4. Preparar o PostgreSQL

As etapas 1–5 funcionam sem PostgreSQL. Para executar a etapa 6, são necessários:

- Serviço PostgreSQL em execução.
- Banco de destino e usuário da aplicação criados; no ambiente local, `inep` e `inep_app`.
- As cinco tabelas definidas em [schema.sql](src/pipeline/banco/schema.sql) já criadas no banco de destino.
- Permissões de conexão, uso do schema `public`, criação de tabelas temporárias e leitura/escrita nas tabelas da aplicação. O usuário precisa ser proprietário dos objetos ou receber os privilégios adequados.
- Espaço para a cópia temporária local, staging, dados publicados e WAL do PostgreSQL.

A criação do banco, do usuário e das tabelas é uma preparação externa à pipeline. Em uma instalação nova, um administrador deve configurar esses recursos; no pgAdmin, o schema pode ser executado no Query Tool conectado ao banco de destino. Execute o script de criação apenas na preparação inicial de um banco sem essas tabelas. **No ambiente local deste projeto, essa preparação já foi realizada.** O carregador não cria nem recria automaticamente as tabelas definitivas.

Se `.env` ainda não existir, copie `.env.example` para `.env` na raiz do projeto e configure:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=inep
POSTGRES_USER=inep_app
POSTGRES_PASSWORD=
```

Preencha a senha real somente no `.env` local. A etapa 6 lê exclusivamente esse arquivo; variáveis do terminal não substituem sua configuração. `.env` é ignorado pelo Git. Use o usuário da aplicação; o carregador rejeita o usuário `postgres`.

## 5. Executar a persistência — etapa 6

Após conferir a publicação da etapa 5:

```powershell
.\.venv\Scripts\python.exe main.py --etapa 6
```

Esse comando consome apenas os produtos existentes; não executa as etapas anteriores. São obrigatórios:

- Os três Parquets de dimensões/catálogo e as partições de taxas em `data/processed/dashboard/`.
- `outputs/relatorios/relatorio_consolidacao.csv`, com publicação válida.
- `outputs/relatorios/schema_consolidacao.json`.

Não execute a etapa 6 simultaneamente com a publicação da etapa 5. O carregador captura uma cópia temporária dos arquivos e verifica hashes antes/depois, schemas, período e contagens. Essa captura não altera a origem.

A carga utiliza `psycopg` 3 e COPY para quatro tabelas temporárias da sessão. Valida todo o conteúdo transferido, chaves, duplicidades, relacionamentos, atributos históricos, taxas e catálogo. Depois substitui as tabelas analíticas por DELETE/INSERT em **uma única transação**, junto com a atualização do controle de carga. Uma falha nessa publicação executa rollback e preserva a versão anterior.

Reexecutar a mesma origem não duplica registros: mantém o conteúdo e cria um novo UUID em `controle_carga`. Apenas a publicação mais recente fica ativa. Um advisory lock serializa os carregadores. Redução de período ou contagens frente à carga ativa bloqueia a substituição e exige revisão da origem.

### Como confirmar o resultado?

O terminal informa UUID, status, duração e linhas publicadas. Procure **`Status: sucesso`**. O relatório atual fica em:

```text
outputs/relatorios/relatorio_persistencia_postgresql.json
```

Cada execução também mantém `persistencia_<UUID>.json`, com manifesto de origem, hashes, contagens, validações e diagnóstico sem credenciais. Falhas retornam código de saída 1. Se houver perda de resposta ao COMMIT, o carregador consulta o UUID para reconciliar o resultado; sem acesso ao banco, registra resultado indeterminado, que deve ser conferido antes de repetir a carga.

Nas duas cargas completas validadas, a etapa 6 levou aproximadamente 9 minutos. O tempo depende do ambiente, volume e estado do banco.

## 6. Consultar os dados

No **pgAdmin**, conecte-se ao banco `inep` e abra o **Query Tool**. Execute as consultas abaixo com um usuário que tenha permissão de leitura.

### Verificar a publicação ativa

```sql
SELECT id_execucao, status, inicio, fim, quantidade_linhas,
       quantidade_escolas, quantidade_municipios
FROM public.controle_carga
WHERE carga_ativa = true;
```

Após uma carga confirmada, deve existir uma única linha ativa, com status `sucesso`.

### Conferir volume e período

```sql
SELECT COUNT(*) AS linhas, MIN(ano) AS ano_minimo, MAX(ano) AS ano_maximo
FROM public.fato_rendimento_escolar;

SELECT ano, COUNT(*) AS escolas_no_ano
FROM public.fato_rendimento_escolar
GROUP BY ano
ORDER BY ano;
```

### Consultar uma amostra de escolas de 2024

```sql
SELECT f.ano, f.co_entidade, e.no_entidade,
       e.no_municipio, e.sg_uf,
       f.tap_fun, f.tre_fun, f.tab_fun
FROM public.fato_rendimento_escolar AS f
JOIN public.dim_escola AS e ON e.id_escola = f.id_escola
WHERE f.ano = 2024
ORDER BY f.co_entidade
LIMIT 20;
```

`tap_fun`, `tre_fun` e `tab_fun` representam os percentuais de aprovação, reprovação e abandono do ensino fundamental. Para consultar outra UF, acrescente, por exemplo, `AND e.sg_uf = 'SP'` antes do `ORDER BY`.

### Consultar o histórico de uma escola

Substitua o código fictício pelo código da escola desejada, mantendo as aspas:

```sql
SELECT f.ano, f.co_entidade, e.no_entidade, e.no_municipio,
       f.tap_fun, f.tre_fun, f.tab_fun
FROM public.fato_rendimento_escolar AS f
JOIN public.dim_escola AS e ON e.id_escola = f.id_escola
WHERE f.co_entidade = '00123456'
ORDER BY f.ano;
```

### Cuidados para interpretar os dados

- Códigos INEP são texto: preserve zeros à esquerda.
- Taxas são percentuais; NULL representa ausência, não zero.
- `id_escola` e `id_municipio` identificam versões de atributos históricos. Faça as junções por esses IDs; juntar apenas pelo código pode multiplicar registros.
- O catálogo tem vários aliases/períodos por métrica. Não o junte à fato apenas por `coluna_analitica`, pois isso multiplica linhas.
- As métricas têm recortes sobrepostos; não some recortes nem interprete uma média simples de taxas escolares como taxa municipal.
- Nomes harmonizados não garantem, sozinhos, comparabilidade metodológica entre todos os anos. Consulte o [dicionário de dados](docs/dicionario_dados.md) e a [metodologia](docs/metodologia.md).

### Ler a camada analítica sem usar o banco

Também é possível consultar os Parquets em Python. Para recuperar o ano do caminho das partições, use `partitioning="hive"`:

```python
import pyarrow.dataset as ds

taxas = ds.dataset(
    "data/processed/dashboard/taxas",
    format="parquet",
    partitioning="hive",
)
amostra = taxas.head(
    20,
    columns=["ano", "co_entidade", "tap_fun", "tre_fun", "tab_fun"],
    filter=ds.field("ano") == 2024,
).to_pandas()
print(amostra)
```

Execute o exemplo na raiz do projeto com o ambiente Python configurado.

## Reexecuções e comandos disponíveis

| Comando, com o ambiente ativado | Comportamento |
| --- | --- |
| `python main.py` | Executa as etapas 1–5. |
| `python main.py --etapa 1` | Executa descoberta e inventário. |
| `python main.py --etapa 2` | Executa etapas 1 e 2. |
| `python main.py --etapa 3` | Executa etapas 1–3. |
| `python main.py --etapa 4` | Executa etapas 1–4. |
| `python main.py --etapa 5` | Executa somente a consolidação dos Parquets anuais existentes. |
| `python main.py --etapa 6` | Executa somente a persistência dos produtos analíticos existentes. |
| `python main.py --help` | Mostra as opções disponíveis. |

**A etapa 4 reutiliza os Parquets anuais existentes por padrão.** Substituir um Excel e executar `main.py` novamente não regenera automaticamente a base daquele ano. Para uma fonte corrigida, regenere explicitamente a base anual correspondente antes de consolidar; a função `gerar_base_padronizada` oferece `sobrescrever=True`, mas não há opção equivalente na CLI atual. Depois execute novamente a etapa 5, confira a publicação e execute a etapa 6. Consulte a [metodologia](docs/metodologia.md) antes de regenerar bases existentes.

Se os dados já estão processados e carregados, você pode começar pelas consultas. Execute a etapa 5 quando precisar reconsolidar os anuais existentes e a etapa 6 quando precisar publicar a camada analítica no banco.

## Organização e documentação

```text
main.py          entrada dos comandos
src/pipeline/    código das etapas e schema SQL
requirements.txt dependências do ambiente
.env.example     modelo de configuração PostgreSQL
.env             configuração local, ignorada pelo Git
data/raw/        arquivos originais fornecidos pelo usuário
data/interim/    bases anuais padronizadas
data/processed/  histórico e camada analítica
outputs/         relatórios e evidências locais
docs/            documentação do projeto
```

Documentação complementar:

- [Estrutura e etapas](docs/guia_estrutura_projeto.md).
- [Fontes e preparação da entrada](docs/fontes_dados.md).
- [Metodologia](docs/metodologia.md).
- [Dicionário e contrato de dados](docs/dicionario_dados.md).
- [Modelo PostgreSQL e garantias da carga](docs/modelo_banco_dados.md).
- [Diário técnico e resultados reais](docs/diario_tecnico.md).
