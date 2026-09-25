"""Correspondências verificadas nos cabeçalhos locais do INEP, por layout.

Os códigos F04/F58 mudam de significado em 2018. Não inferir semântica
pela posição ou pelo código isolado. Períodos futuros exigem revisão.
"""

import pandas as pd

FAMILIAS = {"tap": "aprovacao", "tre": "reprovacao", "tab": "abandono"}
RECORTES = (
    ["fun", "fun_ai", "fun_af"]
    + [f"fun_{i:02d}" for i in range(1, 10)]
    + ["med"] + [f"med_{i:02d}" for i in range(1, 5)] + ["med_ns"]
)
PERIODOS = [(2007, 2010), (2011, 2014), (2015, 2017), (2018, 2020), (2021, 2024)]
COLUNAS_METRICAS = [f"{familia}_{recorte}" for familia in FAMILIAS for recorte in RECORTES]


def sufixos_periodo(ano: int) -> list[str]:
    """Retorna os aliases na ordem semântica de RECORTES, nunca na física."""
    if 2007 <= ano <= 2010:
        return (["fundamental", "1a_a_4a_serie_1o_a_5o_ano", "5a_a_8a_serie_6o_ao_9o_ano",
                 "1o_aensifundamental"]
                + [f"{i}a_serie_{i+1}o_ano" for i in range(1, 9)]
                + ["medio"] + [f"{i}a_serie_medio" for i in range(1, 5)] + ["medio_nao_seriado"])
    if 2011 <= ano <= 2014:
        return (["ens_fundamental", "anos_iniciais_1o_ao_5o_ano", "anos_finais_6o_ao_9o_ano"]
                + [f"{i}o_ano" for i in range(1, 10)]
                + ["ens_medio"] + [f"{i}a_serie" for i in range(1, 5)] + ["medio_nao_seriado"])
    if 2015 <= ano <= 2017:
        return (["fun", "f14", "f58"] + [f"f{i:02d}" for i in range(9)]
                + ["med"] + [f"m{i:02d}" for i in range(1, 5)] + ["mns"])
    if 2018 <= ano <= 2020:
        return (["fun", "f14", "f04", "f58", "f00", "f01", "f02", "f03", "f05", "f06", "f07", "f08"]
                + ["med"] + [f"m{i:02d}" for i in range(1, 5)] + ["mns"])
    if 2021 <= ano <= 2024:
        return RECORTES.copy()
    raise ValueError(f"Layout do ano {ano} ainda não validado no catálogo de métricas.")


def mapa_metricas(ano: int) -> dict[str, str]:
    return {f"{f}_{origem}": f"{f}_{destino}" for f in FAMILIAS
            for origem, destino in zip(sufixos_periodo(ano), RECORTES, strict=True)}


def dimensao_metricas() -> pd.DataFrame:
    """Um registro por alias, família e período; a coluna analítica pode repetir."""
    registros = []
    for inicio, fim in PERIODOS:
        for origem, destino in mapa_metricas(inicio).items():
            familia, recorte = destino.split("_", 1)
            etapa = "ensino_fundamental" if recorte.startswith("fun") else "ensino_medio"
            detalhe = recorte.partition("_")[2] or "total"
            detalhe = {"ai": "anos_iniciais", "af": "anos_finais", "ns": "nao_seriado"}.get(detalhe, detalhe)
            registros.append(dict(codigo_original=origem, coluna_analitica=destino,
                                  ano_inicio=inicio, ano_fim=fim, tipo_taxa=FAMILIAS[familia],
                                  etapa_ensino=etapa, detalhamento=detalhe,
                                  descricao=f"Percentual de {FAMILIAS[familia]}: {etapa}, {detalhe}",
                                  observacao="Séries/anos de 8 e 9 anos conforme cabeçalho da fonte; não somar recortes."))
    return pd.DataFrame(registros)
