const API_URL = import.meta.env?.VITE_API_URL || "http://localhost:8000";
let renovacao = null;

export function savedTokens() {
  try {
    return JSON.parse(localStorage.getItem("alpr.tokens"));
  } catch {
    return null;
  }
}

export function saveTokens(tokens) {
  if (tokens) localStorage.setItem("alpr.tokens", JSON.stringify(tokens));
  else localStorage.removeItem("alpr.tokens");
  window.dispatchEvent(new Event("alpr.tokens"));
}

async function renovar() {
  const anteriores = savedTokens();
  if (!anteriores?.refresh_token) throw new Error("Sessao encerrada");
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: anteriores.refresh_token }),
  });
  if (!response.ok) {
    // Uma falha de rede/servidor nao apaga a sessao; 401 significa sessao invalida.
    if (response.status === 401 && savedTokens()?.refresh_token === anteriores.refresh_token) saveTokens(null);
    throw new Error(response.status === 401 ? "Sessao expirada. Entre novamente." : "Nao foi possivel renovar a sessao");
  }
  const tokens = await response.json();
  if (savedTokens()?.refresh_token !== anteriores.refresh_token) throw new Error("Sessao alterada durante a renovacao");
  saveTokens(tokens);
  return tokens;
}

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers);
  const autenticada = headers.has("Authorization");
  if (autenticada && savedTokens()?.access_token) headers.set("Authorization", `Bearer ${savedTokens().access_token}`);
  const usado = headers.get("Authorization");
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (response.status !== 401 || !autenticada) return response;
  let tokens = savedTokens();
  if (!tokens) return response;
  if (`Bearer ${tokens.access_token}` === usado) {
    if (!renovacao) renovacao = renovar().finally(() => { renovacao = null; });
    tokens = await renovacao;
  }
  headers.set("Authorization", `Bearer ${tokens.access_token}`);
  return fetch(`${API_URL}${path}`, { ...options, headers });
}

export async function request(path, options = {}) {
  const response = await apiFetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : detail || "Erro na requisicao");
  }
  return data;
}

export function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}
