import test from "node:test";
import assert from "node:assert/strict";
import { resolveRoute } from "../src/navigation.js";

test("link direto identifica a pagina exclusiva e o ID da leitura", () => {
  assert.deepEqual(resolveRoute("#/leituras/42"), { aba: "leituras", leituraId: "42" });
  assert.deepEqual(resolveRoute("#/leituras/42/"), { aba: "leituras", leituraId: "42" });
});

test("rota de volta abre a listagem e endereco inicial continua em acessos", () => {
  assert.deepEqual(resolveRoute("#/leituras"), { aba: "leituras", leituraId: null });
  assert.deepEqual(resolveRoute(""), { aba: "acessos", leituraId: null });
  assert.deepEqual(resolveRoute("#/usuarios"), { aba: "usuarios", leituraId: null });
});

test("IDs invalidos nao abrem a pagina de detalhes", () => {
  for (const hash of ["#/leituras/abc", "#/leituras/0", "#/leituras/42/outra"])
    assert.equal(resolveRoute(hash).leituraId, null);
});
