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

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

O [guia dos testes](docs/guia_testes.md) explica os casos, como habilitar integração PostgreSQL e os limites das verificações. Cada função de teste tem sua explicação no código.

## Documentação

- [Estrutura](docs/guia_estrutura_projeto.md): onde está cada responsabilidade.
- [Fontes](docs/fontes_dados.md): obtenção e preparação da entrada.
- [Metodologia](docs/metodologia.md): regras de transformação e qualidade.
- [Dicionário](docs/dicionario_dados.md): campos, tipos e métricas.
- [Modelo do banco](docs/modelo_banco_dados.md): relações, carga e Power BI.
- [Diário técnico](docs/diario_tecnico.md): decisões e evidências datadas.

Dados, relatórios, credenciais, ambientes virtuais e caches ficam fora do Git. Os resultados das execuções reais estão registrados no diário técnico.
