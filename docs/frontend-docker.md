# Frontend no Nginx do servidor

O Nginx existente serve os arquivos React e encaminha `/api/*` ao backend.
O frontend fica na raiz de um dominio ou subdominio exclusivo.

## Build

Na raiz do projeto, gere os arquivos usando apenas Docker:

```bash
mkdir -p frontend/dist
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose -f compose.frontend.yml run --rm --build frontend-build
```

O container Node instala as dependencias na imagem, gera os arquivos em
`frontend/dist/` no host e termina. Nao inicia o backend nem um servidor web.
O UID/GID evita gerar arquivos pertencentes ao root no Linux. Cada build
substitui o conteudo anterior de `dist/`; copie-o ao Nginx depois de concluir.

Se preferir usar Node instalado na maquina:

```bash
cd frontend
npm ci
npm run build:server
```

O comando gera `frontend/dist/` com `VITE_API_URL=/api`, mesmo se `.env.local`
apontar para localhost. Essa variavel e usada durante o build, nao em runtime.
Nenhuma variavel adicional e necessaria no backend para essa configuracao.
Como frontend e API usam o mesmo dominio, nao e necessario configurar CORS.

## Arquivos no container Nginx existente

Copie o conteudo de `frontend/dist/` para um diretorio do servidor, como
`/srv/alpr/frontend/`, e adicione este volume ao servico Nginx no Compose dele:

```yaml
volumes:
  - /srv/alpr/frontend:/usr/share/nginx/html/alpr:ro
```

Preserve os demais volumes e configuracoes do seu Nginx. Recrie esse servico
apos adicionar o volume; reload sozinho nao adiciona um volume ao container.

## Rede com o backend

O Nginx deve compartilhar uma rede Docker com `alpr-api`. Descubra a rede
`public` do backend:

```bash
docker inspect alpr-api --format '{{json .NetworkSettings.Networks}}'
```

No Compose do Nginx existente, acrescente essa rede como externa e associe-a
ao servico Nginx, mantendo as redes que ele ja usa:

```yaml
services:
  nginx:
    networks:
      - alpr

networks:
  alpr:
    external: true
    name: nome-do-projeto_public
```

Substitua o nome da rede pelo encontrado no inspect.

## Configuracao do dominio

O arquivo `frontend/nginx.conf` e um exemplo de bloco `server` para o dominio
`alpr.exemplo.com`. Ajuste o dominio e incorpore `root`, `index`,
`client_max_body_size` e os dois blocos `location` ao seu `server` existente,
preservando certificados e configuracao HTTPS. Substitua locais duplicados.

`proxy_pass http://alpr-api:8000/` remove o prefixo `/api/` antes de encaminhar
ao backend. `localhost` dentro do container Nginx apontaria para o proprio Nginx.

Com o backend e o volume disponiveis, valide e recarregue:

```bash
docker exec nome-do-nginx nginx -t
docker exec nome-do-nginx nginx -s reload
curl -I https://alpr.exemplo.com/
curl https://alpr.exemplo.com/api/openapi.json
```

Recarregue o Nginx se o container do backend for recriado e mudar de IP.
Para atualizar o frontend, gere um novo build e substitua os arquivos no
diretorio montado, removendo assets antigos que nao sao mais usados.

Referencias: [redes Docker](https://docs.docker.com/compose/how-tos/networking/),
[proxy_pass](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).
