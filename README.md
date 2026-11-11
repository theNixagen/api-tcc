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
REDIS_URL=redis://localhost:6377/0

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
- `004_create_leituras.sql`: fila persistente de fotos e metadados de deteccao/OCR.
- `005_operacao_leituras.sql`: captura, tentativas, status processando, revisao auditada e indices.
- `006_revisao_sem_deteccao.sql`: revisao da imagem original sem deteccoes, incluindo leituras antigas sem placa.

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
  "sid": "...",
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
  "sid": "...",
  "jti": "...",
  "exp": 1234567890
}
```

O JWT precisa ser valido e o ID correspondente precisa existir no Redis:

- `auth:access:<token_id>`
- `auth:refresh:<refresh_token_id>`
- `auth:session:<sid>` (compartilhada pelo par de tokens e suas renovacoes)

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

Remove o refresh informado e a sessao do Redis, invalidando tambem os access tokens dessa sessao.

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

Clientes usam `/alpr` e suas consultas com `X-Cliente-Secret`.

As fotos sao salvas no PostgreSQL e entram em uma fila por ordem de ID.
O POST retorna `202 Accepted` com o ID, sem aguardar deteccao ou OCR.
O worker consulta a fila a cada segundo e processa uma foto por vez; um lock do
PostgreSQL impede processamento simultaneo entre instancias da API.
Envios pendentes sobrevivem a reinicios. Uma interrupcao durante a leitura reverte
a transacao e permite nova tentativa, sem duplicar eventos confirmados.
Cada foto pode ter ate 10 MiB; acima disso a API retorna `413`, e arquivo vazio
retorna `400`. A admissao tem cota global de 1000 fotos e 256 MiB pendentes/em processamento;
quando atingida retorna `503` com `Retry-After`.

Antes de iniciar a API, aplique todas as migracoes, incluindo `006_revisao_sem_deteccao.sql`, pelo
fluxo de migracoes existente (`python scripts/migrate.py` ou o servico
`postgres-migrations` do Compose).

```http
POST /alpr
X-Cliente-Secret: <secret_do_cliente>
Content-Type: multipart/form-data
```

Campo do arquivo:

- `imagem`
- `capturado_em`: opcional, ISO 8601 com fuso, por exemplo `2026-10-20T14:00:00-04:00`.
  O evento usa esse horario. Sem o campo, usa o recebimento e marca `captura_informada=false`;
  a API nao pode recuperar o horario real de uma captura que o cliente nao informou.

Exemplo:

```bash
curl -X POST http://localhost:8000/alpr \
  -H "X-Cliente-Secret: $CLIENTE_SECRET" \
  -F "imagem=@imagens/crv.jpeg"
```

Resposta do envio (`202`, com `Location: /alpr/1`):

```json
{"id": 1, "status": "pendente"}
```

Consulte `GET /alpr/1` com o mesmo `X-Cliente-Secret`. O cliente so pode consultar
seus proprios envios. Os status sao `pendente`, `processando`, `concluida` e `erro`.
O resultado e separado: `aceita`, `revisao` ou `rejeitada`.
Uma imagem sem deteccoes tambem recebe `revisao`, com `detections` vazio.
Cada deteccao conserva seu proprio resultado/motivo; uma leitura com qualquer
deteccao pendente de revisao tem resultado `revisao`.

Para consultar o resumo da fila, use `GET /alpr/fila` com o mesmo secret:

```json
{
  "total": 11,
  "pendentes": 2,
  "processando": 1,
  "concluidas": 7,
  "erros": 1,
  "revisao": 2,
  "primeira_pendente": {
    "id": 9,
    "nome_arquivo": "foto.jpg",
    "criado_em": "2026-10-16T12:00:00Z"
  }
}
```

As contagens incluem apenas os envios do cliente autenticado. `pendentes` nao inclui
a foto em processamento. `revisao` e um subconjunto das concluidas, nao deve ser
somado ao total. `primeira_pendente` e `null` quando nao ha pendencias.

Exemplo de consulta concluida (campos de data omitidos):

```json
{
  "id": 1,
  "status": "concluida",
  "nome_arquivo": "crv.jpeg",
  "content_type": "image/jpeg",
  "tamanho_bytes": 123456,
  "duracao_ms": 250.5,
  "erro": null,
  "detections": [
    {
      "id": 1,
      "placa": "ABC1234",
      "texto_ocr": "ABC-1234",
      "evento_id": 1,
      "confianca_deteccao": 0.91,
      "confianca_ocr": 0.95,
      "bbox": [10, 20, 100, 60],
      "modelo": "plateDetector.onnx",
      "imgsz": 640
    }
  ]
}
```

`leituras` guarda arquivo original, cliente, nome, tipo, tamanho, datas, duracao,
status e erro. `metadados_leitura` guarda uma linha por deteccao, com vinculo ao
envio e ao evento, placa, texto original do OCR, confiancas, bbox, modelo e imgsz.
Falhas revertem eventos e metadados parciais; a mensagem e persistida em `leituras.erro`.

Para depuracao, cada placa detectada e exportada antes do OCR para
`logs/recortes/leitura_<id>_placa_<numero>.jpg`. O terminal da API mostra o ID da
leitura, arquivo original, coordenadas e confiancas de deteccao e OCR em percentual.
Se nao houver deteccao, o terminal informa isso e nenhum recorte e criado.
No Compose, `./logs` e montado em `/app/logs`; acompanhe com
`docker compose logs -f api`. Os recortes permanecem mesmo se o OCR falhar;
falhas ao exportar sao registradas e nao interrompem a leitura.

## Operacao e revisao das leituras

O frontend tem uma aba **Leituras** para `operador` e `admin`, com fila, filtros,
paginacao, imagem original, horarios, confiancas, tentativas, erros e historico de revisoes.
As rotas `/leituras` usam JWT; o secret da camera nao e necessario no painel.
O botao **Ver leitura** abre uma pagina exclusiva em `#/leituras/<id>`, com
link de volta para a listagem. O endereco permite acesso direto, recarga e
navegacao pelos botoes voltar/avancar do navegador.

Uma placa so gera evento automaticamente se seguir o formato brasileiro antigo
(`ABC1234`) ou Mercosul (`ABC1D23`) e atingir ambos os limites de confianca.
Os valores iniciais sao **0.70 para deteccao** e **0.80 para OCR**, configuraveis
por `DETECTION_MIN_CONFIDENCE` e `OCR_MIN_CONFIDENCE`. Sao valores provisórios,
nao calibrados: avalie-os com fotos rotuladas das cameras antes de confiar nos resultados.
O detector coleta candidatos a partir de 0.40; os candidatos abaixo do limite
de aceitacao, com texto invalido ou confianca OCR ausente ficam para revisao.

Na revisao, o operador informa placa, entrada/saida e justificativa para aceitar,
ou apenas a justificativa para rejeitar. A auditoria preserva usuario, texto anterior,
correcao, acao, motivo, evento e data. Uma deteccao ja revisada nao pode criar outro evento.
Se o detector nao encontrar placas, a mesma tela oferece a revisao da imagem
original: informar uma placa brasileira valida e entrada/saida cria um evento
com o horario da captura; rejeitar registra a justificativa sem criar evento.
Nao sao inventados metadados de deteccao, coordenadas ou confiancas para uma
placa informada manualmente. Essa auditoria fica vinculada diretamente a leitura.
Uma leitura ja aceita/rejeitada nao pode ser revisada novamente por essa rota.
Se a foto antiga ja tiver sido removida pela retencao, somente a rejeicao fica disponivel.
As novas leituras sem deteccao preservam a imagem enquanto aguardam revisao.

O worker mantem o modelo em um subprocesso reutilizavel. `ALPR_TIMEOUT_SECONDS=120`
limita a inferencia (incluindo a inicializacao do modelo); timeout encerra o subprocesso.
`ALPR_MAX_ATTEMPTS=3` limita as tentativas automaticas, com espera de 5 segundos
entre falhas. O status `processando`, inicio e contador sao persistidos antes da
inferencia. Tarefas abandonadas sao recuperadas ao adquirir o lock global.
O painel permite reprocessar erros com imagem disponivel; preserva o contador
total e concede um novo lote de tentativas. Eventos e metadados sao confirmados
juntos, somente se o resultado ainda pertence a tentativa atual.

`ALPR_MAX_PENDING` e `ALPR_MAX_PENDING_BYTES` controlam as cotas da fila.
`IMAGE_RETENTION_DAYS=30` remove automaticamente os bytes de originais finalizados
ha mais de 30 dias, exceto os que aguardam revisao. Tambem remove recortes antigos
de `logs/recortes`. Nomes, datas, metadados, auditoria e eventos permanecem no banco.
A limpeza e verificada a cada hora pelo worker; `IMAGE_RETENTION_DAYS=0` a desativa.

`REPORT_TIMEZONE=America/Cuiaba` define o dia local dos relatorios. Datas sao
armazenadas com fuso; filtros de API exigem fuso e sao convertidos para UTC.
`GET /eventos` agora aceita `placa`, `inicio`, `fim`, `limit` e `offset`.
`GET /eventos/acessos` pagina os pares completos e aceita `placa`, `entrada_inicio`,
`entrada_fim`, `saida_inicio`, `saida_fim`, `limit` e `offset`. A tela usa essa rota,
sem baixar todo o historico. `/relatorios/acessos-diarios` tambem aceita `limit`/`offset`.

O frontend renova tokens ao receber 401 e repete a requisicao uma vez. Logout
revoga a sessao compartilhada por access e refresh, inclusive tokens renovados.
Depois desta atualizacao, tokens antigos sem identificador de sessao exigem novo login.
A sessao dura ate `REFRESH_TOKEN_DAYS` a partir do login; refresh nao prolonga esse prazo.

Os scripts usam `CLIENTE_SECRET` (aceitam `RASPBERRY_SECRET` como compatibilidade)
com o cabecalho `X-Cliente-Secret`. A camera envia `capturado_em` ao capturar o frame.
Para arquivos historicos, informe `CAPTURADO_EM` apenas se souber o horario real;
sem ele, o servidor identifica o horario como recebimento.

Verificacao: `.venv/bin/python -m unittest discover -s tests -v` e `npm test` no frontend.
Para testar o fluxo em PostgreSQL, defina `TEST_POSTGRES_URL`; a suite cria e remove
schemas aleatorios exclusivos, sem alterar as tabelas publicas.

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

## Frontend

O frontend fica em `frontend/` e usa React com Vite.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Por padrao ele consome a API em `http://localhost:8000`.

Para servir o frontend diretamente no Nginx existente no servidor, veja
[Frontend no Nginx do servidor](docs/frontend-docker.md).

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

Logout encerra a sessao informada; logins independentes em outros dispositivos
continuam validos. Desativar o usuario impede acessos e renovacoes de todas as suas sessoes.
