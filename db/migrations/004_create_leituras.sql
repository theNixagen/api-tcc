CREATE TABLE IF NOT EXISTS public.leituras (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES public.clientes(id) ON DELETE SET NULL,
    nome_arquivo TEXT NOT NULL,
    content_type TEXT,
    imagem BYTEA NOT NULL,
    tamanho_bytes INTEGER NOT NULL CHECK (tamanho_bytes > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'concluida', 'erro')),
    erro TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalizado_em TIMESTAMPTZ,
    duracao_ms DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS ix_leituras_pendentes
    ON public.leituras (id) WHERE status = 'pendente';

CREATE TABLE IF NOT EXISTS public.metadados_leitura (
    id SERIAL PRIMARY KEY,
    leitura_id INTEGER NOT NULL REFERENCES public.leituras(id) ON DELETE CASCADE,
    evento_id INTEGER REFERENCES public.eventos(id) ON DELETE SET NULL,
    placa TEXT NOT NULL,
    texto_ocr TEXT NOT NULL,
    confianca_deteccao DOUBLE PRECISION NOT NULL,
    confianca_ocr DOUBLE PRECISION,
    bbox JSON NOT NULL,
    modelo TEXT NOT NULL,
    imgsz INTEGER NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_metadados_leitura_leitura_id
    ON public.metadados_leitura (leitura_id);
