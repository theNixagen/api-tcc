-- As migrações são reaplicadas em cada inicialização. A 007 renomeia esta tabela.
DO $$
BEGIN
    IF to_regclass('public.cameras') IS NULL THEN
        CREATE TABLE IF NOT EXISTS public.clientes (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(80) NOT NULL,
            chave_hash VARCHAR(64) NOT NULL UNIQUE,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    END IF;
END $$;
