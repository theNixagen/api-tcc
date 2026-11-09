# Frontend com Nginx externo

O caminho das requisicoes fica:

```text
Navegador -> Nginx do servidor (HTTPS) -> alpr-frontend:80
                                         /       -> arquivos React
                                         /api/*  -> api:8000/*
```

O container do frontend compila o React com Node e serve os arquivos com Nginx.
O navegador usa `/api` no mesmo dominio; nao usa `localhost:8000` nem precisa de
outro dominio para a API. O `.env.local` do frontend fica fora do build Docker.
O HTTPS continua no Nginx que ja existe no servidor.

## Rede e inicializacao

Descubra a rede Docker do Nginx existente (substitua `nome-do-nginx`):

```bash
docker inspect nome-do-nginx --format '{{json .NetworkSettings.Networks}}'
```

Na raiz do projeto, defina o nome dessa rede e inicie o frontend:

```bash
export PROXY_NETWORK=nome-da-rede-do-nginx
docker compose -f compose.yml -f compose.frontend.yml up -d --build frontend
```

A rede deve existir. O backend deve estar rodando pelo `compose.yml` do mesmo
projeto, pois o frontend acessa o servico `api` pela rede `public`.
Se ainda nao estiver rodando, inicie os dois:

```bash
docker compose -f compose.yml -f compose.frontend.yml up -d --build api frontend
```

Use os mesmos arquivos `-f` e o mesmo `PROXY_NETWORK` nos comandos seguintes.
Tambem pode salvar `PROXY_NETWORK` no `.env` do Compose. O frontend nao publica
portas no host; o Nginx existente acessa `alpr-frontend:80` pela rede compartilhada.

## Configuracao do Nginx existente

No bloco `server` do dominio escolhido, mantenha a configuracao de certificados
e HTTPS existente e adicione esta localizacao:

```nginx
client_max_body_size 11m;

location / {
    proxy_pass http://alpr-frontend:80;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Este exemplo usa um dominio ou subdominio exclusivo, como `alpr.exemplo.com`,
com o frontend na raiz `/`. Substitua uma localizacao `/` existente em vez de
duplicar o bloco. Preserve outras configuracoes necessarias do seu servidor.

Depois de subir o frontend e editar o arquivo montado no Nginx:

```bash
docker exec nome-do-nginx nginx -t
docker exec nome-do-nginx nginx -s reload
```

O Nginx externo precisa ser recarregado se o frontend for recriado e mudar de IP.
O Nginx do frontend atualiza automaticamente a resolucao do backend pelo DNS Docker.

## Atualizacao e verificacao

```bash
docker compose -f compose.yml -f compose.frontend.yml up -d --build frontend
docker compose -f compose.yml -f compose.frontend.yml logs --tail=50 frontend
curl -I https://alpr.exemplo.com/
curl https://alpr.exemplo.com/api/openapi.json
```

Recarregue tambem o Nginx externo apos recriar o frontend.

Referencias: [build em etapas](https://docs.docker.com/build/building/multi-stage/),
[redes entre projetos Compose](https://docs.docker.com/compose/how-tos/networking/),
[proxy_pass](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).
