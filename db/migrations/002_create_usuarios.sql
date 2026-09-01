CREATE TABLE IF NOT EXISTS public.usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    senha_hash VARCHAR(200) NOT NULL,
    papel VARCHAR(20) NOT NULL
        CHECK (papel IN ('operador', 'admin')),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
