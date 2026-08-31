CREATE TABLE IF NOT EXISTS public.eventos (
    id SERIAL PRIMARY KEY,

    tipo_evento VARCHAR(10) NOT NULL
        CHECK (tipo_evento IN ('entrada', 'saida')),

    data_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    placa VARCHAR(10) NOT NULL
);
