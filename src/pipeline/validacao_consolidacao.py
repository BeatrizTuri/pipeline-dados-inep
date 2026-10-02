"""Contrato de tipos e verificações da consolidação, independentes de escrita."""

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pyarrow as pa

from src.pipeline.config import TAXA_MAXIMA, TAXA_MINIMA, UF_VALIDAS

IDENTIFICACAO = ["ano", "no_regiao", "sg_uf", "co_municipio", "no_municipio",
                 "co_entidade", "no_entidade", "tipoloca", "dependad"]
RASTREABILIDADE = ["fonte_arquivo", "fonte_caminho", "fonte_aba"]
TEXTOS_TAXAS = "taxas_textuais_origem"


def colunas_taxas(colunas) -> list[str]:
    return sorted(c for c in colunas if c.startswith(("tap_", "tre_", "tab_")))


def schema_historico(schemas: list[pa.Schema]) -> pa.Schema:
    """União determinística; metadados adicionais escalares são preservados como texto."""
    nomes = set().union(*(set(s.names) for s in schemas))
    if TEXTOS_TAXAS in nomes:
        raise ValueError(f"Nome reservado na entrada: {TEXTOS_TAXAS}")
    taxas = colunas_taxas(nomes)
    ordem = IDENTIFICACAO + taxas + RASTREABILIDADE
    ordem += sorted(nomes.difference(ordem)) + [TEXTOS_TAXAS]
    return pa.schema([(c, pa.int32() if c == "ano" else pa.float64() if c in taxas else pa.string())
                      for c in ordem])


def tipar_lote(dados: pd.DataFrame, ano: int, schema: pa.Schema) -> tuple[pd.DataFrame, int]:
    """Preserva zeros e textos auxiliares; rejeita taxas textuais de escolas."""
    for c in ("co_entidade", "co_municipio"):
        if c in dados and pd.api.types.is_numeric_dtype(dados[c]) and dados[c].notna().any():
            raise ValueError(f"{c} deve chegar como texto; zeros anteriores não podem ser recuperados.")
    dados = dados.reindex(columns=schema.names).copy()
    taxas = colunas_taxas(schema.names)
    for c in set(schema.names).difference(taxas + ["ano"]):
        dados[c] = dados[c].astype("string").str.strip().replace("", pd.NA)
    anos = pd.to_numeric(dados["ano"], errors="coerce")
    if anos.isna().any() or (anos != ano).any():
        raise ValueError(f"Ano ausente/inválido ou divergente do arquivo ({ano}).")
    dados["ano"] = anos.astype("int32")
    originais: dict[int, dict[str, str]] = {}
    for c in taxas:
        texto = dados[c].astype("string").str.strip().replace({"": pd.NA, "--": pd.NA, "-": pd.NA})
        numero = pd.to_numeric(texto.str.replace(",", ".", regex=False), errors="coerce")
        invalidos = texto.notna() & numero.isna()
        if (invalidos & dados["co_entidade"].notna()).any():
            raise ValueError(f"Taxa não numérica em escola identificada: {c}.")
        for i in dados.index[invalidos]:
            originais.setdefault(i, {})[c] = str(texto.loc[i])
        dados[c] = numero.astype("float64")
    for i, valores in originais.items():
        dados.loc[i, TEXTOS_TAXAS] = json.dumps(valores, ensure_ascii=False, sort_keys=True)
    return dados, sum(len(v) for v in originais.values())


def mascara_taxas_invalidas(dados: pd.DataFrame) -> pd.DataFrame:
    return dados.notna() & (~np.isfinite(dados) | (dados < TAXA_MINIMA) | (dados > TAXA_MAXIMA))


@dataclass
class Auditoria:
    """Retém apenas chaves e impressões digitais, não a tabela histórica."""

    contagens: dict[str, int] = field(default_factory=lambda: dict(
        quantidade_linhas_entrada=0, quantidade_linhas_consolidadas=0,
        quantidade_linhas_descartadas=0, escolas_ausentes=0, municipios_ausentes=0,
        codigos_escola_invalidos=0, codigos_municipio_invalidos=0,
        ufs_invalidas=0, valores_invalidos=0, valores_textuais=0,
        duplicidades_ano_escola=0, duplicatas_exatas=0, conflitos_ano_escola=0))
    escolas: set[str] = field(default_factory=set)
    municipios: set[str] = field(default_factory=set)
    ufs: set[str] = field(default_factory=set)
    chaves: dict[str, str] = field(default_factory=dict)
    assinaturas: set[str] = field(default_factory=set)

    def atualizar(self, dados: pd.DataFrame, textos: int) -> None:
        c = self.contagens
        c["quantidade_linhas_entrada"] += len(dados)
        c["quantidade_linhas_consolidadas"] += len(dados)
        c["escolas_ausentes"] += int(dados.co_entidade.isna().sum())
        c["municipios_ausentes"] += int(dados.co_municipio.isna().sum())
        for coluna, tamanho, contador in (("co_entidade", 8, "codigos_escola_invalidos"),
                                           ("co_municipio", 7, "codigos_municipio_invalidos")):
            valores = dados[coluna]
            c[contador] += int((valores.notna() & ~valores.str.fullmatch(f"[0-9]{{{tamanho}}}", na=False)).sum())
        c["ufs_invalidas"] += int((~dados.sg_uf.isin(UF_VALIDAS)).sum())
        c["valores_invalidos"] += int(mascara_taxas_invalidas(dados[colunas_taxas(dados)]).sum().sum())
        c["valores_textuais"] += textos
        self.escolas.update(dados.co_entidade.dropna())
        self.municipios.update(dados.co_municipio.dropna())
        self.ufs.update(dados.sg_uf.dropna())
        # Exclui somente proveniência: a mesma observação pode vir de abas distintas.
        conteudo = dados.drop(columns=RASTREABILIDADE).astype(object).where(dados.drop(columns=RASTREABILIDADE).notna(), None)
        for codigo, valores in zip(dados.co_entidade, conteudo.itertuples(index=False, name=None), strict=True):
            assinatura = hashlib.sha256(json.dumps(valores, ensure_ascii=False, default=str).encode()).hexdigest()
            if assinatura in self.assinaturas:
                c["duplicatas_exatas"] += 1
            self.assinaturas.add(assinatura)
            if pd.isna(codigo):
                continue
            if codigo in self.chaves:
                c["duplicidades_ano_escola"] += 1
                if self.chaves[codigo] != assinatura:
                    c["conflitos_ano_escola"] += 1
            else:
                self.chaves[codigo] = assinatura

    def resumo(self) -> dict:
        return {**self.contagens, "quantidade_escolas": len(self.escolas),
                "municipios_unicos": len(self.municipios), "ufs_encontradas": ";".join(sorted(self.ufs))}
