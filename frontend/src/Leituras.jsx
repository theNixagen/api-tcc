import React, { useEffect, useRef, useState } from "react";
import { apiFetch, authHeaders, request } from "./api";
import { nomeLeitura } from "./nomesLeitura";

const data = (valor) => valor ? new Date(valor).toLocaleString("pt-BR") : "—";
const confianca = (valor) => valor == null ? "indisponivel" : `${(valor * 100).toFixed(1)}%`;
const mensagensSemDeteccao = {
  pendente: {
    titulo: "Aguardando processamento",
    descricao: "A imagem está na fila. As detecções aparecerão aqui assim que a leitura for concluída.",
  },
  processando: {
    titulo: "Analisando a imagem",
    descricao: "Estamos procurando placas nesta foto. O resultado será atualizado automaticamente.",
  },
  concluida: {
    titulo: "Nenhuma placa detectada",
    descricao: "O detector não encontrou uma placa. Confira a foto para informar a placa manualmente ou rejeitar a leitura com uma justificativa.",
  },
  aceita: {
    titulo: "Leitura aceita na revisão",
    descricao: "A placa foi informada manualmente e o evento foi registrado. Confira os dados no histórico de revisões abaixo.",
  },
  rejeitada: {
    titulo: "Leitura rejeitada na revisão",
    descricao: "A imagem foi conferida e rejeitada. Nenhum evento foi criado nesta revisão; a justificativa está no histórico abaixo.",
  },
  erro: {
    titulo: "Não foi possível concluir a leitura",
    descricao: "Nenhuma detecção está disponível. Consulte o erro informado acima para avaliar uma nova tentativa de processamento.",
  },
};

export default function Leituras({ token }) {
  const [filtros, setFiltros] = useState({ status: "", resultado: "", placa: "" });
  const [offset, setOffset] = useState(0);
  const [lista, setLista] = useState({ itens: [], total: 0 });
  const [fila, setFila] = useState(null);
  const [erro, setErro] = useState("");
  const versaoLista = useRef(0);

  async function carregar() {
    const versao = ++versaoLista.current;
    const params = new URLSearchParams({ limit: 20, offset });
    Object.entries(filtros).forEach(([campo, valor]) => { if (valor) params.set(campo, valor); });
    try {
      const [leituras, resumo] = await Promise.all([
        request(`/leituras?${params}`, { headers: authHeaders(token) }),
        request("/leituras/fila", { headers: authHeaders(token) }),
      ]);
      if (versao !== versaoLista.current) return;
      setLista(leituras);
      setFila(resumo);
      setErro("");
    } catch (error) { if (versao === versaoLista.current) setErro(error.message); }
  }

  useEffect(() => {
    carregar();
    const timer = setInterval(carregar, 5000);
    return () => { clearInterval(timer); versaoLista.current++; };
  }, [token, filtros, offset]);

  function filtrar(campo, valor) {
    setOffset(0);
    setFiltros((anteriores) => ({ ...anteriores, [campo]: valor }));
  }

  return <section>
    <header className="page-header"><h2>Leituras</h2><p>Fila, fotos e revisao dos reconhecimentos. Atualizacao a cada 5 segundos.</p></header>
    {fila && <p className="notice" role="status">
      Aguardando: {fila.pendentes} · Processando: {fila.processando} · Concluidas: {fila.concluidas} · Erros: {fila.erros} · Para revisao: {fila.revisao}
    </p>}
    <div className="form-grid">
      <label>Status<select value={filtros.status} onChange={(e) => filtrar("status", e.target.value)}>
        <option value="">Todos</option>
        {["pendente", "processando", "concluida", "erro"].map((item) => <option key={item} value={item}>{nomeLeitura(item)}</option>)}
      </select></label>
      <label>Resultado<select value={filtros.resultado} onChange={(e) => filtrar("resultado", e.target.value)}>
        <option value="">Todos</option>
        {["aceita", "revisao", "sem_placa", "rejeitada"].map((item) => <option key={item} value={item}>{nomeLeitura(item)}</option>)}
      </select></label>
      <label>Placa<input value={filtros.placa} maxLength={10} onChange={(e) => filtrar("placa", e.target.value.toUpperCase())} /></label>
      <button type="button" onClick={carregar}>Atualizar</button>
    </div>
    {erro && <p className="error" role="alert">{erro}</p>}
    <div className="table-wrap"><table>
      <thead><tr><th>ID / arquivo</th><th>Captura</th><th>Status</th><th>Resultado</th><th>Tentativas</th><th>Acoes</th></tr></thead>
      <tbody>{lista.itens.map((item) => <tr key={item.id}>
        <td>{item.id} · {item.nome_arquivo}</td><td>{data(item.capturado_em)}</td>
        <td>{nomeLeitura(item.status)}</td><td>{nomeLeitura(item.resultado)}</td><td>{item.tentativas}</td>
        <td><a className="button-link" href={`#/leituras/${item.id}`}>Ver leitura</a></td>
      </tr>)}{!lista.itens.length && <tr><td colSpan="6">Nenhuma leitura encontrada.</td></tr>}</tbody>
    </table></div>
    <div className="pagination">
      <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Anterior</button>
      <span>{lista.total ? offset + 1 : 0}–{Math.min(offset + 20, lista.total)} de {lista.total}</span>
      <button disabled={offset + 20 >= lista.total} onClick={() => setOffset(offset + 20)}>Proxima</button>
    </div>
  </section>;
}

export function LeituraDetalhe({ token, id }) {
  const [detalhe, setDetalhe] = useState(null);
  const [auditoria, setAuditoria] = useState([]);
  const [erro, setErro] = useState("");
  const versaoDetalhe = useRef(0);
  const mensagemSemDeteccao = mensagensSemDeteccao[detalhe?.resultado] || mensagensSemDeteccao[detalhe?.status];

  async function carregar() {
    const versao = ++versaoDetalhe.current;
    try {
      const [leitura, revisoes] = await Promise.all([
        request(`/leituras/${id}`, { headers: authHeaders(token) }),
        request(`/leituras/${id}/revisoes`, { headers: authHeaders(token) }),
      ]);
      if (versao !== versaoDetalhe.current) return;
      setDetalhe(leitura);
      setAuditoria(revisoes);
      setErro("");
    } catch (error) { if (versao === versaoDetalhe.current) setErro(error.message); }
  }

  useEffect(() => {
    carregar();
    const timer = setInterval(carregar, 5000);
    return () => { clearInterval(timer); versaoDetalhe.current++; };
  }, [id, token]);

  async function reprocessar() {
    try {
      await request(`/leituras/${id}/reprocessar`, { method: "POST", headers: authHeaders(token) });
      await carregar();
    } catch (error) { setErro(error.message); }
  }

  return <section>
    <header className="page-header">
      <h2>Leitura {id}</h2>
      <p>Foto, resultado e revisoes desta leitura. Atualizacao a cada 5 segundos.</p>
    </header>
    <div className="pagination">
      <a className="button-link secondary" href="#/leituras">Voltar para leituras</a>
      <button type="button" onClick={carregar}>Atualizar</button>
    </div>
    {erro && <p className="error" role="alert">{erro}</p>}
    {!detalhe && !erro && <p role="status">Carregando leitura...</p>}
    {detalhe && <article className="edit-panel">
      <h3>Leitura {detalhe.id} · {detalhe.nome_arquivo}</h3>
      <dl className="leitura-campos">
        <div>
          <dt>Status do processamento</dt>
          <dd><span className={`leitura-status leitura-status--${detalhe.status}`}>{nomeLeitura(detalhe.status)}</span></dd>
        </div>
        <div>
          <dt>Resultado da leitura</dt>
          <dd>{nomeLeitura(detalhe.resultado)}</dd>
        </div>
        <div>
          <dt>Tentativas de processamento</dt>
          <dd>{detalhe.tentativas} de {detalhe.tentativas_limite}</dd>
        </div>
        <div>
          <dt>Data e hora da captura</dt>
          <dd>
            {data(detalhe.capturado_em)}
            {!detalhe.captura_informada && <small>Captura não informada. Utilizado o horário de recebimento.</small>}
          </dd>
        </div>
        <div>
          <dt>Recebida em</dt>
          <dd>{data(detalhe.criado_em)}</dd>
        </div>
        <div>
          <dt>Início do processamento</dt>
          <dd>{detalhe.iniciado_em ? data(detalhe.iniciado_em) : "Não informado"}</dd>
        </div>
        <div>
          <dt>Fim do processamento</dt>
          <dd>{detalhe.finalizado_em ? data(detalhe.finalizado_em) : "Ainda não finalizado"}</dd>
        </div>
      </dl>
      {detalhe.erro && <p className="error">{detalhe.erro}</p>}
      {detalhe.imagem_disponivel ? <Foto key={detalhe.id} id={detalhe.id} token={token} /> : <p>Imagem removida pela retencao.</p>}
      {detalhe.status === "erro" && detalhe.imagem_disponivel && <button onClick={reprocessar}>Reprocessar erro</button>}
      <div className="deteccoes-cabecalho">
        <h3>Detecções de placas</h3>
        <span>Total: {detalhe.detections.length}</span>
      </div>
      {!detalhe.detections.length && <div className="leitura-vazia" role="status">
        <span className="leitura-vazia-icone" aria-hidden="true">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <rect x="3" y="6" width="18" height="12" rx="3" />
            <path d="M7 10h10M7 14h4m3 0h3" />
          </svg>
        </span>
        <h4>{mensagemSemDeteccao?.titulo || "Nenhuma detecção disponível"}</h4>
        <p>{mensagemSemDeteccao?.descricao || "Os resultados desta imagem serão exibidos aqui."}</p>
      </div>}
      {!detalhe.detections.length && detalhe.status === "concluida" && ["revisao", "sem_placa"].includes(detalhe.resultado) && <section className="deteccao-revisao">
        <h5>Revisão da imagem original</h5>
        <p>Se houver uma placa na foto, informe o texto e o tipo de passagem. Caso contrário, rejeite a leitura.</p>
        {!detalhe.imagem_disponivel && <p className="error">A imagem original não está mais disponível. Você pode rejeitar a leitura com uma justificativa.</p>}
        <Revisao leituraId={detalhe.id} podeAceitar={detalhe.imagem_disponivel} token={token} onSave={carregar} />
      </section>}
      {detalhe.detections.map((item) => <div className="edit-panel deteccao-card" key={item.id}>
        <header className="deteccao-cabecalho">
          <div>
            <span className="deteccao-rotulo">Placa reconhecida</span>
            <h4>{item.placa || "Não reconhecida"}</h4>
          </div>
          <span className={`leitura-status leitura-resultado--${item.resultado}`}>{nomeLeitura(item.resultado)}</span>
        </header>
        <dl className="leitura-campos">
          <div><dt>Confiança da detecção</dt><dd>{confianca(item.confianca_deteccao)}</dd></div>
          <div><dt>Confiança da leitura do texto</dt><dd>{confianca(item.confianca_ocr)}</dd></div>
          <div><dt>Evento vinculado</dt><dd>{item.evento_id ? `#${item.evento_id}` : "Nenhum evento criado"}</dd></div>
          <div><dt>Texto original reconhecido</dt><dd>{item.texto_ocr || "Nenhum texto reconhecido"}</dd></div>
        </dl>
        <details className="deteccao-tecnica">
          <summary>Coordenadas da placa na imagem</summary>
          <p>Início: ({item.bbox[0]}, {item.bbox[1]}) · Fim: ({item.bbox[2]}, {item.bbox[3]})</p>
        </details>
        {item.motivo && <p className="deteccao-motivo"><strong>Observação</strong>{item.motivo}</p>}
        {item.resultado === "revisao" && <section className="deteccao-revisao">
          <h5>Revisão manual</h5>
          <p>Confira a imagem antes de aceitar ou rejeitar esta leitura.</p>
          <Revisao item={item} token={token} onSave={carregar} />
        </section>}
      </div>)}
      {auditoria.length > 0 && <div><h4>Historico de revisoes</h4><ul>{auditoria.map((item) => <li key={item.id}>
        {data(item.criado_em)} · {item.username} · {nomeLeitura(item.acao)} · {item.placa_anterior || "Sem texto"} → {item.placa_corrigida || "Rejeitada"} · {item.motivo}{item.evento_id && ` · Evento #${item.evento_id}`}
      </li>)}</ul></div>}
    </article>}
  </section>;
}

function Foto({ id, token }) {
  const [url, setUrl] = useState("");
  const [erro, setErro] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    (async () => {
      try {
        const response = await apiFetch(`/leituras/${id}/imagem`, { headers: authHeaders(token), signal: controller.signal });
        if (!response.ok) throw new Error("Nao foi possivel carregar a foto");
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch (error) { if (!controller.signal.aborted) setErro(error.message); }
    })();
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [id, token]);
  return erro ? <p className="error">{erro}</p> : url ? <img className="leitura-foto" src={url} alt={`Foto original da leitura ${id}`} /> : <p>Carregando foto...</p>;
}

function Revisao({ item, leituraId, podeAceitar = true, token, onSave }) {
  const [form, setForm] = useState({ placa: item?.placa || "", tipo_evento: "entrada", motivo: "" });
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  async function salvar(event) {
    event.preventDefault();
    const acao = event.nativeEvent.submitter?.value || "aceitar";
    setSalvando(true);
    try {
      const rota = leituraId ? `/leituras/${leituraId}/revisar` : `/leituras/deteccoes/${item.id}/revisar`;
      await request(rota, {
        method: "POST", headers: authHeaders(token), body: JSON.stringify({ ...form, acao }),
      });
      await onSave();
    } catch (error) { setErro(error.message); }
    finally { setSalvando(false); }
  }
  return <form onSubmit={salvar}>
    <div className="form-grid">
      <label>Placa corrigida<input value={form.placa} maxLength={10} onChange={(e) => setForm({ ...form, placa: e.target.value.toUpperCase() })} /></label>
      <label>Evento<select value={form.tipo_evento} onChange={(e) => setForm({ ...form, tipo_evento: e.target.value })}>
        <option value="entrada">Entrada</option><option value="saida">Saida</option>
      </select></label>
      <label>Justificativa<input required minLength={3} maxLength={1000} value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} /></label>
      <button value="aceitar" disabled={salvando || !podeAceitar}>Aceitar e criar evento</button>
      <button value="rejeitar" className="danger" disabled={salvando}>Rejeitar</button>
    </div>
    {erro && <p className="error">{erro}</p>}
  </form>;
}
