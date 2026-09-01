from app.services.raspberry_service import gerar_raspberry_secret, hash_raspberry_secret


def main() -> None:
    secret = gerar_raspberry_secret()
    print(f"secret={secret}")
    print(f"chave_hash={hash_raspberry_secret(secret)}")


if __name__ == "__main__":
    main()
