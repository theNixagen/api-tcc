from pathlib import Path
from typing import Any

import requests

SERVER_URL = "http://localhost:8000/alpr"

# Diretório contendo as imagens
IMAGE_DIR = Path("./imagens")

# Extensões aceitas
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def enviar_imagem(image_path: Path) -> None:
    print(f"\nEnviando: {image_path.name}")

    try:
        with open(image_path, "rb") as image:
            response = requests.post(
                SERVER_URL,
                files={"imagem": (image_path.name, image, "image/jpeg")},
                timeout=30,
            )

        response.raise_for_status()

        resultado: Any = response.json()

        print("Resposta:")
        print(resultado)

    except requests.RequestException as error:
        print(f"Erro ao enviar {image_path.name}: {error}")


def main() -> None:
    if not IMAGE_DIR.exists():
        print(f"Diretório não encontrado: {IMAGE_DIR}")
        return

    imagens = [
        arquivo
        for arquivo in IMAGE_DIR.iterdir()
        if arquivo.is_file() and arquivo.suffix.lower() in EXTENSIONS
    ]

    if not imagens:
        print("Nenhuma imagem encontrada.")
        return

    print(f"{len(imagens)} imagens encontradas.")

    for image_path in imagens:
        enviar_imagem(image_path)

    print("\nFinalizado.")


if __name__ == "__main__":
    main()
