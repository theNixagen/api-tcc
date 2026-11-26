import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { authHeaders, request, savedTokens, saveTokens } from "./api";
import Leituras, { LeituraDetalhe } from "./Leituras";
import { nomeLeitura } from "./nomesLeitura";
import { resolveRoute } from "./navigation";

function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalized));
  } catch {
    return null;
  }
}

function App() {
  const [tokens, setTokens] = useState(savedTokens);
  useEffect(() => {
    const atualizar = () => setTokens(savedTokens());
    window.addEventListener("alpr.tokens", atualizar);
    window.addEventListener("storage", atualizar);
    return () => {
      window.removeEventListener("alpr.tokens", atualizar);
      window.removeEventListener("storage", atualizar);
    };
  }, []);
  const usuario = useMemo(
    () => (tokens?.access_token ? decodeJwt(tokens.access_token) : null),
    [tokens],
  );

  async function logout() {
    try {
      const atuais = savedTokens();
      if (atuais?.refresh_token) await request("/auth/logout", {
        method: "POST", body: JSON.stringify({ refresh_token: atuais.refresh_token }),
      });
    } catch (error) {
      window.alert(`Nao foi possivel revogar a sessao no servidor: ${error.message}`);
    } finally {
      saveTokens(null);
    }
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
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const atualizar = () => setHash(window.location.hash);
    window.addEventListener("hashchange", atualizar);
    return () => window.removeEventListener("hashchange", atualizar);
  }, []);
  const { aba, leituraId } = resolveRoute(hash);
  function setAba(proxima) {
    window.location.hash = `/${proxima}`;
  }
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
            className={aba === "leituras" ? "active" : ""}
            onClick={() => setAba("leituras")}
          >Leituras</button>
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
                className={aba === "cameras" ? "active" : ""}
                onClick={() => setAba("cameras")}
              >
                Câmeras
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
        {aba === "leituras" && (leituraId
          ? <LeituraDetalhe key={leituraId} token={tokens.access_token} id={leituraId} />
          : <Leituras token={tokens.access_token} />)}
        {aba === "acessos" && <Acessos token={tokens.access_token} />}
        {aba === "usuarios" && isAdmin && <Usuarios token={tokens.access_token} />}
        {aba === "cameras" && isAdmin && <Cameras token={tokens.access_token} />}
        {!["leituras", "acessos", "usuarios", "cameras"].includes(aba) && <p>Pagina nao encontrada.</p>}
      </section>
    </main>
  );
}

function Usuarios({ token }) {
  const [form, setForm] = useState({
    username: "",
    senha: "",
    papel: "operador",
  });
  const [usuarios, setUsuarios] = useState([]);
  const [editando, setEditando] = useState(null);
  const [mensagem, setMensagem] = useState("");

  async function carregar() {
    try {
      setUsuarios(
        await request("/usuarios", { headers: authHeaders(token) }),
      );
    } catch (error) {
      setMensagem(error.message);
    }
  }

  useEffect(() => {
    carregar();
  }, [token]);

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
      await carregar();
    } catch (error) {
      setMensagem(error.message);
    }
  }

  async function salvar(event) {
    event.preventDefault();
    setMensagem("");
    try {
      await request(`/usuarios/${editando.id}`, {
        method: "PUT",
        headers: authHeaders(token),
        body: JSON.stringify({
          ...editando,
          senha: editando.senha || null,
        }),
      });
      setMensagem(`Usuario ${editando.username} atualizado.`);
      setEditando(null);
      await carregar();
    } catch (error) {
      setMensagem(error.message);
    }
  }

  async function excluir(usuario) {
    if (!confirm(`Excluir o usuario ${usuario.username}?`)) return;
    setMensagem("");
    try {
      await request(`/usuarios/${usuario.id}`, {
        method: "DELETE",
        headers: authHeaders(token),
      });
      setMensagem(`Usuario ${usuario.username} excluido.`);
      await carregar();
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
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Papel</th>
              <th>Status</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.length ? (
              usuarios.map((usuario) => (
                <tr key={usuario.id}>
                  <td>{usuario.username}</td>
                  <td>{usuario.papel}</td>
                  <td>{usuario.ativo ? "Ativo" : "Inativo"}</td>
                  <td className="actions">
                    <button
                      type="button"
                      className="secondary small"
                      onClick={() => setEditando({ ...usuario, senha: "" })}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="danger small"
                      onClick={() => excluir(usuario)}
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4">Nenhum usuario encontrado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {editando && (
        <form className="edit-panel form-grid" onSubmit={salvar}>
          <label>
            Usuario
            <input
              value={editando.username}
              onChange={(event) =>
                setEditando({ ...editando, username: event.target.value })
              }
              required
            />
          </label>
          <label>
            Nova senha
            <input
              type="password"
              value={editando.senha}
              onChange={(event) =>
                setEditando({ ...editando, senha: event.target.value })
              }
              placeholder="Manter a atual"
            />
          </label>
          <label>
            Papel
            <select
              value={editando.papel}
              onChange={(event) =>
                setEditando({ ...editando, papel: event.target.value })
              }
            >
              <option value="operador">operador</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={editando.ativo}
              onChange={(event) =>
                setEditando({ ...editando, ativo: event.target.checked })
              }
            />
            Ativo
          </label>
          <button>Salvar</button>
          <button
            type="button"
            className="secondary"
            onClick={() => setEditando(null)}
          >
            Cancelar
          </button>
        </form>
      )}
    </section>
  );
}

function DirecaoCamera({ valor, onChange, obrigatoria = false }) {
  return (
    <label>
      Direção
      <select value={valor || ""} onChange={(event) => onChange(event.target.value)} required={obrigatoria}>
        <option value="" disabled>Selecione a direção</option>
        <option value="entrada">Entrada</option>
        <option value="saida">Saída</option>
      </select>
    </label>
  );
}

function Cameras({ token }) {
  const [form, setForm] = useState({ nome: "", chave_hash: "", direcao: "" });
  const [cameras, setCameras] = useState([]);
  const [editando, setEditando] = useState(null);
  const [secret, setSecret] = useState("");
  const [mensagem, setMensagem] = useState("");

  async function carregar() {
    try {
      setCameras(
        await request("/cameras", { headers: authHeaders(token) }),
      );
    } catch (error) {
      setMensagem(error.message);
    }
  }

  useEffect(() => {
    carregar();
  }, [token]);

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
      const camera = await request("/cameras", {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify(form),
      });
      setMensagem(`Câmera ${camera.nome} cadastrada.`);
      setForm({ nome: "", chave_hash: "", direcao: "" });
      setSecret("");
      await carregar();
    } catch (error) {
      setMensagem(error.message);
    }
  }

  async function salvar(event) {
    event.preventDefault();
    setMensagem("");
    try {
      await request(`/cameras/${editando.id}`, {
        method: "PUT",
        headers: authHeaders(token),
        body: JSON.stringify(editando),
      });
      setMensagem(`Câmera ${editando.nome} atualizada.`);
      setEditando(null);
      await carregar();
    } catch (error) {
      setMensagem(error.message);
    }
  }

  async function excluir(camera) {
    if (!confirm(`Excluir a câmera ${camera.nome}?`)) return;
    setMensagem("");
    try {
      await request(`/cameras/${camera.id}`, {
        method: "DELETE",
        headers: authHeaders(token),
      });
      setMensagem(`Câmera ${camera.nome} excluída.`);
      await carregar();
    } catch (error) {
      setMensagem(error.message);
    }
  }

  return (
    <section>
      <Header title="Câmeras" subtitle="A direção da câmera define se a leitura registra uma entrada ou uma saída." />
      <form className="form-grid" onSubmit={submit}>
        <label>
          Nome
          <input
            value={form.nome}
            onChange={(event) => setForm({ ...form, nome: event.target.value })}
            placeholder="Câmera do portão 1"
            required
          />
        </label>
        <DirecaoCamera valor={form.direcao} onChange={(direcao) => setForm({ ...form, direcao })} obrigatoria />
        <label className="wide">
          Hash da chave da câmera
          <input
            value={form.chave_hash}
            onChange={(event) =>
              setForm({ ...form, chave_hash: event.target.value })
            }
            required
          />
        </label>
        <button type="button" className="secondary" onClick={gerarSecret}>
          Gerar chave
        </button>
        <button>Cadastrar câmera</button>
      </form>
      {secret && (
        <p className="notice">
          Chave da câmera: <code>{secret}</code>
        </p>
      )}
      {mensagem && <p className="notice">{mensagem}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Câmera</th>
              <th>Direção</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {cameras.length ? (
              cameras.map((camera) => (
                <tr key={camera.id}>
                  <td>{camera.nome}</td>
                  <td>{camera.direcao ? nomeLeitura(camera.direcao) : "Não configurada"}</td>
                  <td>{camera.ativo ? "Ativa" : "Inativa"}</td>
                  <td className="actions">
                    <button
                      type="button"
                      className="secondary small"
                      onClick={() => setEditando({ ...camera })}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="danger small"
                      onClick={() => excluir(camera)}
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4">Nenhuma câmera cadastrada.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {editando && (
        <form className="edit-panel form-grid" onSubmit={salvar}>
          <label>
            Nome
            <input
              value={editando.nome}
              onChange={(event) =>
                setEditando({ ...editando, nome: event.target.value })
              }
              required
            />
          </label>
          <DirecaoCamera valor={editando.direcao} onChange={(direcao) => setEditando({ ...editando, direcao })} />
          <label className="checkbox">
            <input
              type="checkbox"
              checked={editando.ativo}
              onChange={(event) =>
                setEditando({ ...editando, ativo: event.target.checked })
              }
            />
            Ativa
          </label>
          <button>Salvar</button>
          <button
            type="button"
            className="secondary"
            onClick={() => setEditando(null)}
          >
            Cancelar
          </button>
        </form>
      )}
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
  const [pagina, setPagina] = useState({ itens: [], total: 0 });
  const [offset, setOffset] = useState(0);
  const [erro, setErro] = useState("");

  async function carregar(event, proximoOffset = 0, valores = filtros) {
    event?.preventDefault();
    setErro("");

    try {
      const params = new URLSearchParams({ limit: 50, offset: proximoOffset });
      if (valores.placa) params.set("placa", valores.placa);
      for (const [campo, parametro] of [
        ["entradaInicio", "entrada_inicio"], ["entradaFim", "entrada_fim"],
        ["saidaInicio", "saida_inicio"], ["saidaFim", "saida_fim"],
      ]) {
        if (valores[campo]) params.set(parametro, new Date(valores[campo]).toISOString());
      }
      setPagina(
        await request(`/eventos/acessos?${params}`, {
          headers: authHeaders(token),
        }),
      );
      setOffset(proximoOffset);
    } catch (error) {
      setErro(error.message);
    }
  }

  useEffect(() => {
    carregar();
  }, [token]);

  const acessos = pagina.itens;

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
          onClick={() => {
            const vazios = {
              placa: "",
              entradaInicio: "",
              entradaFim: "",
              saidaInicio: "",
              saidaFim: "",
            };
            setFiltros(vazios);
            carregar(null, 0, vazios);
          }}
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
              <th>Saída</th>
            </tr>
          </thead>
          <tbody>
            {acessos?.length ? (
              acessos.map((acesso) => (
                <tr key={acesso.id}>
                  <td>{acesso.placa}</td>
                  <td>{formatDate(acesso.data_hora_entrada)}</td>
                  <td>{formatDate(acesso.data_hora_saida) || "Pendente"}</td>
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
      <div className="pagination">
        <button disabled={offset === 0} onClick={() => carregar(null, Math.max(0, offset - 50))}>Anterior</button>
        <span>{pagina.total ? offset + 1 : 0}–{Math.min(offset + 50, pagina.total)} de {pagina.total}</span>
        <button disabled={offset + 50 >= pagina.total} onClick={() => carregar(null, offset + 50)}>Proxima</button>
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

createRoot(document.getElementById("root")).render(<App />);
