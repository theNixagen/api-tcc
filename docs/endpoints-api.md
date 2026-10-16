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
Entrada: imagem multipart.
Saida: 202 com id e status; Location aponta para GET /alpr/{id}.
Regra: alterna entrada/saida por placa.
Fila: persistida em leituras, por ordem de ID, serializada por lock PostgreSQL.
Limites: 10 MiB por foto; arquivo vazio retorna 400; acima do limite retorna 413.
Migracao: 004_create_leituras.sql cria leituras e metadados_leitura.
```

```text
GET /alpr/fila
Objetivo: consultar o resumo dos envios do cliente.
Auth: X-Cliente-Secret.
Saida: total, pendentes, concluidas, erros e primeira_pendente (id, nome_arquivo,
criado_em), ou null quando nao houver pendencias.
Obs: pendentes inclui a foto em processamento; contagens restritas ao cliente.
```

```text
GET /alpr/{leitura_id}
Objetivo: consultar status e metadados de uma leitura.
Auth: X-Cliente-Secret, restrito ao cliente que enviou a imagem.
Saida: status (pendente/concluida/erro), nome do arquivo, tipo, tamanho, datas,
duracao, erro e detections com placa, evento_id, confiancas de deteccao e OCR,
texto original do OCR, bbox, modelo e imgsz.
Obs: durante a inferencia o status permanece pendente; sem placas, detections e vazio.
Erro: 404 se nao existir ou pertencer a outro cliente.
```

```text
GET /eventos
Objetivo: listar historico de eventos por placa.
Auth: Bearer admin ou operador.
Entrada: nenhuma.
Saida: veiculos com lista de eventos.
```

```text
GET /relatorios/acessos-diarios
Objetivo: relatorio diario de acessos.
Auth: Bearer admin ou operador.
Entrada: data opcional, placa opcional.
Saida: veiculos com pares entrada/saida.
```
