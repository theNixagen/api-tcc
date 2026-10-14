import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalized));
  } catch {
    return null;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(data?.detail || "Erro na requisicao");
  }

  return data;
}

function App() {
  const [tokens, setTokens] = useState(() => {
    const saved = localStorage.getItem("alpr.tokens");
    return saved ? JSON.parse(saved) : null;
  });
  const usuario = useMemo(
    () => (tokens?.access_token ? decodeJwt(tokens.access_token) : null),
    [tokens],
  );

  function saveTokens(nextTokens) {
    setTokens(nextTokens);
    localStorage.setItem("alpr.tokens", JSON.stringify(nextTokens));
  }

  function logout() {
    setTokens(null);
    localStorage.removeItem("alpr.tokens");
  }

  if (!tokens || !usuario) {
    return <Login onLogin={saveTokens} />;
  }

  return <Dashboard tokens={tokens} usuario={usuario} onLogout={logout} />;
}

function Login({ onLogin }) {
  const [form, setForm] = useState({ username: "admin", senha: "admin123" });
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      onLogin(
        await request("/auth/login", {
          method: "POST",
          body: JSON.stringify(form),
        }),
      );
    } catch (error) {
      setErro(error.message);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="login-screen">
      <form className="login-panel" onSubmit={submit}>
        <div>
          <p className="eyebrow">ALPR</p>
          <h1>Acesso ao sistema</h1>
        </div>
        <label>
          Usuario
          <input
            value={form.username}
            onChange={(event) =>
              setForm({ ...form, username: event.target.value })
            }
            autoComplete="username"
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={form.senha}
            onChange={(event) => setForm({ ...form, senha: event.target.value })}
            autoComplete="current-password"
          />
        </label>
        {erro && <p className="error">{erro}</p>}
        <button disabled={carregando}>
          {carregando ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}

function Dashboard({ tokens, usuario, onLogout }) {
  const [aba, setAba] = useState("acessos");
  const isAdmin = usuario.papel === "admin";

  return (
    <main className="shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">ALPR</p>
          <h1>Gestao</h1>
        </div>
        <nav>
          <button
            className={aba === "acessos" ? "active" : ""}
            onClick={() => setAba("acessos")}
          >
            Acessos
          </button>
          {isAdmin && (
            <>
              <button
                className={aba === "usuarios" ? "active" : ""}
                onClick={() => setAba("usuarios")}
              >
                Usuarios
              </button>
              <button
                className={aba === "clientes" ? "active" : ""}
                onClick={() => setAba("clientes")}
              >
                Clientes
              </button>
            </>
          )}
        </nav>
        <div className="account">
          <strong>{usuario.username}</strong>
          <span>{usuario.papel}</span>
          <button onClick={onLogout}>Sair</button>
        </div>
      </aside>

      <section className="content">
        {aba === "acessos" && <Acessos token={tokens.access_token} />}
        {aba === "usuarios" && isAdmin && <Usuarios token={tokens.access_token} />}
        {aba === "clientes" && isAdmin && <Clientes token={tokens.access_token} />}
      </section>
    </main>
  );
}

function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}

function Usuarios({ token }) {
  const [form, setForm] = useState({
    username: "",
    senha: "",
    papel: "operador",
  });
  const [mensagem, setMensagem] = useState("");

  async function submit(event) {
    event.preventDefault();
    setMensagem("");
    try {
      const usuario = await request("/usuarios", {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify(form),
      });
      setMensagem(`Usuario ${usuario.username} criado.`);
      setForm({ username: "", senha: "", papel: "operador" });
    } catch (error) {
      setMensagem(error.message);
    }
  }

  return (
    <section>
      <Header title="Usuarios" subtitle="Criacao de administradores e operadores." />
      <form className="form-grid" onSubmit={submit}>
        <label>
          Usuario
          <input
            value={form.username}
            onChange={(event) =>
              setForm({ ...form, username: event.target.value })
            }
            required
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={form.senha}
            onChange={(event) => setForm({ ...form, senha: event.target.value })}
            required
          />
        </label>
        <label>
          Papel
          <select
            value={form.papel}
            onChange={(event) => setForm({ ...form, papel: event.target.value })}
          >
            <option value="operador">operador</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <button>Criar usuario</button>
      </form>
      {mensagem && <p className="notice">{mensagem}</p>}
    </section>
  );
}

function Clientes({ token }) {
  const [form, setForm] = useState({ nome: "", chave_hash: "" });
  const [secret, setSecret] = useState("");
  const [mensagem, setMensagem] = useState("");

  async function gerarSecret() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    const raw = btoa(String.fromCharCode(...bytes))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
    const hash = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(raw),
    );
    const chave_hash = [...new Uint8Array(hash)]
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
    setSecret(raw);
    setForm((current) => ({ ...current, chave_hash }));
  }

  async function submit(event) {
    event.preventDefault();
    setMensagem("");
    try {
      const cliente = await request("/clientes", {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify(form),
      });
      setMensagem(`Cliente ${cliente.nome} cadastrado.`);
      setForm({ nome: "", chave_hash: "" });
    } catch (error) {
      setMensagem(error.message);
    }
  }

  return (
    <section>
      <Header title="Clientes" subtitle="Cadastro de clientes que enviam imagens." />
      <form className="form-grid" onSubmit={submit}>
        <label>
          Nome
          <input
            value={form.nome}
            onChange={(event) => setForm({ ...form, nome: event.target.value })}
            placeholder="cliente-portao-1"
            required
          />
        </label>
        <label className="wide">
          Hash do secret
          <input
            value={form.chave_hash}
            onChange={(event) =>
              setForm({ ...form, chave_hash: event.target.value })
            }
            required
          />
        </label>
        <button type="button" className="secondary" onClick={gerarSecret}>
          Gerar secret
        </button>
        <button>Cadastrar cliente</button>
      </form>
      {secret && (
        <p className="notice">
          Secret gerado: <code>{secret}</code>
        </p>
      )}
      {mensagem && <p className="notice">{mensagem}</p>}
    </section>
  );
}

function Acessos({ token }) {
  const [filtros, setFiltros] = useState({
    placa: "",
    entradaInicio: "",
    entradaFim: "",
    saidaInicio: "",
    saidaFim: "",
  });
  const [eventos, setEventos] = useState(null);
  const [erro, setErro] = useState("");

  async function carregar(event) {
    event?.preventDefault();
    setErro("");

    try {
      setEventos(
        await request("/eventos", {
          headers: authHeaders(token),
        }),
      );
    } catch (error) {
      setErro(error.message);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  const acessos = useMemo(
    () => filtrarAcessos(montarAcessos(eventos?.veiculos || []), filtros),
    [eventos, filtros],
  );

  return (
    <section>
      <Header title="Acessos" subtitle="Consulta baseada no historico de eventos." />
      <form className="filters" onSubmit={carregar}>
        <label>
          Placa
          <input
            value={filtros.placa}
            onChange={(event) =>
              setFiltros({ ...filtros, placa: event.target.value.toUpperCase() })
            }
            placeholder="ABC1234"
          />
        </label>
        <label>
          Entrada inicial
          <input
            type="datetime-local"
            value={filtros.entradaInicio}
            onChange={(event) =>
              setFiltros({ ...filtros, entradaInicio: event.target.value })
            }
          />
        </label>
        <label>
          Entrada final
          <input
            type="datetime-local"
            value={filtros.entradaFim}
            onChange={(event) =>
              setFiltros({ ...filtros, entradaFim: event.target.value })
            }
          />
        </label>
        <label>
          Saida inicial
          <input
            type="datetime-local"
            value={filtros.saidaInicio}
            onChange={(event) =>
              setFiltros({ ...filtros, saidaInicio: event.target.value })
            }
          />
        </label>
        <label>
          Saida final
          <input
            type="datetime-local"
            value={filtros.saidaFim}
            onChange={(event) =>
              setFiltros({ ...filtros, saidaFim: event.target.value })
            }
          />
        </label>
        <button>Filtrar</button>
        <button
          type="button"
          className="secondary"
          onClick={() =>
            setFiltros({
              placa: "",
              entradaInicio: "",
              entradaFim: "",
              saidaInicio: "",
              saidaFim: "",
            })
          }
        >
          Limpar
        </button>
      </form>
      {erro && <p className="error">{erro}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Placa</th>
              <th>Entrada</th>
              <th>Saida</th>
            </tr>
          </thead>
          <tbody>
            {acessos?.length ? (
              acessos.map((acesso, index) => (
                <tr key={`${acesso.placa}-${index}`}>
                  <td>{acesso.placa}</td>
                  <td>{formatDate(acesso.data_hora_entrada)}</td>
                  <td>{formatDate(acesso.data_hora_saida) || "Em aberto"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="3">Nenhum acesso encontrado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Header({ title, subtitle }) {
  return (
    <header className="page-header">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </header>
  );
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function montarAcessos(veiculos) {
  return veiculos.flatMap((veiculo) => {
    const acessos = [];
    let entrada = null;

    for (const evento of veiculo.eventos) {
      if (evento.tipo_evento === "entrada") {
        if (entrada) {
          acessos.push({
            placa: veiculo.placa,
            data_hora_entrada: entrada,
            data_hora_saida: null,
          });
        }
        entrada = evento.data_hora;
      }

      if (evento.tipo_evento === "saida" && entrada) {
        acessos.push({
          placa: veiculo.placa,
          data_hora_entrada: entrada,
          data_hora_saida: evento.data_hora,
        });
        entrada = null;
      }
    }

    if (entrada) {
      acessos.push({
        placa: veiculo.placa,
        data_hora_entrada: entrada,
        data_hora_saida: null,
      });
    }

    return acessos;
  });
}

function filtrarAcessos(acessos, filtros) {
  const entradaInicio = filtros.entradaInicio && new Date(filtros.entradaInicio);
  const entradaFim = filtros.entradaFim && new Date(filtros.entradaFim);
  const saidaInicio = filtros.saidaInicio && new Date(filtros.saidaInicio);
  const saidaFim = filtros.saidaFim && new Date(filtros.saidaFim);

  return acessos.filter((acesso) => {
    const entrada = new Date(acesso.data_hora_entrada);
    const saida = acesso.data_hora_saida && new Date(acesso.data_hora_saida);

    if (filtros.placa && !acesso.placa.includes(filtros.placa)) return false;
    if (entradaInicio && entrada < entradaInicio) return false;
    if (entradaFim && entrada > entradaFim) return false;
    if (saidaInicio && (!saida || saida < saidaInicio)) return false;
    if (saidaFim && (!saida || saida > saidaFim)) return false;
    return true;
  });
}

createRoot(document.getElementById("root")).render(<App />);
