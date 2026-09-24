# ALPR API

Backend FastAPI para reconhecimento automático de placas, registro de eventos de entrada/saida e consulta protegida por autenticacao.

## Visao Geral

O sistema recebe imagens no endpoint `/alpr`, detecta placas, roda OCR e registra eventos no PostgreSQL. Usuarios humanos autenticam com JWT e refresh token. Clientes usam um secret proprio, enviado somente para o `/alpr`.

Principais recursos:

- ALPR com detector YOLO e OCR.
- Eventos agrupados por veiculo.
- Autenticacao JWT com access token e refresh token.
- Validacao de `token_id` e `refresh_token_id` no Redis.
- Autorizacao por papeis: `admin` e `operador`.
- Cadastro de usuarios restrito a admins.
- Cadastro de hashes de clientes restrito a admins.
- Secret de cliente de 256 bits gerado por script local.

## Arquitetura

```text
app/
  api/
    deps.py                  # dependencias FastAPI de auth/cliente
    routes/
      alpr.py                # POST /alpr
      auth.py                # login, refresh, logout
      eventos.py             # GET /eventos
      clientes.py            # cadastro de hashes de clientes
      usuarios.py            # cadastro de usuarios
  core/
    config.py                # env vars e constantes
  db/
    redis.py                 # conexao Redis
    session.py               # engine/session SQLAlchemy
  models/
    evento.py
    cliente.py
    usuario.py
  schemas/
    auth.py
    evento.py
    cliente.py
    usuario.py
  services/
    alpr_service.py
    auth_service.py
    evento_service.py
    plate_detector.py
    plate_ocr.py
    cliente_service.py
    usuario_service.py
```

Camadas:

- `routes`: contrato HTTP, status code e dependencies.
- `schemas`: DTOs Pydantic e tipos de resposta.
- `services`: regras de negocio.
- `models`: mapeamento SQLAlchemy.
- `db`: conexoes com PostgreSQL e Redis.
- `core`: configuracao.

## Dependencias Externas

- PostgreSQL: dados permanentes.
- Redis: estado de sessao dos JWTs.
- Modelo YOLO em `models/plateDetector.pt`.
- PaddleOCR para OCR.

## Configuracao

Para rodar tudo via Docker, use `.env.example`:

```env
POSTGRES_DB=alpr
POSTGRES_USER=alpr
POSTGRES_PASSWORD=alpr
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

API_PORT=8000
REDIS_URL=redis://redis:6379/0

JWT_SECRET=troque-essa-chave-em-producao
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

Para desenvolvimento local, onde a API roda no seu `.venv` e apenas PostgreSQL/Redis rodam no Compose, use `.env.development.local`:

```env
POSTGRES_DB=alpr
POSTGRES_USER=alpr
POSTGRES_PASSWORD=alpr
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

DATABASE_URL=postgresql://alpr:alpr@localhost:5432/alpr
API_PORT=8000
REDIS_URL=redis://localhost:6379/0

JWT_SECRET=troque-essa-chave-em-producao
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

Em producao, troque obrigatoriamente:

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `ADMIN_PASSWORD`

Para gerar um `JWT_SECRET` forte:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Opcao 1: Rodar Tudo Com Docker

Crie o `.env` a partir do exemplo Docker:

```bash
cp .env.example .env
```

Suba todos os servicos:

```bash
docker compose up --build
```

Servicos criados:

- `api`: FastAPI em `http://localhost:${API_PORT}`
- `postgres`: banco de dados
- `postgres-migrations`: executa todos os arquivos `db/migrations/*.sql`
- `redis`: armazenamento dos IDs de tokens ativos

## Opcao 2: Rodar API Local Sem Container

Neste modo, a API roda no seu Python local. O Compose sobe apenas PostgreSQL e Redis.

Prerequisitos instalados no seu PC:

- Python 3.12
- Docker
- bibliotecas do sistema usadas por OpenCV/Paddle/YOLO, equivalentes a `libglib2.0-0`, `libgl1` e `libgomp1` no Debian/Ubuntu

Crie e ative o ambiente Python:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Suba apenas PostgreSQL e Redis:

```bash
docker compose -f compose.yml --env-file .env.development.local up -d --force-recreate postgres redis
docker compose -f compose.yml --env-file .env.development.local ps
```

Se o Docker negar acesso ao socket, execute com `sudo` ou adicione seu usuario ao grupo `docker`:

```bash
sudo docker compose -f compose.yml --env-file .env.development.local up -d --force-recreate postgres redis
sudo usermod -aG docker "$USER"
```

Depois de alterar o grupo, saia e entre de novo na sessao do terminal.

Execute as migracoes e suba a API no seu PC:

```bash
. .venv/bin/activate
python scripts/migrate.py && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API fica em `http://localhost:8000`.
O PostgreSQL de desenvolvimento fica publicado em `localhost:5433`, para evitar conflito com algum Postgres local em `5432`.
Se a migracao falhar com `Connection refused`, rode `docker compose -f compose.yml --env-file .env.development.local ps` e tente de novo quando `alpr-postgres` estiver `healthy`.

Se o Postgres ja tiver sido criado antes com outra senha, e voce nao precisar manter os dados locais, recrie o volume:

```bash
docker compose -f compose.yml --env-file .env.development.local down -v
docker compose -f compose.yml --env-file .env.development.local up -d --force-recreate postgres redis
python scripts/migrate.py
```

## Migrações

As migrações ficam em `db/migrations`:

- `001_create_eventos.sql`: tabela de eventos.
- `002_create_usuarios.sql`: tabela de usuarios e remocao de tabela antiga de refresh tokens, se existir.
- `003_create_clientes.sql`: tabela de clientes.

No Docker completo, o container `postgres-migrations` executa todos os arquivos `.sql` em ordem alfabetica.
No desenvolvimento local, use:

```bash
python scripts/migrate.py
```

## Autenticacao de Usuarios

### Papeis

- `admin`: cria usuarios e cadastra clientes.
- `operador`: consulta eventos.

### Login

```http
POST /auth/login
Content-Type: application/json
```

```json
{
  "username": "admin",
  "senha": "admin123"
}
```

Resposta:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### Claims dos Tokens

Access token:

```json
{
  "typ": "access",
  "sub": "1",
  "username": "admin",
  "papel": "admin",
  "token_id": "...",
  "jti": "...",
  "exp": 1234567890
}
```

Refresh token:

```json
{
  "typ": "refresh",
  "sub": "1",
  "username": "admin",
  "papel": "admin",
  "refresh_token_id": "...",
  "jti": "...",
  "exp": 1234567890
}
```

O JWT precisa ser valido e o ID correspondente precisa existir no Redis:

- `auth:access:<token_id>`
- `auth:refresh:<refresh_token_id>`

### Refresh

```http
POST /auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "..."
}
```

O refresh token antigo e revogado no Redis e um novo par de tokens e emitido.

### Logout

```http
POST /auth/logout
Content-Type: application/json
```

```json
{
  "refresh_token": "..."
}
```

Remove o `refresh_token_id` do Redis.

## Usuarios

### Criar Usuario

Somente `admin`.

```http
POST /usuarios
Authorization: Bearer <access_token_admin>
Content-Type: application/json
```

```json
{
  "username": "operador1",
  "senha": "senha-forte",
  "papel": "operador"
}
```

Resposta:

```json
{
  "id": 2,
  "username": "operador1",
  "papel": "operador"
}
```

## Clientes

O cliente nao usa JWT. Ele usa um secret de 256 bits. O banco armazena somente o hash SHA-256 desse secret.

### Gerar Secret

```bash
.venv/bin/python gerar_cliente_secret.py
```

Saida:

```text
secret=<valor_para_o_cliente>
chave_hash=<valor_para_cadastrar_no_backend>
```

Guarde o `secret` no cliente. Cadastre apenas o `chave_hash` no backend.

### Cadastrar Hash

Somente `admin`.

```http
POST /clientes
Authorization: Bearer <access_token_admin>
Content-Type: application/json
```

```json
{
  "nome": "cliente-portao-1",
  "chave_hash": "<sha256_hex_de_64_caracteres>"
}
```

Resposta:

```json
{
  "id": 1,
  "nome": "cliente-portao-1",
  "ativo": true
}
```

## ALPR

Unico endpoint acessivel aos clientes.

```http
POST /alpr
X-Cliente-Secret: <secret_do_cliente>
Content-Type: multipart/form-data
```

Campo do arquivo:

- `imagem`

Exemplo:

```bash
curl -X POST http://localhost:8000/alpr \
  -H "X-Cliente-Secret: $CLIENTE_SECRET" \
  -F "imagem=@imagens/crv.jpeg"
```

Resposta:

```json
{
  "detections": [
    {
      "placa": "ABC1234",
      "evento": {
        "id": 1,
        "tipo_evento": "entrada"
      },
      "confidence_detection": 0.91,
      "bbox": [10, 20, 100, 60]
    }
  ]
}
```

## Eventos

Somente `admin` ou `operador`.

```http
GET /eventos
Authorization: Bearer <access_token>
```

Resposta:

```json
{
  "veiculos": [
    {
      "placa": "ABC1234",
      "eventos": [
        {
          "id": 1,
          "tipo_evento": "entrada",
          "data_hora": "2026-09-01T10:00:00Z"
        }
      ]
    }
  ]
}
```

## Relatorios

Somente `admin` ou `operador`.

```http
GET /relatorios/acessos-diarios?data=2026-09-02&placa=ABC1234
Authorization: Bearer <access_token>
```

Filtros:

- `data`: data das entradas do relatorio. Se omitida, usa o dia atual.
- `placa`: opcional, filtra uma placa especifica.

Resposta:

```json
{
  "data": "2026-09-02",
  "veiculos": [
    {
      "placa": "ABC1234",
      "acessos": [
        {
          "data_hora_entrada": "2026-09-02T08:00:00Z",
          "data_hora_saida": "2026-09-02T12:00:00Z"
        },
        {
          "data_hora_entrada": "2026-09-02T14:00:00Z",
          "data_hora_saida": null
        }
      ]
    }
  ]
}
```

## Testes

```bash
.venv/bin/python -m unittest discover -s tests
```

## Validacoes de Desenvolvimento

```bash
.venv/bin/python -m py_compile app/main.py app/api/deps.py app/api/routes/*.py app/services/*.py app/db/*.py app/core/*.py scripts/migrate.py gerar_cliente_secret.py
.venv/bin/python -m unittest discover -s tests
docker compose config
docker compose -f compose.yml --env-file .env.development.local config
```

## Seguranca

- O banco nao armazena refresh tokens nem secrets de cliente em texto puro.
- Refresh tokens sao rotacionados no `/auth/refresh`.
- Access tokens sao aceitos apenas se o `token_id` ainda existir no Redis.
- Clientes acessam somente `/alpr`.
- Rotas administrativas exigem papel `admin`.
- `GET /eventos` exige `admin` ou `operador`.
- `GET /relatorios/*` exige `admin` ou `operador`.

Limite atual proposital: logout revoga o refresh token informado, mas nao revoga automaticamente todos os access tokens ja emitidos para o usuario. Para encerrar todas as sessoes de um usuario, remova as chaves `auth:access:*` e `auth:refresh:*` correspondentes no Redis ou adicione uma rotina administrativa dedicada.
