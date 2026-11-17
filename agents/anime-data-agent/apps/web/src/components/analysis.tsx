"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Anime, api, ApiError, Conversation, Dataset, Health, loadMedia, MediaIndex, number, QueryResult, score, Turn, format } from "../lib/api";
import { AnimeDetail, Art, Header } from "./shared";
import { useArtwork } from "../lib/artwork";

const SESSION = "anime-data-agent:conversation:v1";
let opening: Promise<Conversation> | null = null;
function remember(id: string) { try { localStorage.setItem(SESSION, id); } catch { /* history remains on server */ } }
function openSession() {
  if (!opening) {
    opening = (async () => {
      let id: string | null = null;
      try { id = localStorage.getItem(SESSION); } catch { /* optional local pointer */ }
      if (id) { try { return await api<Conversation>(`/conversations/${encodeURIComponent(id)}`); } catch (e) { if (!(e instanceof ApiError) || e.status !== 404) throw e; } }
      const created = await api<Conversation>("/conversations", {}); remember(created.id); return created;
    })().finally(() => { opening = null; });
  }
  return opening;
}
type Pending = { message: string; base_turn_id: string | null; selected_ids: number[]; request_id: string };

export default function Analysis() {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [media, setMedia] = useState<MediaIndex | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [incoming, setIncoming] = useState<Anime | null>(null);
  const [detail, setDetail] = useState<Anime | null>(null);
  const [view, setView] = useState<"table" | "chart">("table");
  const [initAttempt, setInitAttempt] = useState(0);
  const pending = useRef<Pending | null>(null);
  const thread = useRef<HTMLDivElement>(null);
  const turn = conversation?.turns.find(t => t.id === conversation.active_turn_id);
  const result = turn?.response.result || null;
  const artwork = useArtwork(media, result?.evidence.load_id || dataset?.load_id, [...(result?.rows.map(r => r.anime_id) || []), ...(incoming ? [incoming.anime_id] : []), ...(detail ? [detail.anime_id] : [])]);
  const images = artwork.images;

  useEffect(() => {
    let active = true;
    setBusy(true); setError("");
    void openSession().then(c => { if (active) { setConversation(c); setSelected(c.turns.find(t => t.id === c.active_turn_id)?.response.state.selected_ids || []); } })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : "No se pudo abrir el historial."); })
      .finally(() => { if (active) setBusy(false); });
    void api<Dataset>("/dataset").then(d => { if (active) setDataset(d); }).catch(() => {});
    void api<Health>("/health").then(h => { if (active) setHealth(h); }).catch(() => {});
    void loadMedia().then(m => { if (active) setMedia(m); });
    const id = new URLSearchParams(location.search).get("anime");
    if (id && /^\d+$/.test(id)) void api<QueryResult>(`/anime/${id}`).then(r => { if (active) setIncoming(r.rows[0]); }).catch(() => {});
    return () => { active = false; };
  }, [initAttempt]);

  useEffect(() => { const element = thread.current; if (element) element.scrollTop = element.scrollHeight; }, [conversation, busy]);

  async function send(message: string, retry = false) {
    if (!conversation || busy || !message.trim()) return;
    const body = retry && pending.current ? pending.current : {
      message: message.trim(), base_turn_id: conversation.active_turn_id,
      selected_ids: selected, request_id: crypto.randomUUID(),
    };
    pending.current = body; setBusy(true); setError("");
    try {
      await api<Turn>(`/conversations/${conversation.id}/turns`, body, 90000);
      const refreshed = await api<Conversation>(`/conversations/${conversation.id}`);
      setConversation(refreshed); setSelected(refreshed.turns.find(t => t.id === refreshed.active_turn_id)?.response.state.selected_ids || []);
      setDraft(""); setDetail(null); pending.current = null;
      void api<Health>("/health").then(setHealth).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar el mensaje.");
      if (e instanceof ApiError && e.status === 409) {
        try { const fresh = await api<Conversation>(`/conversations/${conversation.id}`); setConversation(fresh); setSelected([]); pending.current = null; } catch { /* keep exact retry body */ }
      }
    } finally { setBusy(false); }
  }

  async function activate(saved: Turn) {
    if (!conversation || busy) return;
    setBusy(true); setError("");
    try {
      const restored = await api<Conversation>(`/conversations/${conversation.id}/activate`, { turn_id: saved.id, expected_active_turn_id: conversation.active_turn_id });
      setConversation(restored); setSelected(saved.response.state.selected_ids); setDetail(null); pending.current = null;
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo recuperar ese turno.");
      if (e instanceof ApiError && e.status === 409) { try { setConversation(await api<Conversation>(`/conversations/${conversation.id}`)); setSelected([]); } catch { /* retained */ } }
    } finally { setBusy(false); }
  }
  async function newConversation() {
    if (busy) return;
    setBusy(true); setError("");
    try { const next = await api<Conversation>("/conversations", {}); remember(next.id); setConversation(next); setSelected([]); setDetail(null); setDraft(""); pending.current = null; }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo crear la conversación."); } finally { setBusy(false); }
  }
  async function openDetail(anime: Anime) {
    try { const r = await api<QueryResult>(`/anime/${anime.anime_id}`); setDetail(r.rows[0]); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo cargar el detalle."); }
  }
  function toggle(id: number) { setSelected(previous => previous.includes(id) ? previous.filter(i => i !== id) : previous.length < 2 ? [...previous, id] : previous); }
  function submit(event: FormEvent) { event.preventDefault(); void send(draft); }
  const suggestions = result ? ["Solo TV", "Máximo 26 episodios", "Ordénalos por popularidad"] : ["Busca Death Note", "Muéstrame los 10 animes de fantasía mejor puntuados", "¿Cuántas series se estrenaron por año desde 2020?"];

  return <><Header analysis /><main className="analysis-shell">
    <div className="workspace-heading"><div><span className="eyebrow">DE LA PREGUNTA A LA EVIDENCIA</span><h1>Explorá. Compará. <em>Descubrí.</em></h1></div><div className="workspace-badge"><i />{health?.agent_mode === "openai" ? `OpenAI · ${health.model_name}` : health ? "Conversación con reglas acotadas" : "Comprobando modo de conversación"}<span>{health?.agent_mode === "openai" ? health.model_status === "verified" ? "Llamada real verificada · herramientas locales" : health.model_status === "missing_api_key" ? "Falta configurar la clave local" : "Configurado · pendiente de primera llamada real" : health ? (health.model_warning ? `IA no disponible: ${health.model_warning}. Continuamos con reglas locales.` : "Modo explícito sin modelo de IA") : "El resultado anterior se conserva"}</span></div></div>
    <div className="workspace-grid">
      <section className="chat-panel" aria-labelledby="chat-heading"><div className="panel-heading"><div><span className="eyebrow">TU CONVERSACIÓN</span><h2 id="chat-heading">Preguntale al catálogo</h2></div><button className="icon-button" title="Nueva conversación; conserva la anterior" aria-label="Nueva conversación" disabled={busy} onClick={() => void newConversation()}>＋</button></div>
        {incoming && <div className="incoming-anime"><Art src={images?.[incoming.anime_id]?.cover} alt={`Portada de ${incoming.title}`} /><div><span className="eyebrow">DESDE EXPLORAR</span><strong>{incoming.title}</strong><button disabled={busy} onClick={() => void send(`Detalle de ${incoming.anime_id}`)}>Ver en la conversación ↗</button></div><button className="dismiss" aria-label="Descartar anime elegido" onClick={() => setIncoming(null)}>×</button></div>}
        <div className="chat-thread" ref={thread} aria-label="Historial de conversación">
          {!conversation?.turns.length && <div className="chat-welcome"><div className="welcome-icon" aria-hidden="true">✳</div><h3>Una buena pregunta<br />abre otra historia.</h3><p>Buscá un título, compará dos entregas o explorá los estrenos por año.</p></div>}
          {conversation?.turns.map((saved, i) => <article className={`chat-turn ${saved.id === conversation.active_turn_id ? "active-turn" : ""}`} key={saved.id}>
            <div className="user-message"><span>VOS · {String(i + 1).padStart(2, "0")}</span><p>{saved.message}</p></div><div className="agent-message"><span className="agent-label">✳ DATA AGENT <small>{saved.response.interpreter === "openai_tools" ? "OPENAI + HERRAMIENTAS" : "REGLAS"}</small>{saved.response.status === "clarification" && <small>ACLARACIÓN</small>}</span><p>{saved.response.explanation}</p>{saved.response.model_run && <p className="muted">{saved.response.model_run.requests} llamadas · {number(saved.response.model_run.input_tokens)} tokens de entrada · {number(saved.response.model_run.output_tokens)} de salida</p>}<button className="text-button" disabled={busy || saved.id === conversation.active_turn_id} onClick={() => void activate(saved)}>{saved.id === conversation.active_turn_id ? "Turno activo" : "Recuperar este turno ↶"}</button></div>
          </article>)}
          {busy && <p className="thinking" role="status">Preparando resultados…</p>}
        </div>
        {error && <div className="error-message" role="alert"><p>{error}</p>{pending.current ? <button disabled={busy} onClick={() => void send(pending.current!.message, true)}>Reintentar el mismo envío</button> : <button disabled={busy} onClick={() => setInitAttempt(n => n + 1)}>Reconectar</button>}<small>El resultado anterior se conserva.</small></div>}
        <div className="composer"><div className="prompt-chips">{suggestions.map(s => <button key={s} disabled={busy || !conversation} onClick={() => void send(s)}>{s}</button>)}</div><form onSubmit={submit}><label className="sr-only" htmlFor="message">Mensaje al agente</label><textarea id="message" placeholder="Por ejemplo: Busca Death Note" value={draft} onChange={e => setDraft(e.target.value)} maxLength={2000} rows={2} disabled={busy} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(draft); } }} /><button className="send-button" type="submit" aria-label="Enviar mensaje" disabled={busy || !draft.trim() || !conversation}>↗</button></form><small>Enter para enviar · Shift + Enter para una nueva línea</small></div>
      </section>

      <section className="results-panel" aria-labelledby="results-heading"><div className="panel-heading"><div><span className="eyebrow">RESULTADOS CON CONTEXTO</span><h2 id="results-heading">{detail ? "Detalle del anime" : result?.kind === "compare" ? "Comparación" : result?.kind === "aggregate" ? "Patrones del catálogo" : "Tu espacio de análisis"}</h2></div>{detail && <button className="text-button" onClick={() => setDetail(null)}>← Volver a resultados</button>}</div>
        {detail ? <AnimeDetail anime={detail} media={images?.[detail.anime_id]} /> : result ? <>
          <div className="result-summary"><strong>{number(result.total)}<span>{result.kind === "aggregate" ? "registros agrupados" : "registros elegibles"}</span></strong><p>{result.kind === "aggregate" ? `${result.groups.length} grupos` : `${result.rows.length} visibles de ${number(result.total)}`}<span>{result.omitted_missing_metric ? `${number(result.omitted_missing_metric)} sin dato para ordenar` : "Sin mínimo obligatorio de valoraciones"}</span></p></div>
          <details className="filter-details"><summary>Filtros y orden aplicados</summary><pre>{JSON.stringify(result.applied_query, null, 2)}</pre></details>
          {result.status === "empty" ? <div className="empty-state"><h3>Sin coincidencias.</h3><p>La selección está vacía. Refiná los filtros o iniciá otra búsqueda.</p></div> : <>
            <div className="results-toolbar"><div className="segmented small"><button aria-pressed={view === "table"} onClick={() => setView("table")}>Tabla</button><button aria-pressed={view === "chart"} onClick={() => setView("chart")}>Gráfico</button></div>{result.rows.length > 0 && <div className="selection-actions"><span>{selected.length} / 2 seleccionados</span><button className="button compact" disabled={selected.length !== 2 || busy} onClick={() => void send("Compara estos dos")}>Comparar ↗</button><button className="text-button" disabled={!selected.length || busy} onClick={() => setSelected([])}>Limpiar</button></div>}</div>
            {view === "chart" ? <Chart result={result} selected={selected} onSelect={toggle} /> : result.kind === "aggregate" ? <div className="table-scroll"><table><caption>Conteos de la selección filtrada completa</caption><thead><tr><th>Grupo</th><th>Registros</th></tr></thead><tbody>{result.groups.map(g => <tr key={g.key}><td>{g.key}</td><td>{number(g.count)}</td></tr>)}</tbody></table></div> : <div className="table-scroll"><table><caption>Datos de las entregas devueltas por la consulta</caption><thead><tr><th><span className="sr-only">Seleccionar</span></th><th>Anime</th><th>Puntuación / 10</th><th>Valoraciones</th><th>Episodios</th><th>Pos. popularidad</th></tr></thead><tbody>{result.rows.map(anime => <tr key={anime.anime_id} className={selected.includes(anime.anime_id) ? "row-selected" : ""}><td><input type="checkbox" aria-label={`Seleccionar ${anime.title}`} checked={selected.includes(anime.anime_id)} disabled={busy || (!selected.includes(anime.anime_id) && selected.length === 2)} onChange={() => toggle(anime.anime_id)} /></td><td><button className="table-title" onClick={() => void openDetail(anime)}><Art src={images?.[anime.anime_id]?.cover} alt="" /><span>{anime.title}<small>{format[anime.type] || anime.type} · {anime.start_year} · ID {anime.anime_id}</small></span></button></td><td>{score(anime.score)}</td><td>{number(anime.scored_by)}</td><td>{number(anime.episodes)}</td><td>{number(anime.popularity)}</td></tr>)}</tbody></table></div>}
            {result.kind === "compare" && <div className="comparison-facts">{result.rows.map(anime => <article key={anime.anime_id}><h3>{anime.title}</h3><p><b>Géneros</b>{anime.genres.join(", ") || "Desconocidos"}</p><p><b>Estudios</b>{anime.studios.join(", ") || "Desconocidos"}</p><button className="text-button" onClick={() => void openDetail(anime)}>Abrir ficha ↗</button></article>)}</div>}
          </>}
          <details className="evidence-details"><summary>Fuente y evidencia de este resultado <span>↗</span></summary><p>MyAnimeList mediante LeoRigasaki/Anime-dataset. Fecha del archivo: {result.evidence.source_file_date}; no certifica actualización de cada fila.</p><p className="muted">{result.definitions.groups}</p><pre>{JSON.stringify(result.evidence, null, 2)}</pre></details>
        </> : <div className="results-empty"><span className="orbital-mark" aria-hidden="true">◎</span><h3>Las preguntas cambian.<br /><em>Los datos las conectan.</em></h3><p>Tus resultados aparecerán acá, con filtros, visualizaciones y la fuente de cada consulta.</p><div className="empty-stats"><span><b>{number(dataset?.records)}</b>entregas en la captura</span><span><b>0</b>cifras inventadas</span></div><Link href="/">Volver a explorar el catálogo ↗</Link></div>}
      </section>
    </div><footer className="workspace-footer"><span>MyAnimeList · captura {dataset?.source_file_date || "2026-11-16"}</span><span>Historial local persistente · {conversation ? `Conversación ${conversation.id.slice(0, 8)}` : "Sin conexión"}</span><span>Escritorio · móvil en beta futura</span></footer>
  </main></>;
}

function Chart({ result, selected, onSelect }: { result: QueryResult; selected: number[]; onSelect: (id: number) => void }) {
  const aggregate = result.kind === "aggregate";
  const metric = aggregate ? "count" : ["score", "popularity", "scored_by", "episodes", "duration_seconds", "rank", "start_year"].includes(result.applied_query.order_by || "") ? result.applied_query.order_by! : "score";
  const labels: Record<string, string> = { count: "Registros", score: "Puntuación / 10", popularity: "Posición de popularidad · menor es mejor", scored_by: "Valoraciones", episodes: "Episodios", duration_seconds: "Segundos por episodio", rank: "Posición reportada por MAL", start_year: "Año de estreno" };
  const data = aggregate ? result.groups.map(g => ({ key: g.key, value: g.count, id: null })) : result.rows.map(r => ({ key: r.title, value: r[metric as keyof Anime] as number | null, id: r.anime_id }));
  const maximum = metric === "score" ? 10 : Math.max(1, ...data.map(d => d.value || 0));
  return <figure className="chart"><figcaption>{labels[metric]}<small>Misma selección de la tabla · escala desde cero</small></figcaption><div className="chart-rows">{data.map((d, i) => <div className={`chart-row ${d.id && selected.includes(d.id) ? "chart-selected" : ""}`} key={`${d.id || d.key}-${i}`}><span className="chart-name" title={d.key}>{d.id ? <button disabled={!selected.includes(d.id) && selected.length === 2} onClick={() => onSelect(d.id!)} aria-pressed={selected.includes(d.id)}>{d.key}</button> : d.key}</span><div className="bar-track"><span className="bar-fill" style={{ width: `${d.value == null ? 0 : d.value / maximum * 100}%` }} /></div><span className="bar-value">{d.value == null ? "Sin dato" : metric === "score" ? d.value.toFixed(2) : number(d.value)}</span></div>)}</div><p className="muted">{aggregate ? result.definitions.groups : "Seleccioná hasta dos barras para comparar. Los valores desconocidos no se dibujan como cero."}</p></figure>;
}
