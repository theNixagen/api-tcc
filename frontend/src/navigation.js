export function resolveRoute(hash) {
  const caminho = hash.replace(/^#/, "") || "/acessos";
  const leitura = /^\/leituras\/([1-9]\d*)\/?$/.exec(caminho);
  if (leitura) return { aba: "leituras", leituraId: leitura[1] };
  return { aba: caminho.slice(1), leituraId: null };
}
