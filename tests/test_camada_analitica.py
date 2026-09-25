import pandas as pd
import pyarrow.dataset as ds
import pytest

from src.pipeline.consolidacao import gerar_base_consolidada
from src.pipeline.metricas import mapa_metricas, dimensao_metricas


@pytest.mark.parametrize("ano,origem,destino", [
    (2007, "tap_1a_serie_2o_ano", "tap_fun_02"),
    (2011, "tre_ens_fundamental", "tre_fun"),
    (2015, "tap_f58", "tap_fun_af"),
    (2018, "tap_f58", "tap_fun_01"),
    (2018, "tap_f04", "tap_fun_af"),
    (2018, "tab_f03", "tab_fun_05"),
    (2024, "tab_med_ns", "tab_med_ns"),
])
def test_significado_por_periodo(ano, origem, destino):
    assert mapa_metricas(ano)[origem] == destino


def test_catalogo_tem_54_metricas_por_layout():
    d = dimensao_metricas()
    assert len(d) == 270
    assert not d.duplicated(["ano_inicio", "codigo_original"]).any()
    assert d.groupby("ano_inicio").coluna_analitica.nunique().eq(54).all()
    with pytest.raises(ValueError):
        mapa_metricas(2025)


def test_dimensoes_temporais_particoes_reexecucao(tmp_path):
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    for ano, municipio, nome, coluna in [(2015, "001", "Antiga", "tap_f58"), (2018, "002", "Nova", "tap_f58")]:
        d = pd.DataFrame([dict(ano=str(ano), co_entidade="0001", co_municipio=municipio,
                               no_entidade=nome, no_municipio=f"Municipio {municipio}",
                               sg_uf="SP", no_regiao="Sudeste", tipoloca="Urbana", dependad="Particular",
                               **{coluna: "93"})])
        d.to_parquet(entrada / f"taxas_rendimento_{ano}.parquet", index=False)
    for _ in range(2):
        r = gerar_base_consolidada(entrada, tmp_path / "saida/historico.parquet", tmp_path / "relatorio.csv")
        assert r[-1]["publicado"] and r[-1]["linhas_analiticas"] == 2
    pasta = tmp_path / "saida/dashboard"
    assert len(list((pasta / "taxas").rglob("*.parquet"))) == 2
    dados = ds.dataset(pasta / "taxas", format="parquet", partitioning="hive").to_table().to_pandas()
    assert dados.ano.tolist() == [2015, 2018]
    assert dados.tap_fun_af.iloc[0] == dados.tap_fun_01.iloc[1] == 93
    assert pd.isna(dados.tap_fun_01.iloc[0]) and pd.isna(dados.tap_fun_af.iloc[1])
    escolas = pd.read_parquet(pasta / "dim_escolas.parquet")
    municipios = pd.read_parquet(pasta / "dim_municipios.parquet")
    assert len(escolas) == len(municipios) == 2
    assert escolas.id_escola.is_unique and municipios.id_municipio.is_unique
    assert set(dados.id_escola) == set(escolas.id_escola)
    assert set(dados.id_municipio) == set(municipios.id_municipio)
    assert set(escolas.dependad) == {"Privada"}
    unidos = dados.merge(escolas[["id_escola", "no_entidade"]], on="id_escola", validate="many_to_one", suffixes=("", "_dim"))
    assert unidos.no_entidade.tolist() == unidos.no_entidade_dim.tolist() == ["Antiga", "Nova"]
