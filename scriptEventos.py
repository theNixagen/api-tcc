import os
from pprint import pprint
from sys import argv
from typing import Any

import requests

SERVER_URL = "http://127.0.0.1:8000/eventos"


def main() -> None:
    url = argv[1] if len(argv) > 1 else SERVER_URL

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Erro ao buscar eventos em {url}: {error}")
        return

    data: Any = response.json()
    pprint(data)


if __name__ == "__main__":
    main()
