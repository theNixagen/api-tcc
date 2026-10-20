import test from "node:test";
import assert from "node:assert/strict";
import { apiFetch, request, saveTokens, savedTokens } from "../src/api.js";

test("renova uma unica vez para chamadas simultaneas e repete com access novo", async () => {
  const originalFetch = globalThis.fetch;
  const armazenamento = new Map();
  globalThis.localStorage = {
    getItem: (key) => armazenamento.get(key) ?? null,
    setItem: (key, value) => armazenamento.set(key, value),
    removeItem: (key) => armazenamento.delete(key),
  };
  globalThis.window = new EventTarget();
  saveTokens({ access_token: "antigo", refresh_token: "refresh-antigo" });
  let renovacoes = 0;
  let repeticoes = 0;
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/auth/refresh")) {
      renovacoes++;
      await new Promise((resolve) => setTimeout(resolve, 5));
      return Response.json({ access_token: "novo", refresh_token: "refresh-novo" });
    }
    if (new Headers(options.headers).get("Authorization") === "Bearer antigo") return new Response(null, { status: 401 });
    repeticoes++;
    return Response.json({ ok: true });
  };
  try {
    const resultados = await Promise.all([1, 2, 3].map(() => request("/leituras", { headers: { Authorization: "Bearer antigo" } })));
    assert.equal(renovacoes, 1);
    assert.equal(repeticoes, 3);
    assert.ok(resultados.every((item) => item.ok));
    assert.equal(savedTokens().refresh_token, "refresh-novo");
    globalThis.fetch = async () => new Response(null, { status: 401 });
    await assert.rejects(apiFetch("/leituras", { headers: { Authorization: "Bearer novo" } }), /Sessao expirada/);
    assert.equal(savedTokens(), null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
