BEGIN;

CREATE TABLE public.dim_municipio (

    id_municipio text NOT NULL,

    co_municipio text NOT NULL,

    no_municipio text,

    sg_uf text,

    no_regiao text,

    CONSTRAINT pk_dim_municipio PRIMARY KEY (id_municipio),

    CONSTRAINT ck_dim_municipio_hash CHECK (id_municipio ~ '^[0-9a-f]{64}$')

);



CREATE TABLE public.dim_escola (

    id_escola text NOT NULL,

    co_entidade text NOT NULL,

    no_entidade text,

    id_municipio text,

    tipoloca text,

    dependad text,

    co_municipio text,

    no_municipio text,

    sg_uf text,

    no_regiao text,

    CONSTRAINT pk_dim_escola PRIMARY KEY (id_escola),

    CONSTRAINT uq_dim_escola_id_codigo UNIQUE (id_escola, co_entidade),

    CONSTRAINT fk_dim_escola_municipio FOREIGN KEY (id_municipio)

        REFERENCES public.dim_municipio (id_municipio)

        ON DELETE NO ACTION ON UPDATE NO ACTION,

    CONSTRAINT ck_dim_escola_hash CHECK (id_escola ~ '^[0-9a-f]{64}$'),

    CONSTRAINT ck_dim_escola_municipio_hash

        CHECK (id_municipio IS NULL OR id_municipio ~ '^[0-9a-f]{64}$'),

    CONSTRAINT ck_dim_escola_municipio_identificado
        CHECK (id_municipio IS NULL OR co_municipio IS NOT NULL)

);

CREATE TABLE public.fato_rendimento_escolar (

    ano integer NOT NULL,

    co_entidade text NOT NULL,

    id_escola text NOT NULL,

    id_municipio text,

    tap_fun double precision

        CONSTRAINT ck_fato_tap_fun CHECK (tap_fun IS NULL OR (tap_fun >= 0 AND tap_fun <= 100)),

    tap_fun_ai double precision

        CONSTRAINT ck_fato_tap_fun_ai CHECK (tap_fun_ai IS NULL OR (tap_fun_ai >= 0 AND tap_fun_ai <= 100)),

    tap_fun_af double precision

        CONSTRAINT ck_fato_tap_fun_af CHECK (tap_fun_af IS NULL OR (tap_fun_af >= 0 AND tap_fun_af <= 100)),

    tap_fun_01 double precision

        CONSTRAINT ck_fato_tap_fun_01 CHECK (tap_fun_01 IS NULL OR (tap_fun_01 >= 0 AND tap_fun_01 <= 100)),

    tap_fun_02 double precision

        CONSTRAINT ck_fato_tap_fun_02 CHECK (tap_fun_02 IS NULL OR (tap_fun_02 >= 0 AND tap_fun_02 <= 100)),

    tap_fun_03 double precision

        CONSTRAINT ck_fato_tap_fun_03 CHECK (tap_fun_03 IS NULL OR (tap_fun_03 >= 0 AND tap_fun_03 <= 100)),

    tap_fun_04 double precision

        CONSTRAINT ck_fato_tap_fun_04 CHECK (tap_fun_04 IS NULL OR (tap_fun_04 >= 0 AND tap_fun_04 <= 100)),

    tap_fun_05 double precision

        CONSTRAINT ck_fato_tap_fun_05 CHECK (tap_fun_05 IS NULL OR (tap_fun_05 >= 0 AND tap_fun_05 <= 100)),

    tap_fun_06 double precision

        CONSTRAINT ck_fato_tap_fun_06 CHECK (tap_fun_06 IS NULL OR (tap_fun_06 >= 0 AND tap_fun_06 <= 100)),

    tap_fun_07 double precision

        CONSTRAINT ck_fato_tap_fun_07 CHECK (tap_fun_07 IS NULL OR (tap_fun_07 >= 0 AND tap_fun_07 <= 100)),

    tap_fun_08 double precision

        CONSTRAINT ck_fato_tap_fun_08 CHECK (tap_fun_08 IS NULL OR (tap_fun_08 >= 0 AND tap_fun_08 <= 100)),

    tap_fun_09 double precision

        CONSTRAINT ck_fato_tap_fun_09 CHECK (tap_fun_09 IS NULL OR (tap_fun_09 >= 0 AND tap_fun_09 <= 100)),

    tap_med double precision

        CONSTRAINT ck_fato_tap_med CHECK (tap_med IS NULL OR (tap_med >= 0 AND tap_med <= 100)),

    tap_med_01 double precision

        CONSTRAINT ck_fato_tap_med_01 CHECK (tap_med_01 IS NULL OR (tap_med_01 >= 0 AND tap_med_01 <= 100)),

    tap_med_02 double precision

        CONSTRAINT ck_fato_tap_med_02 CHECK (tap_med_02 IS NULL OR (tap_med_02 >= 0 AND tap_med_02 <= 100)),

    tap_med_03 double precision

        CONSTRAINT ck_fato_tap_med_03 CHECK (tap_med_03 IS NULL OR (tap_med_03 >= 0 AND tap_med_03 <= 100)),

    tap_med_04 double precision

        CONSTRAINT ck_fato_tap_med_04 CHECK (tap_med_04 IS NULL OR (tap_med_04 >= 0 AND tap_med_04 <= 100)),

    tap_med_ns double precision

        CONSTRAINT ck_fato_tap_med_ns CHECK (tap_med_ns IS NULL OR (tap_med_ns >= 0 AND tap_med_ns <= 100)),

    tre_fun double precision

        CONSTRAINT ck_fato_tre_fun CHECK (tre_fun IS NULL OR (tre_fun >= 0 AND tre_fun <= 100)),

    tre_fun_ai double precision

        CONSTRAINT ck_fato_tre_fun_ai CHECK (tre_fun_ai IS NULL OR (tre_fun_ai >= 0 AND tre_fun_ai <= 100)),

    tre_fun_af double precision

        CONSTRAINT ck_fato_tre_fun_af CHECK (tre_fun_af IS NULL OR (tre_fun_af >= 0 AND tre_fun_af <= 100)),

    tre_fun_01 double precision

        CONSTRAINT ck_fato_tre_fun_01 CHECK (tre_fun_01 IS NULL OR (tre_fun_01 >= 0 AND tre_fun_01 <= 100)),

    tre_fun_02 double precision

        CONSTRAINT ck_fato_tre_fun_02 CHECK (tre_fun_02 IS NULL OR (tre_fun_02 >= 0 AND tre_fun_02 <= 100)),

    tre_fun_03 double precision

        CONSTRAINT ck_fato_tre_fun_03 CHECK (tre_fun_03 IS NULL OR (tre_fun_03 >= 0 AND tre_fun_03 <= 100)),

    tre_fun_04 double precision

        CONSTRAINT ck_fato_tre_fun_04 CHECK (tre_fun_04 IS NULL OR (tre_fun_04 >= 0 AND tre_fun_04 <= 100)),

    tre_fun_05 double precision

        CONSTRAINT ck_fato_tre_fun_05 CHECK (tre_fun_05 IS NULL OR (tre_fun_05 >= 0 AND tre_fun_05 <= 100)),

    tre_fun_06 double precision

        CONSTRAINT ck_fato_tre_fun_06 CHECK (tre_fun_06 IS NULL OR (tre_fun_06 >= 0 AND tre_fun_06 <= 100)),

    tre_fun_07 double precision

        CONSTRAINT ck_fato_tre_fun_07 CHECK (tre_fun_07 IS NULL OR (tre_fun_07 >= 0 AND tre_fun_07 <= 100)),

    tre_fun_08 double precision

        CONSTRAINT ck_fato_tre_fun_08 CHECK (tre_fun_08 IS NULL OR (tre_fun_08 >= 0 AND tre_fun_08 <= 100)),

    tre_fun_09 double precision

        CONSTRAINT ck_fato_tre_fun_09 CHECK (tre_fun_09 IS NULL OR (tre_fun_09 >= 0 AND tre_fun_09 <= 100)),

    tre_med double precision

        CONSTRAINT ck_fato_tre_med CHECK (tre_med IS NULL OR (tre_med >= 0 AND tre_med <= 100)),

    tre_med_01 double precision

        CONSTRAINT ck_fato_tre_med_01 CHECK (tre_med_01 IS NULL OR (tre_med_01 >= 0 AND tre_med_01 <= 100)),

    tre_med_02 double precision

        CONSTRAINT ck_fato_tre_med_02 CHECK (tre_med_02 IS NULL OR (tre_med_02 >= 0 AND tre_med_02 <= 100)),

    tre_med_03 double precision

        CONSTRAINT ck_fato_tre_med_03 CHECK (tre_med_03 IS NULL OR (tre_med_03 >= 0 AND tre_med_03 <= 100)),

    tre_med_04 double precision

        CONSTRAINT ck_fato_tre_med_04 CHECK (tre_med_04 IS NULL OR (tre_med_04 >= 0 AND tre_med_04 <= 100)),

    tre_med_ns double precision

        CONSTRAINT ck_fato_tre_med_ns CHECK (tre_med_ns IS NULL OR (tre_med_ns >= 0 AND tre_med_ns <= 100)),

    tab_fun double precision

        CONSTRAINT ck_fato_tab_fun CHECK (tab_fun IS NULL OR (tab_fun >= 0 AND tab_fun <= 100)),

    tab_fun_ai double precision

        CONSTRAINT ck_fato_tab_fun_ai CHECK (tab_fun_ai IS NULL OR (tab_fun_ai >= 0 AND tab_fun_ai <= 100)),

    tab_fun_af double precision

        CONSTRAINT ck_fato_tab_fun_af CHECK (tab_fun_af IS NULL OR (tab_fun_af >= 0 AND tab_fun_af <= 100)),

    tab_fun_01 double precision

        CONSTRAINT ck_fato_tab_fun_01 CHECK (tab_fun_01 IS NULL OR (tab_fun_01 >= 0 AND tab_fun_01 <= 100)),

    tab_fun_02 double precision

        CONSTRAINT ck_fato_tab_fun_02 CHECK (tab_fun_02 IS NULL OR (tab_fun_02 >= 0 AND tab_fun_02 <= 100)),

    tab_fun_03 double precision

        CONSTRAINT ck_fato_tab_fun_03 CHECK (tab_fun_03 IS NULL OR (tab_fun_03 >= 0 AND tab_fun_03 <= 100)),

    tab_fun_04 double precision

        CONSTRAINT ck_fato_tab_fun_04 CHECK (tab_fun_04 IS NULL OR (tab_fun_04 >= 0 AND tab_fun_04 <= 100)),

    tab_fun_05 double precision

        CONSTRAINT ck_fato_tab_fun_05 CHECK (tab_fun_05 IS NULL OR (tab_fun_05 >= 0 AND tab_fun_05 <= 100)),

    tab_fun_06 double precision

        CONSTRAINT ck_fato_tab_fun_06 CHECK (tab_fun_06 IS NULL OR (tab_fun_06 >= 0 AND tab_fun_06 <= 100)),

    tab_fun_07 double precision

        CONSTRAINT ck_fato_tab_fun_07 CHECK (tab_fun_07 IS NULL OR (tab_fun_07 >= 0 AND tab_fun_07 <= 100)),

    tab_fun_08 double precision

        CONSTRAINT ck_fato_tab_fun_08 CHECK (tab_fun_08 IS NULL OR (tab_fun_08 >= 0 AND tab_fun_08 <= 100)),

    tab_fun_09 double precision

        CONSTRAINT ck_fato_tab_fun_09 CHECK (tab_fun_09 IS NULL OR (tab_fun_09 >= 0 AND tab_fun_09 <= 100)),

    tab_med double precision

        CONSTRAINT ck_fato_tab_med CHECK (tab_med IS NULL OR (tab_med >= 0 AND tab_med <= 100)),

    tab_med_01 double precision

        CONSTRAINT ck_fato_tab_med_01 CHECK (tab_med_01 IS NULL OR (tab_med_01 >= 0 AND tab_med_01 <= 100)),

    tab_med_02 double precision

        CONSTRAINT ck_fato_tab_med_02 CHECK (tab_med_02 IS NULL OR (tab_med_02 >= 0 AND tab_med_02 <= 100)),

    tab_med_03 double precision

        CONSTRAINT ck_fato_tab_med_03 CHECK (tab_med_03 IS NULL OR (tab_med_03 >= 0 AND tab_med_03 <= 100)),

    tab_med_04 double precision

        CONSTRAINT ck_fato_tab_med_04 CHECK (tab_med_04 IS NULL OR (tab_med_04 >= 0 AND tab_med_04 <= 100)),

    tab_med_ns double precision

        CONSTRAINT ck_fato_tab_med_ns CHECK (tab_med_ns IS NULL OR (tab_med_ns >= 0 AND tab_med_ns <= 100)),

    CONSTRAINT pk_fato_rendimento_escolar PRIMARY KEY (ano, co_entidade),

    CONSTRAINT fk_fato_escola FOREIGN KEY (id_escola, co_entidade)

        REFERENCES public.dim_escola (id_escola, co_entidade)

        ON DELETE NO ACTION ON UPDATE NO ACTION,

    CONSTRAINT fk_fato_municipio FOREIGN KEY (id_municipio)

        REFERENCES public.dim_municipio (id_municipio)

        ON DELETE NO ACTION ON UPDATE NO ACTION,

    CONSTRAINT ck_fato_escola_hash CHECK (id_escola ~ '^[0-9a-f]{64}$'),

    CONSTRAINT ck_fato_municipio_hash

        CHECK (id_municipio IS NULL OR id_municipio ~ '^[0-9a-f]{64}$')

);

CREATE TABLE public.catalogo_metricas (

    codigo_original text NOT NULL,

    coluna_analitica text NOT NULL,

    ano_inicio integer NOT NULL,

    ano_fim integer NOT NULL,

    tipo_taxa text NOT NULL,

    etapa_ensino text NOT NULL,

    detalhamento text NOT NULL,

    descricao text NOT NULL,

    observacao text NOT NULL,

    CONSTRAINT pk_catalogo_metricas PRIMARY KEY (ano_inicio, codigo_original),

    CONSTRAINT ck_catalogo_metricas_periodo CHECK (ano_inicio <= ano_fim)

);

CREATE TABLE public.controle_carga (

    id_execucao uuid NOT NULL,

    inicio timestamptz NOT NULL,

    fim timestamptz,

    status text NOT NULL,

    carga_ativa boolean NOT NULL DEFAULT false,

    quantidade_linhas bigint,

    quantidade_escolas bigint,

    quantidade_municipios bigint,

    quantidade_codigos_escola bigint,

    quantidade_codigos_municipio bigint,

    quantidade_metricas_catalogo bigint,

    versao_pipeline text NOT NULL,

    commit_pipeline text,

    codigo_modificado boolean,

    manifesto_origem jsonb NOT NULL,

    validacoes jsonb,

    mensagem_erro text,

    CONSTRAINT pk_controle_carga PRIMARY KEY (id_execucao),

    CONSTRAINT ck_controle_carga_status

        CHECK (status IN ('em_execucao', 'sucesso', 'falha', 'interrompida')),

    CONSTRAINT ck_controle_carga_periodo

        CHECK (fim IS NULL OR fim >= inicio),

    CONSTRAINT ck_controle_carga_fim

        CHECK (

            (status = 'em_execucao' AND fim IS NULL)

            OR (status IN ('sucesso', 'falha', 'interrompida') AND fim IS NOT NULL)

        ),

    CONSTRAINT ck_controle_carga_ativa

        CHECK (NOT carga_ativa OR status = 'sucesso'),

    CONSTRAINT ck_controle_carga_contagens_nao_negativas

        CHECK (

            quantidade_linhas >= 0

            AND quantidade_escolas >= 0

            AND quantidade_municipios >= 0

            AND quantidade_codigos_escola >= 0

            AND quantidade_codigos_municipio >= 0

            AND quantidade_metricas_catalogo >= 0

        ),

    CONSTRAINT ck_controle_carga_contagens_status

        CHECK (

            (

                status = 'sucesso'

                AND quantidade_linhas IS NOT NULL

                AND quantidade_escolas IS NOT NULL

                AND quantidade_municipios IS NOT NULL

                AND quantidade_codigos_escola IS NOT NULL

                AND quantidade_codigos_municipio IS NOT NULL

                AND quantidade_metricas_catalogo IS NOT NULL

            )

            OR (

                status <> 'sucesso'

                AND quantidade_linhas IS NULL

                AND quantidade_escolas IS NULL

                AND quantidade_municipios IS NULL

                AND quantidade_codigos_escola IS NULL

                AND quantidade_codigos_municipio IS NULL

                AND quantidade_metricas_catalogo IS NULL

            )

        )

);

CREATE INDEX idx_dim_escola_municipio

    ON public.dim_escola (id_municipio);



CREATE INDEX idx_fato_escola_codigo

    ON public.fato_rendimento_escolar (id_escola, co_entidade);



CREATE INDEX idx_fato_municipio

    ON public.fato_rendimento_escolar (id_municipio);


CREATE UNIQUE INDEX uq_controle_carga_ativa

    ON public.controle_carga (carga_ativa)

    WHERE carga_ativa = true;



COMMIT;
