DO $$
BEGIN
    IF to_regclass('public.cameras') IS NULL THEN
        ALTER TABLE public.clientes RENAME TO cameras;
        ALTER TABLE public.leituras RENAME COLUMN cliente_id TO camera_id;
        ALTER TABLE public.leituras RENAME CONSTRAINT leituras_cliente_id_fkey TO leituras_camera_id_fkey;
        ALTER TABLE public.cameras RENAME CONSTRAINT clientes_pkey TO cameras_pkey;
        ALTER TABLE public.cameras RENAME CONSTRAINT clientes_chave_hash_key TO cameras_chave_hash_key;
        ALTER SEQUENCE public.clientes_id_seq RENAME TO cameras_id_seq;
        ALTER INDEX IF EXISTS public.ix_leituras_cliente_status RENAME TO ix_leituras_camera_status;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_leituras_camera_status ON public.leituras(camera_id, status, id);
