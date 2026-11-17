"use client";
import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Anime, api, Dataset, format, loadMedia, MediaIndex, number, query, QueryResult, score, status } from "../lib/api";
import { Art, Header, Metrics } from "./shared";
import { AnimeDetail } from "./shared";
import { useArtwork } from "../lib/artwork";

type Mode = "recent" | "score" | "popular";
const MODES: { id: Mode; name: string; subtitle: string }[] = [
  { id: "recent", name: "Estrenos recientes", subtitle: "Estrenos 2025–2026 · ordenados por puntuación" },
  { id: "score", name: "Mejor puntuados", subtitle: "Todo el catálogo · ordenado por puntuación" },
  { id: "popular", name: "Más populares", subtitle: "Todo el catálogo · menor posición de popularidad primero" },
];

export default function Explore() {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [media, setMedia] = useState<MediaIndex | null>(null);
  const [mode, setMode] = useState<Mode>("recent");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [selected, setSelected] = useState<Anime | null>(null);
  const [detail, setDetail] = useState<Anime | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailBusy, setDetailBusy] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [searchMode, setSearchMode] = useState(false);
  const [retry, setRetry] = useState(0);
  const sequence = useRef(0);
  const hero = useRef<HTMLElement>(null);
  const rail = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const artwork = useArtwork(media, result?.evidence.load_id || dataset?.load_id, result?.rows.map(r => r.anime_id) || []);

  useEffect(() => { void api<Dataset>("/dataset").then(setDataset).catch(() => {}); void loadMedia().then(setMedia); }, []);

  useEffect(() => {
    const id = ++sequence.current;
    setBusy(true); setError("");
    const spec = searchMode ? { kind: "search" as const, filters: { title: search.trim() }, order_by: "title", limit: 20 }
      : { kind: "rank" as const, filters: mode === "recent" ? { year_from: 2025, year_to: 2026 } : {}, order_by: mode === "popular" ? "popularity" : "score", limit: 20 };
    void query(spec).then(r => {
      if (id !== sequence.current) return;
      setResult(r); setSelected(r.rows[0] || null);
    }).catch(e => { if (id === sequence.current) setError(e instanceof Error ? e.message : "No se pudo consultar el catálogo."); })
      .finally(() => { if (id === sequence.current) setBusy(false); });
    // Search is submitted explicitly; typing does not change results.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, searchMode, retry]);

  useEffect(() => {
    let active = true;
    setDetail(null);
    setDetailError("");
    setDetailBusy(Boolean(selected));
    if (selected) void api<QueryResult>(`/anime/${selected.anime_id}`).then(r => { if (active) setDetail(r.rows[0]); })
      .catch(e => { if (active) setDetailError(e instanceof Error ? e.message : "No se pudo cargar la ficha."); })
      .finally(() => { if (active) setDetailBusy(false); });
    return () => { active = false; };
  }, [selected, detailAttempt]);

  useEffect(() => {
    const element = dialog.current;
    if (detailVisible && !element?.open) element?.showModal();
    else if (!detailVisible && element?.open) element.close();
  }, [detailVisible]);

  useEffect(() => {
    const element = hero.current;
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    const scroll = () => { element?.style.setProperty("--parallax-y", motion.matches ? "0px" : `${Math.min(scrollY * .22, 160)}px`); };
    scroll(); addEventListener("scroll", scroll, { passive: true }); motion.addEventListener("change", scroll);
    return () => { removeEventListener("scroll", scroll); motion.removeEventListener("change", scroll); };
  }, []);

  function pick(anime: Anime, openDetail = false) {
    setSelected(anime);
    if (openDetail) setDetailVisible(true);
  }
  function move(offset: number) {
    if (!result?.rows.length) return;
    const index = result.rows.findIndex(r => r.anime_id === selected?.anime_id);
    pick(result.rows[(index + offset + result.rows.length) % result.rows.length]);
  }
  function submit(event: FormEvent) { event.preventDefault(); if (!search.trim()) return; setSearchMode(true); setRetry(r => r + 1); }
  const images = artwork.images;
  const image = selected ? images?.[selected.anime_id] : undefined;
  const current = detail?.anime_id === selected?.anime_id ? detail : selected;
  const position = result?.rows.findIndex(r => r.anime_id === selected?.anime_id) ?? 0;

  return <><Header /><main className="explore">
    <section className="hero" ref={hero} aria-labelledby="hero-title">
      <div className="hero-scene" key={selected?.anime_id ?? "empty"} aria-hidden="true">
        <Art src={image?.banner || image?.cover} alt="" className={`hero-wallpaper ${!image?.banner ? "cover-backdrop" : ""}`} eager />
      </div><div className="hero-shade" /><div className="hero-grid" aria-hidden="true" />
      <div className="hero-copy">
        <div className="eyebrow"><span className="live-dot" /> EXPLORAR / DESCUBRIR / ANALIZAR</div>
        <p className="hero-kicker">Cada historia tiene datos.</p>
        <h1 id="hero-title" key={selected?.title}>{selected?.title || (busy ? "Un universo por descubrir." : "Encontrá tu próxima historia.")}</h1>
        {current && <><div className="tags hero-tags"><span>{format[current.type] || current.type}</span><span>{current.start_year}</span><span>{status[current.status] || current.status}</span>{current.future_start && <span>Estreno futuro en la captura</span>}</div>
          <p className="hero-synopsis">{detail?.synopsis || (detail ? "Sin sinopsis disponible." : "Explorá su puntuación, sus géneros y los datos de esta entrega.")}</p>
          <Metrics anime={current} />
          <div className="hero-actions"><Link className="button primary" href={`/analisis?anime=${current.anime_id}`}>Analizar este anime <span>↗</span></Link><button className="button quiet" onClick={() => setDetailVisible(true)}>Ver ficha completa ↗</button></div>
          <div className="hero-provenance"><span>{current.genres.slice(0, 3).join(" · ")}</span>{image && <a href={image.source_url} target="_blank" rel="noreferrer">Imagen · AniList ↗</a>}</div></>}
        {!current && !busy && <p>Buscá por título o elegí otra selección.</p>}
      </div>
      <div className="hero-cover" key={`poster-${selected?.anime_id}`}><div className="poster-frame"><Art src={image?.cover} alt={selected ? `Portada de ${selected.title}` : "Seleccioná un anime"} eager />{selected && <span className="poster-caption">MAL {selected.anime_id} <span>{image ? "PORTADA" : "SIN IMAGEN"}</span></span>}</div><span className="poster-vertical">HISTORIAS QUE SE PUEDEN EXPLORAR</span></div>
      <div className="hero-bottom"><span className="hero-index">{String(position + 1).padStart(2, "0")}<small> / {String(result?.rows.length || 0).padStart(2, "0")}</small></span><span>DATOS DE LA CAPTURA · {dataset?.source_file_date || result?.evidence.source_file_date || "Cargando"}</span><div className="arrow-controls"><button aria-label="Anime anterior" onClick={() => move(-1)} disabled={!selected}>←</button><button aria-label="Anime siguiente" onClick={() => move(1)} disabled={!selected}>→</button></div></div>
    </section>

    <section className="catalog-section" id="catalogo" aria-labelledby="catalog-title">
      <div className="section-heading"><div><span className="eyebrow">TU PUNTO DE PARTIDA</span><h2 id="catalog-title">Elegí una historia.<br /><span>Explorá lo que hay detrás.</span></h2></div><p>Un catálogo. Muchas formas de preguntar.<br />{number(dataset?.records)} entregas para explorar.</p></div>
      <div className="catalog-toolbar"><div className="segmented" aria-label="Selección del catálogo">{MODES.map(m => <button key={m.id} aria-pressed={!searchMode && mode === m.id} onClick={() => { setSearchMode(false); setMode(m.id); }}>{m.name}</button>)}</div><form className="search-box" onSubmit={submit}><label className="sr-only" htmlFor="anime-search">Buscar por título</label><span aria-hidden="true">⌕</span><input id="anime-search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar un anime…" maxLength={300} /><button aria-label="Buscar anime" type="submit">↗</button></form></div>
      <div className="catalog-caption"><span>{error ? "Selección anterior · no se pudo aplicar la nueva consulta" : searchMode ? `Búsqueda por título: ${result?.applied_query.filters?.title || search}` : MODES.find(m => m.id === mode)?.subtitle}</span><span>{busy ? "Consultando…" : `${number(result?.total)} elegibles · hasta 20 visibles`}</span></div>
      {error && <div className="error-message" role="alert">{error} <button onClick={() => setRetry(n => n + 1)}>Reintentar</button><span>La selección anterior se conserva.</span></div>}
      <p className="sr-only" role="status" aria-live="polite">{busy ? "Cargando selección" : result?.rows.length ? `${result.rows.length} títulos disponibles` : "Sin coincidencias"}</p>
      <div className={`anime-rail ${busy ? "is-loading" : ""}`} ref={rail} aria-label="Animes de la selección" aria-busy={busy}>
        {result?.rows.map((anime, i) => <button id={`anime-card-${anime.anime_id}`} className={`anime-card ${selected?.anime_id === anime.anime_id ? "selected" : ""}`} key={anime.anime_id} aria-pressed={selected?.anime_id === anime.anime_id} aria-haspopup="dialog" onClick={() => pick(anime, true)}><div className="card-art"><Art src={images?.[anime.anime_id]?.cover} alt={`Portada de ${anime.title}`} /><span className="card-rank">{String(i + 1).padStart(2, "0")}</span><span className="card-score">★ {score(anime.score)}</span></div><h3>{anime.title}</h3><p>{format[anime.type] || anime.type} <span>·</span> {anime.start_year} <span>·</span> Ver ficha ↗</p></button>)}
        {!result && busy && [1,2,3,4,5,6].map(i => <div className="skeleton-card" key={i} />)}
        {result && !result.rows.length && <p className="empty-state">No hay títulos que coincidan. Probá otra búsqueda.</p>}
      </div><p className="catalog-footnote">Seleccioná una tarjeta para abrir la ficha completa y actualizar el fondo. No hay un mínimo de valoraciones aplicado.</p>
      {artwork.error && <div className="artwork-notice" role="status">{artwork.error} <button className="text-button" onClick={artwork.retry}>Reintentar imágenes</button></div>}
    </section>
    <section className="analysis-invite"><div><span className="eyebrow">DEL DESCUBRIMIENTO A LA PREGUNTA</span><h2>Tu curiosidad,<br /><em>con evidencia.</em></h2><p>Compará entregas, encontrá patrones y seguí una conversación sin perder los filtros.</p></div><Link href="/analisis" className="button primary">Abrir espacio de análisis ↗</Link></section>
    <footer className="site-footer"><span>ANIME DATA AGENT</span><span>MyAnimeList · captura {dataset?.source_file_date || "2026-11-16"} · No es un ranking en tiempo real.</span><span>Versión de escritorio · móvil en beta futura</span></footer>
  </main><dialog className="detail-dialog" ref={dialog} aria-label={selected ? `Ficha de ${selected.title}` : "Ficha de anime"} onCancel={() => setDetailVisible(false)} onClose={() => setDetailVisible(false)} onClick={e => { if (e.target === e.currentTarget) setDetailVisible(false); }}><div className="dialog-content"><div className="dialog-toolbar"><span className="eyebrow">FICHA COMPLETA</span><button className="icon-button" aria-label="Cerrar ficha" autoFocus onClick={() => setDetailVisible(false)}>×</button></div>{current && <AnimeDetail anime={current} media={image} loading={detailBusy} />}{detailBusy && <p className="dialog-status" role="status">Cargando la sinopsis y los datos completos…</p>}{detailError && <div className="error-message" role="alert">{detailError} <button onClick={() => setDetailAttempt(n => n + 1)}>Reintentar ficha</button></div>}<div className="dialog-actions">{selected && <Link href={`/analisis?anime=${selected.anime_id}`} className="button primary">Analizar este anime ↗</Link>}<button className="button" onClick={() => { setDetailVisible(false); hero.current?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" }); }}>Ver en la portada ↑</button></div></div></dialog></>;
}
