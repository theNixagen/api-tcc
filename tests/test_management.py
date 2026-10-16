import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api.deps import usuario_atual
from app.api.routes.usuarios import editar_usuario as editar_usuario_rota
from app.api.routes.usuarios import excluir_usuario
from app.schemas.usuario import UsuarioUpdateRequest
from app.services.auth_service import UsuarioAutenticado
from app.services.cliente_service import editar_cliente
from app.services.usuario_service import editar_usuario


class FakeSession:
    def __init__(self, registro=None) -> None:
        self.registro = registro
        self.commits = 0
        self.refreshes = 0

    def get(self, _model, _id):
        return self.registro

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass

    def refresh(self, _registro) -> None:
        self.refreshes += 1


class GestaoUsuariosTest(unittest.TestCase):
    @patch("app.services.usuario_service.hash_senha", return_value="novo-hash")
    def test_edita_usuario_e_troca_senha_quando_informada(self, _hash_senha) -> None:
        usuario = SimpleNamespace(
            username="antigo",
            papel="operador",
            ativo=True,
            senha_hash="hash-antigo",
        )
        db = FakeSession(usuario)

        resultado = editar_usuario(db, 1, "novo", "admin", False, "nova-senha")

        self.assertIs(resultado, usuario)
        self.assertEqual(
            (usuario.username, usuario.papel, usuario.ativo, usuario.senha_hash),
            ("novo", "admin", False, "novo-hash"),
        )
        self.assertEqual((db.commits, db.refreshes), (1, 1))

    def test_impede_excluir_o_proprio_usuario(self) -> None:
        with self.assertRaises(HTTPException) as erro:
            excluir_usuario(
                7,
                FakeSession(),
                UsuarioAutenticado(id=7, username="admin", papel="admin"),
            )

        self.assertEqual(erro.exception.status_code, 409)

    def test_impede_desativar_o_proprio_administrador(self) -> None:
        with self.assertRaises(HTTPException) as erro:
            editar_usuario_rota(
                7,
                UsuarioUpdateRequest(username="admin", papel="admin", ativo=False),
                FakeSession(),
                UsuarioAutenticado(id=7, username="admin", papel="admin"),
            )

        self.assertEqual(erro.exception.status_code, 409)

    @patch("app.api.deps.decodificar_jwt", return_value={})
    @patch("app.api.deps.validar_access_token")
    def test_token_de_usuario_excluido_deixa_de_ser_aceito(
        self, validar_token, _decodificar
    ) -> None:
        validar_token.return_value = UsuarioAutenticado(
            id=7, username="admin", papel="admin"
        )

        with self.assertRaises(HTTPException) as erro:
            usuario_atual(SimpleNamespace(credentials="token"), object(), FakeSession())

        self.assertEqual(erro.exception.status_code, 401)


class GestaoClientesTest(unittest.TestCase):
    def test_edita_nome_e_status_do_cliente(self) -> None:
        cliente = SimpleNamespace(nome="Portao 1", ativo=True)
        db = FakeSession(cliente)

        resultado = editar_cliente(db, 1, "Portao 2", False)

        self.assertIs(resultado, cliente)
        self.assertEqual((cliente.nome, cliente.ativo), ("Portao 2", False))
        self.assertEqual((db.commits, db.refreshes), (1, 1))


if __name__ == "__main__":
    unittest.main()
