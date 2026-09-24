from app.services.cliente_service import gerar_cliente_secret, hash_cliente_secret


def main() -> None:
    secret = gerar_cliente_secret()
    print(f"secret={secret}")
    print(f"chave_hash={hash_cliente_secret(secret)}")


if __name__ == "__main__":
    main()
