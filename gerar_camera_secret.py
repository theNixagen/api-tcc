from app.services.camera_service import gerar_camera_secret, hash_camera_secret


def main() -> None:
    secret = gerar_camera_secret()
    print(f"secret={secret}")
    print(f"chave_hash={hash_camera_secret(secret)}")


if __name__ == "__main__":
    main()
