import unittest
from datetime import datetime
from types import SimpleNamespace

from app.services.evento_service import agrupar_eventos_por_veiculo, proximo_tipo_evento


class ProximoTipoEventoTest(unittest.TestCase):
    def test_primeiro_evento_e_entrada(self) -> None:
        self.assertEqual(proximo_tipo_evento(None), "entrada")

    def test_entrada_aberta_vira_saida(self) -> None:
        self.assertEqual(proximo_tipo_evento("entrada"), "saida")

    def test_ultimo_par_fechado_vira_nova_entrada(self) -> None:
        self.assertEqual(proximo_tipo_evento("saida"), "entrada")


class AgruparEventosPorVeiculoTest(unittest.TestCase):
    def test_agrupa_eventos_por_placa(self) -> None:
        agora = datetime(2026, 8, 31, 10, 0)
        eventos = [
            SimpleNamespace(id=1, placa="ABC1234", tipo_evento="entrada", data_hora=agora),
            SimpleNamespace(id=2, placa="ABC1234", tipo_evento="saida", data_hora=agora),
            SimpleNamespace(id=3, placa="XYZ9876", tipo_evento="entrada", data_hora=agora),
        ]

        self.assertEqual(
            agrupar_eventos_por_veiculo(eventos),
            [
                {
                    "placa": "ABC1234",
                    "eventos": [
                        {"id": 1, "tipo_evento": "entrada", "data_hora": agora},
                        {"id": 2, "tipo_evento": "saida", "data_hora": agora},
                    ],
                },
                {
                    "placa": "XYZ9876",
                    "eventos": [
                        {"id": 3, "tipo_evento": "entrada", "data_hora": agora},
                    ],
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
