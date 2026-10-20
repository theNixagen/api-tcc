# Endpoints da API

Formato resumido para colar em post-its no Miro.

```text
POST /auth/login
Objetivo: autenticar usuario.
Auth: nenhuma.
Entrada: username, senha.
Saida: access_token, refresh_token.
```

```text
POST /auth/refresh
Objetivo: renovar sessao.
Auth: nenhuma.
Entrada: refresh_token.
Saida: novo access_token e refresh_token.
```

```text
POST /auth/logout
Objetivo: encerrar sessao.
Auth: nenhuma.
Entrada: refresh_token.
Saida: confirmacao de logout.
```

```text
POST /usuarios
Objetivo: criar usuario.
Auth: Bearer admin.
Entrada: username, senha, papel.
Saida: id, username, papel.
Papeis: admin, operador.
```

```text
POST /clientes
Objetivo: cadastrar cliente autorizado a enviar imagens.
Auth: Bearer admin.
Entrada: nome, chave_hash.
Saida: id, nome, ativo.
Obs: chave_hash e o SHA-256 do secret do cliente.
```

```text
POST /alpr
Objetivo: persistir imagem e enfileirar deteccao/OCR sem aguardar a leitura.
Auth: X-Cliente-Secret.
Entrada: imagem multipart e capturado_em opcional (ISO 8601 com fuso).
Saida: 202 com id e status; Location aponta para GET /alpr/{id}.
Regra: alterna entrada/saida por placa.
Fila: persistida em leituras, por ordem de ID, serializada por lock PostgreSQL.
Limites: 10 MiB por foto; arquivo vazio retorna 400; acima do limite retorna 413.
Migracoes: 004_create_leituras.sql, 005_operacao_leituras.sql e 006_revisao_sem_deteccao.sql.
Admissao: 503 se exceder ALPR_MAX_PENDING ou ALPR_MAX_PENDING_BYTES.
```

```text
GET /alpr/fila
Objetivo: consultar o resumo dos envios do cliente.
Auth: X-Cliente-Secret.
Saida: total, pendentes, processando, concluidas, erros, revisao e primeira_pendente (id, nome_arquivo,
criado_em), ou null quando nao houver pendencias.
Obs: pendentes exclui processando; revisao e subconjunto das concluidas; contagens restritas ao cliente.
```

```text
GET /alpr/{leitura_id}
Objetivo: consultar status e metadados de uma leitura.
Auth: X-Cliente-Secret, restrito ao cliente que enviou a imagem.
Saida: status (pendente/processando/concluida/erro), resultado, capturado_em,
captura_informada, iniciado_em, tentativas, tentativas_limite, proxima_tentativa_em,
imagem_disponivel, nome do arquivo, tipo, tamanho, datas,
duracao, erro e detections com placa, evento_id, confiancas de deteccao e OCR,
texto original do OCR, bbox, modelo e imgsz.
Obs: sem placas, resultado=revisao e detections vazio; a revisao usa a imagem original.
Baixa confianca/formato invalido tambem gera revisao, sem evento automatico.
Erro: 404 se nao existir ou pertencer a outro cliente.
```

```text
GET /eventos
Objetivo: listar historico de eventos por placa.
Auth: Bearer admin ou operador.
Entrada: placa, inicio/fim com fuso, limit (1-500), offset.
Saida: veiculos com lista de eventos, total, limit, offset.
```

```text
GET /relatorios/acessos-diarios
Objetivo: relatorio diario de acessos.
Auth: Bearer admin ou operador.
Entrada: data opcional, placa opcional, limit (1-500), offset.
Saida: veiculos com pares entrada/saida, fuso, total, limit, offset.
Obs: dia definido por REPORT_TIMEZONE, padrao America/Cuiaba.
```

```text
GET /eventos/acessos
Auth: Bearer admin ou operador.
Entrada: placa, entrada_inicio/fim, saida_inicio/fim (com fuso), limit (1-200), offset.
Saida: itens (pares completos de entrada/saida), total, limit, offset.
```

```text
GET /leituras
GET /leituras/fila
GET /leituras/{id}
GET /leituras/{id}/imagem
GET /leituras/{id}/revisoes
Auth: Bearer admin ou operador.
Listagem: status, resultado, placa, limit (1-100), offset; nao inclui bytes das fotos.
Imagem: bytes originais; 404 se removida pela retencao.
Revisoes: usuario, acao, placa anterior/corrigida, motivo, evento e data.
```

```text
POST /leituras/{id}/reprocessar
Auth: Bearer admin ou operador.
Somente status erro e imagem disponivel; preserva contador e renova lote de tentativas.
Saida: 202 com id e status pendente; 409 se nao elegivel; 503 se atingir cota.
```

```text
POST /leituras/deteccoes/{id}/revisar
Auth: Bearer admin ou operador.
Entrada: acao (aceitar/rejeitar), motivo; para aceitar: placa e tipo_evento (entrada/saida).
Aceitar exige placa brasileira valida, cria evento com horario da captura e registra auditoria.
Rejeitar nao cria evento. Deteccao ja revisada retorna 409.
```

```text
POST /leituras/{id}/revisar
Auth: Bearer admin ou operador.
Revisa uma imagem concluida, pendente de revisao e sem deteccoes.
Entrada: acao (aceitar/rejeitar), motivo; para aceitar: placa e tipo_evento.
Aceitar exige imagem original disponivel e placa brasileira valida; cria evento com horario da captura.
Rejeitar registra a decisao sem criar evento. Ambas as acoes geram auditoria vinculada a leitura.
Nao cria metadados de deteccao ficticios. Leitura ja revisada ou com deteccoes retorna 409.
```
