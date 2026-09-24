# ALPR API - Bruno

Abra esta pasta como collection no Bruno:

```text
bruno/ALPR API
```

Selecione o environment `Local`.

Fluxo basico:

1. Rode `Auth/Login` para gravar `access_token` e `refresh_token` no environment.
2. Use `Usuarios/Criar Usuario`, `Clientes/Criar Cliente`, `Eventos/Listar Eventos` e `Relatorios/Acessos Diarios` com o bearer token salvo.
3. Use `ALPR/Processar Imagem` depois de cadastrar o cliente com `Clientes/Criar Cliente`.

Variaveis para ajustar:

- `base_url`: URL da API.
- `admin_username`: usuario do admin inicial.
- `admin_senha`: senha do admin inicial, configurada como secret no environment.
- `cliente_chave_hash`: hash ja configurado para o `cliente_secret` local.
- `cliente_secret`: secret configurado como secret no environment e enviado pelo cliente no header `X-Cliente-Secret`.
- `imagem_path`: caminho do arquivo usado no upload multipart.
- `relatorio_data`: data usada no relatorio diario de acessos.
- `relatorio_placa`: placa opcional usada no filtro do relatorio diario.
