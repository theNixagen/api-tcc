import unittest
from datetime import timedelta
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.deps import exigir_papeis, raspberry_atual
from app.services.auth_service import (
    criar_access_token,
    criar_jwt,
    criar_refresh_token,
    decodificar_jwt,
    hash_senha,
    revogar_token,
    validar_access_token,
    validar_refresh_token,
    verificar_senha,
)
from app.services.raspberry_service import gerar_raspberry_secret, hash_raspberry_secret


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.data[key] = value

    def exists(self, key: str) -> int:
        return 1 if key in self.data else 0

    def delete(self, key: str) -> None:
        self.data.pop(key, None)


class JwtTest(unittest.TestCase):
    def test_decodifica_token_valido(self) -> None:
        token = criar_jwt({"typ": "access", "sub": "1"}, timedelta(minutes=5))

        self.assertEqual(decodificar_jwt(token)["sub"], "1")

    def test_rejeita_token_adulterado(self) -> None:
        token = criar_jwt({"typ": "access", "sub": "1"}, timedelta(minutes=5))
        token = token[:-1] + ("a" if token[-1] != "a" else "b")

        with self.assertRaises(HTTPException):
            decodificar_jwt(token)

    def test_tokens_carregam_usuario_e_sao_validados_no_cache(self) -> None:
        cache = FakeRedis()
        usuario = SimpleNamespace(id=7, username="ana", papel="operador")

        access_token = criar_access_token(cache, usuario)
        refresh_token = criar_refresh_token(cache, usuario)
        access_payload = decodificar_jwt(access_token)
        refresh_payload = decodificar_jwt(refresh_token)

        self.assertEqual(access_payload["papel"], "operador")
        self.assertEqual(access_payload["username"], "ana")
        self.assertIn("token_id", access_payload)
        self.assertEqual(refresh_payload["papel"], "operador")
        self.assertIn("refresh_token_id", refresh_payload)
        self.assertEqual(validar_access_token(cache, access_payload).id, 7)
        self.assertEqual(
            validar_refresh_token(cache, refresh_payload),
            refresh_payload["refresh_token_id"],
        )

    def test_rejeita_token_revogado_no_cache(self) -> None:
        cache = FakeRedis()
        usuario = SimpleNamespace(id=7, username="ana", papel="operador")
        access_payload = decodificar_jwt(criar_access_token(cache, usuario))

        revogar_token(cache, "access", access_payload["token_id"])

        with self.assertRaises(HTTPException):
            validar_access_token(cache, access_payload)

    def test_rejeita_token_expirado(self) -> None:
        token = criar_jwt({"typ": "access", "sub": "1"}, -timedelta(seconds=1))

        with self.assertRaises(HTTPException):
            decodificar_jwt(token)


class SenhaTest(unittest.TestCase):
    def test_verifica_senha_com_pbkdf2(self) -> None:
        senha_hash = hash_senha("segredo")

        self.assertTrue(verificar_senha("segredo", senha_hash))
        self.assertFalse(verificar_senha("errada", senha_hash))


class PapelTest(unittest.TestCase):
    def test_permite_papel_autorizado(self) -> None:
        dependency = exigir_papeis("admin")

        usuario = SimpleNamespace(papel="admin")
        self.assertIs(dependency(usuario), usuario)

    def test_rejeita_papel_sem_permissao(self) -> None:
        dependency = exigir_papeis("admin")

        with self.assertRaises(HTTPException):
            dependency(SimpleNamespace(papel="operador"))


class RaspberrySecretTest(unittest.TestCase):
    def test_gera_secret_de_256_bits_e_hash_sha256(self) -> None:
        secret = gerar_raspberry_secret()
        chave_hash = hash_raspberry_secret(secret)

        self.assertGreaterEqual(len(secret), 43)
        self.assertEqual(len(chave_hash), 64)
        int(chave_hash, 16)

    def test_rejeita_raspberry_sem_chave(self) -> None:
        with self.assertRaises(HTTPException):
            raspberry_atual(None, SimpleNamespace())


if __name__ == "__main__":
    unittest.main()
