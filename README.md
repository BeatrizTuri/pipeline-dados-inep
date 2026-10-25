# Pipeline de dados do INEP

Projeto de TCC para processar as Taxas de Rendimento Escolar por escola, com layouts revisados de **2007 a 2025**. As etapas 1–6 estão implementadas; o relatório Power BI é configurado separadamente.

```text
Excel → padronização → histórico e camada analítica → PostgreSQL → Power BI
```

A pipeline preserva os arquivos brutos e os atributos históricos. Não calcula taxas municipais, médias ponderadas ou indicadores de vulnerabilidade.

## 1. Instalar

No PowerShell, na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para executar os testes:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### Arquivos de dependências

- `requirements.txt`: dependências diretas necessárias à pipeline.
- `requirements-dev.txt`: inclui as dependências da pipeline e o Pytest para os testes.
- `requirements-lock.txt`: registro das versões do ambiente local de desenvolvimento, incluindo dependências transitivas e ferramentas opcionais, como Jupyter e Matplotlib. Essas ferramentas não são necessárias para executar a pipeline atual.

Para uma instalação enxuta, utilize `requirements.txt` ou `requirements-dev.txt`, conforme os comandos acima. O arquivo `requirements-lock.txt` preserva o registro do ambiente mais amplo; não é um lock mínimo da aplicação nem uma garantia de compatibilidade com outros sistemas. Os dois arquivos de instalação não fixam versões.

## 2. Preparar os arquivos

Obtenha e extraia manualmente as planilhas do INEP em `data/raw/taxas_rendimento_escolar/`. Preserve o ano no nome ou caminho. A descoberta procura arquivos `.xls` e `.xlsx` em subpastas; não extrai ZIPs nem realiza downloads.

Novos anos exigem revisão do catálogo em `src/pipeline/metricas.py`. Anos posteriores a 2025 ainda não são aceitos.

## 3. Processar as planilhas

```powershell
.\.venv\Scripts\python.exe main.py
```

Executa as etapas 1–5: descoberta, ingestão, auditoria, limpeza e consolidação. Para executar somente a Etapa 5, usando as bases anuais existentes:

```powershell
.\.venv\Scripts\python.exe main.py --etapa 5
```

`--etapa 1` a `--etapa 4` executam desde o início até a etapa escolhida.

## 4. Conferir a publicação

Os produtos ficam em:

- `data/interim/taxas_rendimento_escolar_padronizada/`: bases anuais.
- `data/processed/taxas_rendimento_escolar_consolidada.parquet`: histórico completo.
- `data/processed/dashboard/`: taxas escolares por ano, dimensões e catálogo.
- `outputs/relatorios/`: ocorrências, contagens e resultados.

Confira a linha `TOTAL` de `relatorio_consolidacao.csv`: a carga no banco exige `publicado=True` e status `ok` ou `aviso`. `erro` bloqueia a carga; leia a observação da linha que falhou. Avisos registram ocorrências previstas pelo [contrato de dados](docs/dicionario_dados.md).

## 5. Executar a persistência — Etapa 6

Antes da primeira carga:

1. Prepare o PostgreSQL com banco e usuário da aplicação.
2. Crie o arquivo local `.env`, seguindo `.env.example`, com host, porta, banco, usuário e senha. Não versione esse arquivo.
3. Execute `src/pipeline/banco/schema.sql` no banco de destino para criar as tabelas. Faça isso somente em um banco novo.

Depois de uma publicação válida da Etapa 5:

```powershell
.\.venv\Scripts\python.exe main.py --etapa 6
```

O comando instala as views de `banco/canonica.sql`, valida a entrada e substitui os dados analíticos em uma transação. Uma falha antes do commit desfaz a substituição. Repetir a mesma carga não acumula dados duplicados; cada execução recebe seu próprio registro de auditoria.

Confira `Status: sucesso` e `outputs/relatorios/relatorio_persistencia_postgresql.json`. Em falha de conexão, confira o serviço, a configuração local e as permissões. Em status indeterminado, consulte o UUID no banco antes de repetir a carga.

## 6. Usar no Power BI

Use `dim_municipio_canonica` para os nomes municipais e `vw_fato_rendimento_escolar` para as observações. Relacione-as por `co_municipio`, de um para muitos, com filtro único. Os códigos devem permanecer texto.

A atualização do banco não troca os campos já usados pelos gráficos. A origem da fato, os relacionamentos e os filtros precisam seguir o [modelo do banco](docs/modelo_banco_dados.md#power-bi).

## Testes

Na raiz do projeto, com o ambiente virtual ativado e `requirements-dev.txt` instalado:

```powershell
# 59 casos independentes do PostgreSQL
python -m pytest

# 23 casos de integração (somente após preparar o ambiente abaixo)
python -m pytest -m integration
```

O padrão exclui o marcador `integration`; o argumento explícito `-m integration` substitui essa seleção. Os 82 casos foram mantidos. Não é necessário definir `INEP_TEST_INTEGRATION`.

### Preparar a integração PostgreSQL

Uma única vez, um administrador deve criar um usuário exclusivo e o banco vazio `inep_test`. Exemplo para executar manualmente no `psql`, conectado a um banco administrativo, fora de uma transação:

```sql
CREATE ROLE inep_test_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
\password inep_test_app
CREATE DATABASE inep_test OWNER inep_test_app;
```

`\password` solicita a senha sem colocá-la no comando SQL. Não use o usuário da pipeline ou um usuário administrativo para os testes. O usuário de testes precisa de `CONNECT`, `CREATE` e `TEMPORARY` em `inep_test`, disponíveis por ser proprietário do banco, e da propriedade dos objetos que cria. Não precisa criar bancos nem papéis. Não lhe conceda acesso às tabelas de `inep`, associação ao papel da aplicação ou outros privilégios administrativos. Em uma instância compartilhada, o administrador deve revisar também privilégios herdados de papéis e de `PUBLIC`; outra instância oferece separação adicional de recursos.

Na raiz do projeto:

```powershell
Copy-Item .env.test.example .env.test
```

Preencha localmente a senha e os dados de conexão em `.env.test`, mantendo `POSTGRES_DB=inep_test`. Esse arquivo é ignorado pelo Git. Preserve o `.env` principal. Não é necessário copiar dados reais nem executar `schema.sql` manualmente: as fixtures criam os objetos com dados artificiais.

Cada conexão, inclusive as secundárias e de recuperação, exige a configuração de `.env.test` e confirma banco, usuário e ausência de privilégios de superusuário, criação de bancos e criação de papéis antes de criar objetos. Configuração ausente ou destino diferente de `inep_test` causa erro, sem fallback para `.env`. Os testes criam schemas `teste_etapa6_<uuid>` e os removem ao terminar. Uma interrupção abrupta pode deixar schemas residuais; confira-os somente no banco de testes. Execute a integração sequencialmente, pois os testes compartilham chaves de advisory lock.

Para verificar somente a seleção, sem abrir conexões:

```powershell
python -m pytest --collect-only -q
python -m pytest -m integration --collect-only -q
```

Para registrar resultados no TCC, acrescente `--junitxml=outputs/testes-independentes.xml` ou `--junitxml=outputs/testes-integracao.xml` ao comando correspondente. Registre também revisão do código e versões do ambiente. A aprovação dos dados artificiais não substitui a auditoria do histórico publicado.

O [guia dos testes](docs/guia_testes.md) explica os casos, como habilitar integração PostgreSQL e os limites das verificações. Cada função de teste tem sua explicação no código.

## Documentação

- [Estrutura](docs/guia_estrutura_projeto.md): onde está cada responsabilidade.
- [Fontes](docs/fontes_dados.md): obtenção e preparação da entrada.
- [Metodologia](docs/metodologia.md): regras de transformação e qualidade.
- [Dicionário](docs/dicionario_dados.md): campos, tipos e métricas.
- [Modelo do banco](docs/modelo_banco_dados.md): relações, carga e Power BI.

Dados, relatórios, registros pessoais, credenciais, ambientes virtuais e caches ficam fora do Git.
