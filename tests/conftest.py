"""Proteções exclusivas da integração; a coleta nunca abre conexões."""

import psycopg
import pytest

from src.pipeline import persistencia as p


@pytest.fixture(autouse=True)
def proteger_integracao(request, monkeypatch):
    if request.node.get_closest_marker("integration") is None:
        return

    arquivo = p.PROJECT_ROOT / ".env.test"
    if not arquivo.is_file():
        pytest.fail("Integração exige .env.test; copie .env.test.example e configure inep_test.", pytrace=False)
    try:
        config = p.configuracao(arquivo)
    except p.ErroPersistencia:
        pytest.fail("Configuração inválida ou incompleta no .env.test.", pytrace=False)
    if config["dbname"] != "inep_test":
        pytest.fail("Integração permitida exclusivamente no banco inep_test.", pytrace=False)

    conectar_original = psycopg.connect

    def configuracao_teste(caminho=None):
        # Inclusive chamadas internas do fluxo e da recuperação ignoram o .env principal.
        return config.copy()

    def conectar_protegido(*args, **kwargs):
        esperado = {**config, "autocommit": True}
        if args or kwargs != esperado:
            raise p.ErroPersistencia("Conexão de integração fora da configuração autorizada.")
        try:
            conexao = conectar_original(**esperado)
        except psycopg.Error:
            raise p.ErroPersistencia("Não foi possível conectar ao PostgreSQL de testes; confira .env.test e permissões.") from None
        try:
            identidade = conexao.execute(
                "SELECT current_database(), current_user, rolsuper, rolcreatedb, rolcreaterole "
                "FROM pg_roles WHERE rolname = current_user"
            ).fetchone()
            if identidade != ("inep_test", config["user"], False, False, False):
                raise p.ErroPersistencia("Banco/usuário não autorizado ou usuário com privilégios administrativos.")
        except Exception:
            conexao.close()
            raise
        return conexao

    monkeypatch.setattr(p, "configuracao", configuracao_teste)
    monkeypatch.setattr(psycopg, "connect", conectar_protegido)
