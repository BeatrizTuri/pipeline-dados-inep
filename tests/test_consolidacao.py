import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.pipeline import consolidacao


def gravar(pasta: Path, ano=2024, **extras) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    registro = dict(ano=str(ano), co_entidade="00123456", co_municipio="0012345",
                    no_entidade="Escola", no_municipio="Município", sg_uf="SP",
                    no_regiao="Sudeste", tipoloca="Urbana", dependad="Municipal",
                    tap_fun="92,1", tre_fun="5.7", tab_fun="2.2",
                    fonte_arquivo="origem.xlsx", fonte_caminho="raw/origem.xlsx", fonte_aba="ESCOLAS")
    registro.update(extras)
    caminho = pasta / f"taxas_rendimento_{ano}.parquet"
    pd.DataFrame([registro]).to_parquet(caminho, index=False)
    return caminho


def executar(tmp_path):
    return consolidacao.gerar_base_consolidada(tmp_path / "entrada", tmp_path / "saida" / "historico.parquet",
                                              tmp_path / "relatorios" / "consolidacao.csv")


def test_publicacao_2024_2025_preserva_54_metricas_e_codigos(tmp_path):
    """
    Cria os dois anos com 54 valores diferentes e publica duas vezes → preserva valores, código
    textual e catálogo até 2025 → evita liberar o ano sem verificar sua saída analítica.
    """
    from src.pipeline.metricas import COLUNAS_METRICAS
    valores = {c: str(i + 1) for i, c in enumerate(COLUNAS_METRICAS)}
    for ano in (2024, 2025):
        gravar(tmp_path / "entrada", ano, **valores)
    for _ in range(2):
        total = executar(tmp_path)[-1]
        assert total["publicado"] and total["anos_processados"] == "2024;2025"
        assert total["linhas_analiticas"] == 2
        for ano in (2024, 2025):
            dados = pq.ParquetFile(tmp_path / f"saida/dashboard/taxas/ano={ano}/taxas.parquet").read().to_pandas()
            assert dados[COLUNAS_METRICAS].iloc[0].tolist() == list(range(1, 55))
            assert dados.co_municipio.tolist() == ["0012345"]
        catalogo = pd.read_parquet(tmp_path / "saida/dashboard/dim_metricas.parquet")
        assert catalogo[catalogo.ano_inicio == 2021].ano_fim.eq(2025).all()


def test_multiplos_anos_schema_codigos_e_ausencias(tmp_path):
    """
    Usa dois anos, vírgula decimal, código com zeros, coluna extra e campos ausentes → converte
    tipos e preserva valores e metadados → evita perda de zeros, de procedência ou preenchimento
    indevido das ausências.
    """
    gravar(tmp_path / "entrada", 2023, extra="metadado")
    p = gravar(tmp_path / "entrada", 2024, co_entidade="00000002", tap_fun=None)
    d = pd.read_parquet(p).drop(columns=["tre_fun"])
    d.to_parquet(p, index=False)
    relatorio = executar(tmp_path)
    assert relatorio[-1]["publicado"]
    assert relatorio[-1]["anos_processados"] == "2023;2024"
    assert "tre_fun" in relatorio[1]["metricas_ausentes"]
    assert relatorio[0]["colunas_desconhecidas"] == "extra"
    h = pd.read_parquet(tmp_path / "saida/historico.parquet")
    assert len(h) == 2
    assert h.co_entidade.tolist() == ["00123456", "00000002"]
    assert h.co_municipio.tolist() == ["0012345", "0012345"]
    assert h.ano.tolist() == [2023, 2024]
    assert h.tap_fun.iloc[0] == 92.1
    assert pd.isna(h.tap_fun.iloc[1]) and pd.isna(h.tre_fun.iloc[1])
    assert h.extra.iloc[0] == "metadado" and pd.isna(h.extra.iloc[1])
    schema = pq.ParquetFile(tmp_path / "saida/historico.parquet").schema_arrow
    assert str(schema.field("ano").type) == "int32"
    assert str(schema.field("tap_fun").type) == "double"
    assert str(schema.field("co_entidade").type) == "string"
    assert set(["fonte_arquivo", "fonte_aba", "fonte_caminho"]).issubset(h.columns)
    assert json.loads((tmp_path / "relatorios/schema_consolidacao.json").read_text(encoding="utf-8"))["schemas"]


@pytest.mark.parametrize("conflito", [False, True])
def test_duplicidade_entre_lotes_bloqueia_publicacao(tmp_path, monkeypatch, conflito):
    """
    Repete uma escola/ano, com valores iguais ou diferentes, em lotes separados → bloqueia e
    distingue repetição exata de conflito → evita observações duplicadas na fato.
    """
    monkeypatch.setattr(consolidacao, "TAMANHO_LOTE", 1)
    p = gravar(tmp_path / "entrada")
    d = pd.read_parquet(p)
    duplicado = d.copy()
    if conflito:
        duplicado["tap_fun"] = "80"
    pd.concat([d, duplicado]).to_parquet(p, index=False)
    r = executar(tmp_path)
    assert r[-1]["status"] == "erro" and not r[-1]["publicado"]
    assert r[0]["duplicidades_ano_escola"] == 1
    assert r[0]["conflitos_ano_escola"] == int(conflito)
    assert r[0]["duplicatas_exatas"] == int(not conflito)
    assert not (tmp_path / "saida/historico.parquet").exists()


def test_sem_escola_preserva_texto_auxiliar_e_exclui_so_analitica(tmp_path):
    """
    Insere linha sem escola com texto no lugar de taxa → guarda o texto no histórico e deixa a
    linha fora da análise escolar → evita perder a evidência original ou contar cabeçalho como
    escola.
    """
    gravar(tmp_path / "entrada", co_entidade=None, co_municipio=None, sg_uf=None,
           tap_fun="Cabeçalho auxiliar")
    r = executar(tmp_path)
    assert r[-1]["publicado"] and r[-1]["status"] == "aviso"
    assert r[-1]["linhas_analiticas"] == 0
    h = pd.read_parquet(tmp_path / "saida/historico.parquet")
    assert len(h) == 1 and pd.isna(h.tap_fun.iloc[0])
    assert json.loads(h.taxas_textuais_origem.iloc[0])["tap_fun"] == "Cabeçalho auxiliar"
    assert r[0]["escolas_ausentes"] == r[0]["municipios_ausentes"] == 1


def test_taxas_invalidas_e_uf(tmp_path):
    """
    Usa 101%, -2%, infinito e UF `XX` → registra ocorrências, mantém 101 no histórico e deixa as
    três taxas nulas na saída analítica → evita usar taxas inválidas sem apagar a origem.
    """
    gravar(tmp_path / "entrada", tap_fun="101", tre_fun="-2", tab_fun="inf", sg_uf="XX")
    r = executar(tmp_path)
    assert r[0]["valores_invalidos"] == 3 and r[0]["ufs_invalidas"] == 1
    h = pd.read_parquet(tmp_path / "saida/historico.parquet")
    a = pd.read_parquet(tmp_path / "saida/dashboard/taxas/ano=2024/taxas.parquet")
    assert h.tap_fun.iloc[0] == 101
    assert a[["tap_fun", "tre_fun", "tab_fun"]].isna().all().all()


@pytest.mark.parametrize("alteracao", [dict(tap_fun="texto inesperado"), dict(co_entidade=123), dict(ano="2023")])
def test_contrato_invalido(tmp_path, alteracao):
    """
    Usa taxa textual em escola identificada, código escolar numérico ou ano divergente do
    arquivo → bloqueia a publicação → evita adivinhar valores, perder zeros ou publicar no ano
    errado.
    """
    p = gravar(tmp_path / "entrada")
    d = pd.read_parquet(p)
    for c, v in alteracao.items():
        d[c] = v
    d.to_parquet(p, index=False)
    r = executar(tmp_path)
    assert r[-1]["status"] == "erro" and not r[-1]["publicado"]


def test_arquivo_corrompido_preserva_todas_saidas_anteriores(tmp_path):
    """
    Acrescenta arquivo ilegível depois de uma publicação válida → falha e mantém os Parquets e
    schema anteriores → evita substituir uma base válida por entrada quebrada.
    """
    gravar(tmp_path / "entrada")
    assert executar(tmp_path)[-1]["publicado"]
    antigos = {p: p.read_bytes() for p in (tmp_path / "saida").rglob("*.parquet")}
    schema = tmp_path / "relatorios/schema_consolidacao.json"
    antigos[schema] = schema.read_bytes()
    (tmp_path / "entrada/taxas_rendimento_2023.parquet").write_bytes(b"invalido")
    assert executar(tmp_path)[-1]["status"] == "erro"
    assert all(p.read_bytes() == conteudo for p, conteudo in antigos.items())


def test_entrada_vazia(tmp_path):
    """
    Não fornece arquivos → retorna erro → evita uma consolidação aparentemente bem-sucedida sem
    entrada.
    """
    assert executar(tmp_path)[-1]["status"] == "erro"


def test_escola_sem_municipio_permanece_na_analitica(tmp_path):
    """
    Fornece escola identificada sem código municipal → mantém a escola e deixa a referência
    municipal nula → evita descartar uma escola só por falta de município.
    """
    gravar(tmp_path / "entrada", co_municipio=None)
    r = executar(tmp_path)
    assert r[-1]["publicado"] and r[-1]["linhas_analiticas"] == 1
    pasta = tmp_path / "saida/dashboard"
    a = pd.read_parquet(pasta / "taxas/ano=2024/taxas.parquet")
    assert a.id_municipio.isna().all()
    assert len(pd.read_parquet(pasta / "dim_municipios.parquet")) == 0
    assert len(pd.read_parquet(pasta / "dim_escolas.parquet")) == 1


def test_reexecucao_remove_particao_obsoleta(tmp_path):
    """
    Publica 2023–2024 e depois somente 2024 → remove a pasta antiga de 2023 → evita misturar
    produtos de execuções diferentes. Esta é uma regra dos arquivos da Etapa 5; a Etapa 6 tem
    proteção adicional contra redução do período.
    """
    p = gravar(tmp_path / "entrada", 2023)
    gravar(tmp_path / "entrada", 2024)
    assert executar(tmp_path)[-1]["publicado"]
    p.unlink()
    assert executar(tmp_path)[-1]["publicado"]
    assert not (tmp_path / "saida/dashboard/taxas/ano=2023").exists()
    assert (tmp_path / "saida/dashboard/taxas/ano=2024/taxas.parquet").exists()


def test_ano_duplicado_em_subpastas(tmp_path):
    """
    Fornece dois arquivos anuais de 2024 em pastas distintas → bloqueia e informa a duplicidade
    → evita escolher um arquivo arbitrariamente.
    """
    gravar(tmp_path / "entrada/a")
    gravar(tmp_path / "entrada/b")
    r = executar(tmp_path)
    assert r[-1]["status"] == "erro"
    assert "Mais de um arquivo" in r[1]["observacao"]


def test_metricas_desconhecidas_preservadas_e_reportadas(tmp_path):
    """
    Inclui uma taxa fora do catálogo → registra o aviso e mantém seu valor no histórico → evita
    apagar uma coluna desconhecida ou tratá-la como métrica harmonizada.
    """
    gravar(tmp_path / "entrada", tap_desconhecida="25")
    r = executar(tmp_path)
    assert r[-1]["publicado"] and r[0]["metricas_desconhecidas"] == "tap_desconhecida"
    assert pd.read_parquet(tmp_path / "saida/historico.parquet").tap_desconhecida.iloc[0] == 25


def test_rollback_publicacao(tmp_path, monkeypatch):
    """
    Faz falhar a segunda substituição de arquivo → restaura os dois destinos antigos → evita
    publicação parcialmente substituída em uma falha de I/O simulada. Não simula desligamento
    abrupto.
    """
    origem1, origem2 = tmp_path / "novo1", tmp_path / "novo2"
    destino1, destino2 = tmp_path / "antigo1", tmp_path / "antigo2"
    for p, texto in [(origem1, "novo1"), (origem2, "novo2"), (destino1, "antigo1"), (destino2, "antigo2")]:
        p.write_text(texto)
    original = Path.replace

    def falhar(self, destino):
        if self == origem2:
            raise OSError("falha simulada")
        return original(self, destino)

    monkeypatch.setattr(Path, "replace", falhar)
    with pytest.raises(OSError):
        consolidacao.publicar([(origem1, destino1), (origem2, destino2)], tmp_path)
    assert destino1.read_text() == "antigo1" and destino2.read_text() == "antigo2"


def test_codigos_malformados_reportados_sem_correcao(tmp_path):
    """
    Usa códigos textuais com formato inesperado → registra aviso e preserva o texto → evita
    inventar correções sem evidência.
    """
    gravar(tmp_path / "entrada", co_entidade="ABC12345", co_municipio="123")
    r = executar(tmp_path)
    assert r[-1]["publicado"] and r[-1]["status"] == "aviso"
    assert r[-1]["codigos_escola_invalidos"] == r[-1]["codigos_municipio_invalidos"] == 1
    h = pd.read_parquet(tmp_path / "saida/historico.parquet")
    assert h.co_entidade.iloc[0] == "ABC12345" and h.co_municipio.iloc[0] == "123"


def test_dimensao_invalida_bloqueia_e_preserva_publicacao(tmp_path, monkeypatch):
    """
    Esvazia a dimensão escolar gerada antes da publicação → detecta referências inválidas e
    conserva a publicação anterior → evita publicar taxas sem os cadastros correspondentes.
    """
    gravar(tmp_path / "entrada")
    assert executar(tmp_path)[-1]["relacionamentos_validados"]
    anteriores = {p: p.read_bytes() for p in (tmp_path / "saida").rglob("*.parquet")}
    schema = tmp_path / "relatorios/schema_consolidacao.json"
    anteriores[schema] = schema.read_bytes()
    gerar = consolidacao.gerar_camada_analitica

    def corromper(historico, destino, colunas):
        contagens = gerar(historico, destino, colunas)
        p = destino / "dim_escolas.parquet"
        d = pd.read_parquet(p)
        d.iloc[:0].to_parquet(p, index=False)
        return contagens

    monkeypatch.setattr(consolidacao, "gerar_camada_analitica", corromper)
    r = executar(tmp_path)
    assert r[-1]["status"] == "erro" and not r[-1]["publicado"]
    assert "Referência inválida" in r[-1]["observacao"]
    assert all(p.read_bytes() == conteudo for p, conteudo in anteriores.items())
