# ALPR API

Backend FastAPI para reconhecimento automático de placas, registro de eventos de entrada/saida e consulta protegida por autenticacao.

## Visao Geral

O sistema recebe imagens no endpoint `/alpr`, detecta placas, roda OCR e registra eventos no PostgreSQL. Usuarios humanos autenticam com JWT e refresh token. Clientes Raspberry usam um secret proprio, enviado somente para o `/alpr`.

Principais recursos:

- ALPR com detector YOLO e OCR.
- Eventos agrupados por veiculo.
- Autenticacao JWT com access token e refresh token.
- Validacao de `token_id` e `refresh_token_id` no Redis.
- Autorizacao por papeis: `admin` e `operador`.
- Cadastro de usuarios restrito a admins.
- Cadastro de hashes de clientes Raspberry restrito a admins.
- Secret de Raspberry de 256 bits gerado por script local.

## Arquitetura

```text
app/
  api/
    deps.py                  # dependencias FastAPI de auth/Raspberry
    routes/
      alpr.py                # POST /alpr
      auth.py                # login, refresh, logout
      eventos.py             # GET /eventos
      raspberry_clientes.py  # cadastro de hashes Raspberry
      usuarios.py            # cadastro de usuarios
  core/
    config.py                # env vars e constantes
  db/
    redis.py                 # conexao Redis
    session.py               # engine/session SQLAlchemy
  models/
    evento.py
    raspberry_cliente.py
    usuario.py
  schemas/
    auth.py
    evento.py
    raspberry.py
    usuario.py
  services/
    alpr_service.py
    auth_service.py
    evento_service.py
    plate_detector.py
    plate_ocr.py
    raspberry_service.py
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

## Variaveis de Ambiente

Exemplo em `.env.example`:

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

Em producao, troque obrigatoriamente:

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `ADMIN_PASSWORD`

Para gerar um `JWT_SECRET` forte:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Subindo com Docker

```bash
docker compose up --build
```

Servicos criados:

- `api`: FastAPI em `http://localhost:${API_PORT}`
- `postgres`: banco de dados
- `postgres-migrations`: executa todos os arquivos `db/migrations/*.sql`
- `redis`: armazenamento dos IDs de tokens ativos

## Migrações

As migrações ficam em `db/migrations`:

- `001_create_eventos.sql`: tabela de eventos.
- `002_create_usuarios.sql`: tabela de usuarios e remocao de tabela antiga de refresh tokens, se existir.
- `003_create_raspberry_clientes.sql`: tabela de clientes Raspberry.

O container `postgres-migrations` executa todos os arquivos `.sql` em ordem alfabetica.

## Autenticacao de Usuarios

### Papeis

- `admin`: cria usuarios e cadastra clientes Raspberry.
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

## Clientes Raspberry

O Raspberry nao usa JWT. Ele usa um secret de 256 bits. O banco armazena somente o hash SHA-256 desse secret.

### Gerar Secret

```bash
.venv/bin/python gerar_raspberry_secret.py
```

Saida:

```text
secret=<valor_para_o_raspberry>
chave_hash=<valor_para_cadastrar_no_backend>
```

Guarde o `secret` no Raspberry. Cadastre apenas o `chave_hash` no backend.

### Cadastrar Hash

Somente `admin`.

```http
POST /raspberry-clientes
Authorization: Bearer <access_token_admin>
Content-Type: application/json
```

```json
{
  "nome": "raspberry-portao-1",
  "chave_hash": "<sha256_hex_de_64_caracteres>"
}
```

Resposta:

```json
{
  "id": 1,
  "nome": "raspberry-portao-1",
  "ativo": true
}
```

## ALPR

Unico endpoint acessivel aos clientes Raspberry.

```http
POST /alpr
X-Raspberry-Secret: <secret_do_raspberry>
Content-Type: multipart/form-data
```

Campo do arquivo:

- `imagem`

Exemplo:

```bash
curl -X POST http://localhost:8000/alpr \
  -H "X-Raspberry-Secret: $RASPBERRY_SECRET" \
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

## Scripts

### Enviar imagens locais

```bash
RASPBERRY_SECRET=<secret> .venv/bin/python scriptImagens.py
```

### Cliente com camera

```bash
RASPBERRY_SECRET=<secret> .venv/bin/python scriptRequest.py
```

### Consultar eventos

```bash
ACCESS_TOKEN=<token> .venv/bin/python scriptEventos.py
```

## Testes

```bash
.venv/bin/python -m unittest discover -s tests
```

## Validacoes de Desenvolvimento

```bash
.venv/bin/python -m py_compile app/main.py app/api/deps.py app/api/routes/*.py app/services/*.py app/db/*.py gerar_raspberry_secret.py
docker compose config
```

## Seguranca

- O banco nao armazena refresh tokens nem secrets de Raspberry em texto puro.
- Refresh tokens sao rotacionados no `/auth/refresh`.
- Access tokens sao aceitos apenas se o `token_id` ainda existir no Redis.
- Clientes Raspberry acessam somente `/alpr`.
- Rotas administrativas exigem papel `admin`.
- `GET /eventos` exige `admin` ou `operador`.
- `GET /relatorios/*` exige `admin` ou `operador`.

Limite atual proposital: logout revoga o refresh token informado, mas nao revoga automaticamente todos os access tokens ja emitidos para o usuario. Para encerrar todas as sessoes de um usuario, remova as chaves `auth:access:*` e `auth:refresh:*` correspondentes no Redis ou adicione uma rotina administrativa dedicada.
