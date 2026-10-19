"""Testes do contrato; integração usa schema descartável, nunca public."""
import os
import json
from contextlib import contextmanager
import uuid
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import psycopg
import pytest

from src.pipeline import persistencia as p
from src.pipeline.camada_analitica import ATRIBUTOS_ESCOLA, ATRIBUTOS_MUNICIPIO, SCHEMA_ANALITICO
from src.pipeline.metricas import COLUNAS_METRICAS, dimensao_metricas


def test_configuracao_ausente(tmp_path):
    """
    Falta arquivo de configuração → informa configuração ausente → evita tentar uma carga sem os
    parâmetros exigidos.
    """
    with pytest.raises(p.ErroPersistencia, match="Configuração ausente"):
        p.configuracao(tmp_path / "ausente")


@pytest.mark.parametrize("porta,usuario", [("abc", "inep_app"), ("0", "inep_app"), ("5432", "postgres")])
def test_configuracao_invalida(tmp_path, porta, usuario):
    """
    Porta `abc`, porta zero ou usuário `postgres` → recusa → aplica o contrato de conexão e uso
    de usuário da aplicação.
    """
    arquivo = tmp_path / ".env"
    arquivo.write_text(f"POSTGRES_HOST=localhost\nPOSTGRES_PORT={porta}\nPOSTGRES_DB=inep\nPOSTGRES_USER={usuario}\nPOSTGRES_PASSWORD=ficticia\n")
    with pytest.raises(p.ErroPersistencia):
        p.configuracao(arquivo)


@pytest.mark.parametrize("valor", [-0.1, 100.1, float("nan"), float("inf"), -float("inf")])
def test_taxa_invalida(valor):
    """
    Percentuais negativos, acima de 100, NaN não nulo ou infinitos → recusa o lote → impede
    entrada analítica inválida antes do envio ao banco.
    """
    lote = pa.record_batch([pa.array([valor], type=pa.float64(), from_pandas=False)], names=[COLUNAS_METRICAS[0]])
    with pytest.raises(p.ErroPersistencia, match="Taxa inválida"):
        p.validar_lote(lote)


def test_null_e_limites_preservados():
    """
    Usa ausência, 0% e 100% → aceita → evita confundir taxa limite válida ou ausência com erro.
    """
    p.validar_lote(pa.record_batch([pa.array([None, 0.0, 100.0])], names=[COLUNAS_METRICAS[0]]))


def test_metrica_inesperada():
    """
    Acrescenta coluna de taxa fora do schema → recusa → evita carregar produto incompatível com
    o contrato da Etapa 6.
    """
    with pytest.raises(p.ErroPersistencia, match="Schema"):
        p.validar_schema(SCHEMA_ANALITICO.append(pa.field("tap_nova", pa.float64())), SCHEMA_ANALITICO)


def test_identificador_numerico_rejeitado():
    """
    Troca o tipo do código escolar de texto para inteiro → recusa → evita aceitar um código
    cujos zeros podem ter sido perdidos.
    """
    schema = pa.schema([pa.field(c.name, pa.int64() if c.name == "co_entidade" else c.type) for c in SCHEMA_ANALITICO])
    with pytest.raises(p.ErroPersistencia, match="texto"):
        p.validar_schema(schema, SCHEMA_ANALITICO)


def test_git_indisponivel(monkeypatch):
    """
    Simula ausência do Git → registra commit desconhecido → evita que a falta dessa
    identificação derrube a carga.
    """
    def falhar(*args, **kwargs):
        raise FileNotFoundError
    monkeypatch.setattr(p.subprocess, "check_output", falhar)
    assert p.identidade_git()["commit_pipeline"] is None


def test_produtos_ausentes(tmp_path):
    """
    Faltam os produtos analíticos → recusa → evita carregar somente parte dos arquivos
    obrigatórios.
    """
    with pytest.raises(p.ErroPersistencia, match="Produtos"):
        p.arquivos_origem(tmp_path)


def fontes(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    municipio = dict(id_municipio="a" * 64, co_municipio="0012345", no_municipio="Município", sg_uf="SP", no_regiao="Sudeste")
    escola = dict(id_escola="b" * 64, co_entidade="00123456", no_entidade="Escola", tipoloca="Urbana", dependad="Privada",
                  **{c: municipio[c] for c in ATRIBUTOS_MUNICIPIO})
    fato = {**{c: escola[c] for c in ATRIBUTOS_ESCOLA}, "id_escola": escola["id_escola"], "id_municipio": municipio["id_municipio"],
            **{c: None for c in COLUNAS_METRICAS}}
    fato[COLUNAS_METRICAS[0]] = 98.125
    for arquivo, dados in (("dim_municipios", municipio), ("dim_escolas", escola)):
        pq.write_table(pa.Table.from_pylist([dados], schema=pa.schema([(c, pa.string()) for c in dados])), origem / f"{arquivo}.parquet")
    dimensao_metricas().to_parquet(origem / "dim_metricas.parquet", index=False)
    taxas = origem / "taxas/ano=2024"
    taxas.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist([fato], schema=SCHEMA_ANALITICO), taxas / "taxas.parquet")
    relatorios = tmp_path / "relatorios"
    relatorios.mkdir()
    (relatorios / "relatorio_consolidacao.csv").write_text("ano,status,publicado,linhas_analiticas,anos_processados,observacao\nTOTAL,ok,True,1,2024,\n")
    schemas = {f.relative_to(origem).as_posix(): {c.name: str(c.type) for c in pq.ParquetFile(f).schema_arrow}
               for f in origem.rglob("*.parquet")}
    (relatorios / "schema_consolidacao.json").write_text(json.dumps({"schemas": schemas}))
    return origem, relatorios


def test_leitura_e_captura_parquets(tmp_path):
    """
    Captura pequenos produtos e controles válidos → confere contagens, hashes registrados e
    código com zeros na cópia → verifica o caminho válido da captura.
    """
    origem, relatorios = fontes(tmp_path)
    manifesto = p.capturar_origem(origem, tmp_path / "copia", relatorios)
    assert manifesto["quantidade_linhas"] == 1
    assert manifesto["anos"] == [2024]
    assert manifesto["quantidade_metricas_catalogo"] == 270
    assert all(len(f["sha256"]) == 64 for f in manifesto["arquivos"])
    escola = pq.read_table(tmp_path / "copia/dim_escolas.parquet").to_pylist()[0]
    assert escola["co_entidade"] == "00123456"


def test_captura_detecta_alteracao(tmp_path, monkeypatch):
    """
    Modifica o arquivo durante a cópia → recusa → evita capturar arquivos que mudam durante a
    leitura.
    """
    origem, relatorios = fontes(tmp_path)
    copiar = p.shutil.copyfile
    def alterar(src, dst):
        resultado = copiar(src, dst)
        if Path(src).name == "dim_escolas.parquet":
            Path(src).write_bytes(b"alterado")
        return resultado
    monkeypatch.setattr(p.shutil, "copyfile", alterar)
    with pytest.raises(p.ErroPersistencia, match="mudou"):
        p.capturar_origem(origem, tmp_path / "copia", relatorios)


@pytest.mark.parametrize("mudanca", ["publicacao", "schema", "contagem"])
def test_captura_rejeita_controle_divergente(tmp_path, mudanca):
    """
    Marca publicação inválida, informa schema errado ou contagem errada → recusa → evita confiar
    em controles incompatíveis com os arquivos.
    """
    origem, relatorios = fontes(tmp_path)
    if mudanca == "schema":
        (relatorios / "schema_consolidacao.json").write_text('{"schemas":{}}')
    else:
        arquivo = relatorios / "relatorio_consolidacao.csv"
        texto = arquivo.read_text()
        arquivo.write_text(texto.replace("True", "False") if mudanca == "publicacao" else texto.replace(",1,2024,", ",2,2024,"))
    with pytest.raises(p.ErroPersistencia):
        p.capturar_origem(origem, tmp_path / "copia", relatorios)


def test_falha_configuracao_gera_relatorio(tmp_path):
    """
    Executa a carga sem configuração → salva relatório de falha sem commit → evita falha sem
    diagnóstico local.
    """
    resultado = p.executar_persistencia(relatorios=tmp_path, arquivo_env=tmp_path / "ausente")
    assert resultado["status"] == "falha"
    assert resultado["commit_confirmado"] is False
    salvo = json.loads((tmp_path / "relatorio_persistencia_postgresql.json").read_text(encoding="utf-8"))
    assert salvo["id_execucao"] == resultado["id_execucao"]


class ConexaoIsolada:
    def __init__(self, conexao, schema):
        self.conexao, self.schema = conexao, schema
        self.falhar = False

    def execute(self, query, params=None):
        texto = query if isinstance(query, str) else query.as_string(self.conexao)
        texto = texto.replace("public.", f'"{self.schema}".')
        if self.falhar and texto.startswith("INSERT INTO") and "fato_rendimento_escolar" in texto:
            raise p.ErroPersistencia("Falha injetada após DELETE e inserções dimensionais")
        return self.conexao.execute(texto, params)

    def cursor(self, **kwargs):
        return self.conexao.cursor(**kwargs)

    def __getattr__(self, nome):
        return getattr(self.conexao, nome)

    def __enter__(self):
        self.conexao.__enter__()
        return self

    def __exit__(self, *args):
        return self.conexao.__exit__(*args)


@pytest.fixture
def banco(tmp_path):
    if os.getenv("INEP_TEST_INTEGRATION") != "1":
        pytest.skip("Integração opcional: INEP_TEST_INTEGRATION=1; schema isolado")
    schema = "teste_etapa6_" + uuid.uuid4().hex
    with psycopg.connect(**p.configuracao(), autocommit=True) as conexao:
        conexao.execute(f'CREATE SCHEMA "{schema}"')
        adaptada = ConexaoIsolada(conexao, schema)
        try:
            script = (p.PROJECT_ROOT / "src/pipeline/banco/schema.sql").read_text(encoding="utf-8")
            adaptada.execute(script.replace("BEGIN;", "").replace("COMMIT;", ""))
            p.instalar_views_canonicas(adaptada)
            origem, relatorios = fontes(tmp_path)
            manifesto = p.capturar_origem(origem, tmp_path / "copia", relatorios)
            with conexao.transaction():
                p.criar_staging(adaptada)
                for tabela, arquivos in {"dim_municipio": [origem / "dim_municipios.parquet"],
                    "dim_escola": [origem / "dim_escolas.parquet"], "catalogo_metricas": [origem / "dim_metricas.parquet"],
                    "fato_rendimento_escolar": [origem / "taxas/ano=2024/taxas.parquet"]}.items():
                    p.carregar_parquet(adaptada, tabela, arquivos)
            yield adaptada, manifesto
        finally:
            conexao.execute(f'DROP SCHEMA "{schema}" CASCADE')


@pytest.mark.integration
@pytest.mark.parametrize("mutacao", [
    "INSERT INTO stg_fato_rendimento_escolar SELECT * FROM stg_fato_rendimento_escolar",
    "UPDATE stg_fato_rendimento_escolar SET id_escola=repeat('c',64)",
    "UPDATE stg_fato_rendimento_escolar SET id_municipio=repeat('c',64)",
    "UPDATE stg_fato_rendimento_escolar SET id_municipio=NULL",
    "UPDATE stg_fato_rendimento_escolar SET no_entidade='Divergente'",
    "UPDATE stg_fato_rendimento_escolar SET tap_fun=-1",
    "UPDATE stg_fato_rendimento_escolar SET tap_fun=101",
    "UPDATE stg_fato_rendimento_escolar SET tap_fun='NaN'::float8",
    "UPDATE stg_fato_rendimento_escolar SET tap_fun='Infinity'::float8",
    "UPDATE stg_catalogo_metricas SET coluna_analitica='inesperada'",
    "UPDATE stg_dim_escola SET co_municipio='9999999'",
    "UPDATE stg_dim_escola SET id_escola='hash_invalido'",
    "UPDATE stg_dim_municipio SET co_municipio=NULL",
])
def test_validacoes_staging(banco, mutacao):
    """
    Altera um elemento da staging válida por vez → a validação recusa → evita publicar dados
    inconsistentes. As treze situações estão detalhadas abaixo.
    """
    conexao, manifesto = banco
    if mutacao.startswith("INSERT"):
        mutacao = "INSERT INTO stg_fato_rendimento_escolar SELECT " + ",".join(p.COLUNAS["fato_rendimento_escolar"] + ["_ord+1"] + p.EXTRAS_FATO) + " FROM stg_fato_rendimento_escolar"
    conexao.execute(mutacao)
    with pytest.raises(p.ErroPersistencia), conexao.conexao.transaction():
        p.validar_staging(conexao, manifesto, {})


def novo_controle(conexao):
    identificador = uuid.uuid4()
    conexao.execute("INSERT INTO public.controle_carga (id_execucao,inicio,status,versao_pipeline,manifesto_origem) VALUES (%s,clock_timestamp(),'em_execucao','teste','{}')", (identificador,))
    return identificador


@pytest.mark.integration
def test_idempotencia_e_rollback_real(banco):
    """
    Publica duas vezes e força erro antes de inserir a fato na terceira → mantém contagens, um
    controle ativo e o valor anterior → verifica reexecução e rollback no banco.
    """
    conexao, manifesto = banco
    validacoes = {}
    with conexao.conexao.transaction():
        contagens = p.validar_staging(conexao, manifesto, validacoes)
    ids = []
    for _ in range(2):
        ids.append(novo_controle(conexao))
        with conexao.conexao.transaction():
            p.publicar(conexao, ids[-1], contagens, validacoes)
        assert p.contagens_banco(conexao) == contagens
    assert conexao.execute("SELECT count(*) FROM public.controle_carga WHERE carga_ativa").fetchone()[0] == 1
    assert conexao.execute("SELECT id_execucao FROM public.controle_carga WHERE carga_ativa").fetchone()[0] == ids[-1]
    terceiro = novo_controle(conexao)
    conexao.falhar = True
    with pytest.raises(p.ErroPersistencia, match="injetada"), conexao.conexao.transaction():
        p.publicar(conexao, terceiro, contagens, {})
    conexao.falhar = False
    assert p.contagens_banco(conexao) == contagens
    assert conexao.execute("SELECT id_execucao FROM public.controle_carga WHERE carga_ativa").fetchone()[0] == ids[-1]
    assert conexao.execute("SELECT co_entidade,tap_fun FROM public.fato_rendimento_escolar").fetchone() == ("00123456", 98.125)


@pytest.mark.integration
def test_municipio_ausente_preserva_geografia(banco):
    """
    Retira código municipal da escola/fato → publica sem referência municipal, mantendo nome e
    UF da escola → evita perder atributos parciais conhecidos.
    """
    conexao, manifesto = banco
    conexao.execute("UPDATE stg_dim_escola SET co_municipio=NULL")
    conexao.execute("UPDATE stg_fato_rendimento_escolar SET co_municipio=NULL,id_municipio=NULL")
    with conexao.conexao.transaction():
        contagens = p.validar_staging(conexao, manifesto, {})
    identificador = novo_controle(conexao)
    with conexao.conexao.transaction():
        p.publicar(conexao, identificador, contagens, {})
    assert conexao.execute("SELECT id_municipio,co_municipio,no_municipio,sg_uf FROM public.dim_escola").fetchone() == (None, None, "Município", "SP")


@pytest.mark.integration
def test_lock_serializa_cargas():
    """
    Duas conexões tentam obter o mesmo lock de teste → somente uma obtém por vez → verifica a
    exclusão oferecida pelo lock. Não executa duas cargas completas em paralelo.
    """
    if os.getenv("INEP_TEST_INTEGRATION") != "1":
        pytest.skip("Integração opcional")
    chave = p.LOCK + 1  # Lock separado do carregador real.
    with psycopg.connect(**p.configuracao(), autocommit=True) as a, psycopg.connect(**p.configuracao(), autocommit=True) as b:
        assert a.execute("SELECT pg_try_advisory_lock(%s)", (chave,)).fetchone()[0]
        assert not b.execute("SELECT pg_try_advisory_lock(%s)", (chave,)).fetchone()[0]
        a.execute("SELECT pg_advisory_unlock(%s)", (chave,))
        assert b.execute("SELECT pg_try_advisory_lock(%s)", (chave,)).fetchone()[0]


@pytest.mark.integration
def test_fluxo_registra_falha_apos_rollback(banco, tmp_path, monkeypatch):
    """
    Após um sucesso, provoca falha no fluxo completo da carga → mantém os dados anteriores e
    registra a tentativa como falha → evita perder o diagnóstico junto com a transação
    revertida.
    """
    conexao, _ = banco
    conectar = psycopg.connect
    falhar = [False]
    def isolada(**kwargs):
        adaptada = ConexaoIsolada(conectar(**kwargs), conexao.schema)
        adaptada.falhar = falhar[0]
        return adaptada
    monkeypatch.setattr(p.psycopg, "connect", isolada)
    monkeypatch.setattr(p, "LOCK", p.LOCK + 2)
    pasta = tmp_path / "fluxo"
    pasta.mkdir()
    origem, relatorios = fontes(pasta)
    primeira = p.executar_persistencia(origem, relatorios)
    assert primeira["status"] == "sucesso"
    falhar[0] = True
    segunda = p.executar_persistencia(origem, relatorios)
    assert segunda["status"] == "falha"
    assert not segunda["commit_confirmado"]
    assert p.contagens_banco(conexao)["quantidade_linhas"] == 1
    assert str(conexao.execute("SELECT id_execucao FROM public.controle_carga WHERE carga_ativa").fetchone()[0]) == primeira["id_execucao"]
    controle = conexao.execute("SELECT status,carga_ativa,quantidade_linhas,mensagem_erro FROM public.controle_carga WHERE id_execucao=%s", (segunda["id_execucao"],)).fetchone()
    assert controle[:3] == ("falha", False, None)
    assert "injetada" in controle[3]


@pytest.mark.integration
def test_resposta_perdida_ao_commit_reconcilia_sucesso(banco, tmp_path, monkeypatch):
    """
    Simula confirmação no banco seguida de erro de comunicação → consulta o controle e reconhece
    sucesso → evita declarar falha de algo já confirmado. Não simula uma queda real de rede.
    """
    conexao, _ = banco
    conectar = psycopg.connect
    class RespostaPerdida(ConexaoIsolada):
        publicar = False

        def execute(self, query, params=None):
            resultado = super().execute(query, params)
            if isinstance(query, str) and "SET status='sucesso'" in query:
                self.publicar = True
            return resultado

        @contextmanager
        def transaction(self):
            with self.conexao.transaction():
                yield
            if self.publicar:
                self.publicar = False
                raise psycopg.OperationalError("Resposta ao COMMIT perdida após confirmação")
    monkeypatch.setattr(p.psycopg, "connect", lambda **kwargs: RespostaPerdida(conectar(**kwargs), conexao.schema))
    monkeypatch.setattr(p, "LOCK", p.LOCK + 3)
    pasta = tmp_path / "reconciliacao"
    pasta.mkdir()
    origem, relatorios = fontes(pasta)
    resultado = p.executar_persistencia(origem, relatorios)
    assert resultado["status"] == "sucesso"
    assert resultado["commit_confirmado"]
    assert resultado["divergencias"] == []
    assert "mensagem_erro" not in resultado
    assert conexao.execute("SELECT status,carga_ativa FROM public.controle_carga WHERE id_execucao=%s", (resultado["id_execucao"],)).fetchone() == ("sucesso", True)


@pytest.mark.integration
@pytest.mark.parametrize("nomes", [("SAO PAULO", "São Paulo"), ("Embu", "Embu das Artes"),
                                    ("Augusto Severo", "Campo Grande"), ("Campo de Santana", "Tacima")])
def test_municipio_canonico_historico_desempate(banco, nomes):
    """
    Usa quatro pares de nomes para o mesmo código e cria disputas entre versões → escolhe por
    ano, frequência e hash, preserva quatro versões e repete a instalação sem duplicar → protege
    a regra canônica e a cardinalidade da view da fato.
    """
    c, _ = banco
    # Código textual com zero; menor hash antigo não pode superar ano recente.
    for chave, nome in [("a", nomes[0]), ("b", nomes[1]), ("c", "Empate"), ("d", "Sem observação")]:
        c.execute("INSERT INTO public.dim_municipio VALUES (%s,'0012345',%s,'SP','Sudeste')",
                  (chave * 64, nome))
    def observar(chave, ano, numero):
        escola = format(numero, '064x')
        c.execute("INSERT INTO public.dim_escola(id_escola,co_entidade) VALUES (%s,%s)", (escola, str(numero)))
        c.execute("INSERT INTO public.fato_rendimento_escolar(ano,co_entidade,id_escola,id_municipio) VALUES (%s,%s,%s,%s)",
                  (ano, str(numero), escola, chave * 64))
    observar("a", 2007, 1)
    observar("b", 2024, 2)
    def conferir(nome):
        for _ in range(2):
            p.instalar_views_canonicas(c)
            assert c.execute("SELECT co_municipio,no_municipio,ano_referencia FROM public.dim_municipio_canonica").fetchall() == [("0012345", nome, 2024)]
        assert c.execute("SELECT count(*) FROM public.dim_municipio").fetchone()[0] == 4
        assert c.execute("SELECT count(*) FROM public.dim_municipio_canonica WHERE co_municipio IS NULL").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM public.vw_fato_rendimento_escolar WHERE co_municipio='0012345'").fetchone()[0] == c.execute("SELECT count(*) FROM public.fato_rendimento_escolar").fetchone()[0]
    conferir(nomes[1])
    observar("c", 2024, 3)
    conferir(nomes[1])  # Empate de ano/frequência: hash b precede c.
    observar("c", 2024, 4)
    conferir("Empate")  # Frequência somente no último ano.
    observar("b", 2024, 5)
    conferir(nomes[1])
    with pytest.raises(RuntimeError), c.conexao.transaction():
        c.execute("DELETE FROM public.fato_rendimento_escolar WHERE ano=2024")
        raise RuntimeError("rollback")
    conferir(nomes[1])


@pytest.mark.integration
def test_persistencia_2025_catalogo_e_canonica(banco):
    """
    Muda a observação artificial para 2025 e publica → fato, ano canônico e catálogo incluem
    2025 → verifica o caminho do novo ano no PostgreSQL.
    """
    c, manifesto = banco
    c.execute("UPDATE stg_fato_rendimento_escolar SET ano=2025")
    manifesto.update(anos=[2025], ano_minimo=2025, ano_maximo=2025)
    with c.conexao.transaction():
        validacoes = {}
        contagens = p.validar_staging(c, manifesto, validacoes)
        identificador = novo_controle(c)
        p.publicar(c, identificador, contagens, validacoes)
    assert c.execute("SELECT ano FROM public.vw_fato_rendimento_escolar").fetchone() == (2025,)
    assert c.execute("SELECT ano_referencia FROM public.dim_municipio_canonica").fetchone() == (2025,)
    assert c.execute("SELECT DISTINCT ano_fim FROM public.catalogo_metricas WHERE ano_inicio=2021").fetchall() == [(2025,)]
