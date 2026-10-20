ALTER TABLE public.leituras DROP CONSTRAINT IF EXISTS leituras_status_check;
ALTER TABLE public.leituras ADD CONSTRAINT leituras_status_check
    CHECK (status IN ('pendente', 'processando', 'concluida', 'erro'));
ALTER TABLE public.leituras ALTER COLUMN imagem DROP NOT NULL;
ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS capturado_em TIMESTAMPTZ;
UPDATE public.leituras SET capturado_em = criado_em WHERE capturado_em IS NULL;
ALTER TABLE public.leituras ALTER COLUMN capturado_em SET NOT NULL;
ALTER TABLE public.leituras ALTER COLUMN capturado_em SET DEFAULT NOW();
ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS captura_informada BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS iniciado_em TIMESTAMPTZ;
ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS tentativas INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS tentativas_limite INTEGER NOT NULL DEFAULT 3;
ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS proxima_tentativa_em TIMESTAMPTZ;
ALTER TABLE public.leituras ADD COLUMN IF NOT EXISTS resultado VARCHAR(20);
ALTER TABLE public.metadados_leitura ADD COLUMN IF NOT EXISTS resultado VARCHAR(20) NOT NULL DEFAULT 'revisao';
ALTER TABLE public.metadados_leitura ADD COLUMN IF NOT EXISTS motivo TEXT;
UPDATE public.metadados_leitura SET resultado = 'aceita' WHERE evento_id IS NOT NULL;
UPDATE public.leituras SET resultado = CASE
    WHEN EXISTS (SELECT 1 FROM public.metadados_leitura m WHERE m.leitura_id = leituras.id AND m.resultado = 'revisao') THEN 'revisao'
    WHEN EXISTS (SELECT 1 FROM public.metadados_leitura m WHERE m.leitura_id = leituras.id AND m.resultado = 'aceita') THEN 'aceita'
    ELSE 'sem_placa' END
WHERE status = 'concluida' AND resultado IS NULL;

CREATE TABLE IF NOT EXISTS public.revisoes_leitura (
    id SERIAL PRIMARY KEY,
    metadado_id INTEGER NOT NULL REFERENCES public.metadados_leitura(id),
    usuario_id INTEGER REFERENCES public.usuarios(id) ON DELETE SET NULL,
    username TEXT NOT NULL,
    acao VARCHAR(10) NOT NULL CHECK (acao IN ('aceitar', 'rejeitar')),
    placa_anterior TEXT NOT NULL,
    placa_corrigida TEXT,
    motivo TEXT NOT NULL,
    evento_id INTEGER REFERENCES public.eventos(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_eventos_placa_data ON public.eventos(placa, data_hora, id);
CREATE INDEX IF NOT EXISTS ix_eventos_data ON public.eventos(data_hora, id);
CREATE INDEX IF NOT EXISTS ix_leituras_cliente_status ON public.leituras(cliente_id, status, id);
CREATE INDEX IF NOT EXISTS ix_leituras_data ON public.leituras(criado_em DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_leituras_resultado ON public.leituras(resultado, id);
CREATE INDEX IF NOT EXISTS ix_metadados_placa ON public.metadados_leitura(placa, leitura_id);
