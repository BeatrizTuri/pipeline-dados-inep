-- Migração aditiva e idempotente; executar dentro de uma transação.
CREATE OR REPLACE VIEW public.dim_municipio_canonica AS
WITH observacoes AS (
    SELECT id_municipio, ano, count(*) AS observacoes_ano
    FROM public.fato_rendimento_escolar
    WHERE id_municipio IS NOT NULL
    GROUP BY id_municipio, ano
), candidatos AS (
    SELECT m.*, o.ano AS ano_referencia, o.observacoes_ano,
           row_number() OVER (
               PARTITION BY m.co_municipio
               ORDER BY o.ano DESC NULLS LAST,
                        o.observacoes_ano DESC NULLS LAST,
                        m.id_municipio COLLATE "C" ASC
           ) AS posicao
    FROM public.dim_municipio m
    LEFT JOIN observacoes o USING (id_municipio)
)
SELECT co_municipio, no_municipio, sg_uf, no_regiao,
       id_municipio AS id_municipio_origem, ano_referencia
FROM candidatos
WHERE posicao = 1;

-- A junção pela PK histórica não multiplica nem elimina fatos sem município.
CREATE OR REPLACE VIEW public.vw_fato_rendimento_escolar AS
SELECT f.*, m.co_municipio
FROM public.fato_rendimento_escolar f
LEFT JOIN public.dim_municipio m USING (id_municipio);
