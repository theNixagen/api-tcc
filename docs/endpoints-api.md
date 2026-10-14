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
Objetivo: processar imagem e registrar entrada/saida.
Auth: X-Cliente-Secret.
Entrada: imagem multipart.
Saida: placa, evento, confianca, bbox.
Regra: alterna entrada/saida por placa.
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
