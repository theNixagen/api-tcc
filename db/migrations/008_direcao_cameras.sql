ALTER TABLE public.cameras ADD COLUMN IF NOT EXISTS direcao VARCHAR(10)
    CONSTRAINT cameras_direcao_check CHECK (direcao IN ('entrada', 'saida'));

ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS direcao VARCHAR(10)
    CONSTRAINT leituras_direcao_check CHECK (direcao IN ('entrada', 'saida'));
