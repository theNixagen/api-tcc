ALTER TABLE public.revisoes_leitura ADD COLUMN IF NOT EXISTS leitura_id INTEGER
    REFERENCES public.leituras(id);
UPDATE public.revisoes_leitura r SET leitura_id = m.leitura_id
FROM public.metadados_leitura m
WHERE r.metadado_id = m.id AND r.leitura_id IS NULL;
ALTER TABLE public.revisoes_leitura ALTER COLUMN leitura_id SET NOT NULL;
ALTER TABLE public.revisoes_leitura ALTER COLUMN metadado_id DROP NOT NULL;
CREATE INDEX IF NOT EXISTS ix_revisoes_leitura_leitura_id
    ON public.revisoes_leitura(leitura_id, id);

-- Inclui leituras antigas sem deteccao na fila de revisao, preservando o historico.
UPDATE public.leituras l SET resultado = 'revisao'
WHERE l.status = 'concluida' AND l.resultado = 'sem_placa'
  AND NOT EXISTS (SELECT 1 FROM public.metadados_leitura m WHERE m.leitura_id = l.id);
