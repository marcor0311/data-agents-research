"use client";
import Link from "next/link";
import { useState } from "react";
import { Anime, Media, number, score, format, status } from "../lib/api";

export function Header({ analysis = false }: { analysis?: boolean }) {
  return <header className="site-header"><Link className="brand" href="/"><span className="brand-icon" aria-hidden="true">a<span>↗</span></span><span>ANIME<span className="brand-sub">DATA AGENT</span></span></Link>
    <nav aria-label="Navegación principal"><Link href="/" aria-current={!analysis ? "page" : undefined}>Explorar</Link><Link href="/analisis" aria-current={analysis ? "page" : undefined}>Análisis <span aria-hidden="true">↗</span></Link></nav>
    <span className="header-note"><i />Catálogo · 2026</span></header>;
}

export function Art({ src, alt, className = "", eager = false }: { src?: string | null; alt: string; className?: string; eager?: boolean }) {
  const [failed, setFailed] = useState<string | null>(null);
  const safe = src && /^https:\/\/(s4\.anilist\.co|s\.anilist\.co|cdn\.anilist\.co)\//.test(src);
  if (!safe || failed === src) return <div className={`art-placeholder ${className}`} role="img" aria-label={`Imagen no disponible: ${alt}`}><span aria-hidden="true">ア</span><small>Imagen no disponible</small></div>;
  return <img className={className} src={src} alt={alt} loading={eager ? "eager" : "lazy"} decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(src)} />;
}

export function Metrics({ anime }: { anime: Anime }) {
  return <dl className="metrics"><div><dt>Puntuación</dt><dd>★ {score(anime.score)}<small>/ 10</small></dd></div><div><dt>Valoraciones</dt><dd>{number(anime.scored_by)}</dd></div><div><dt>Episodios</dt><dd>{number(anime.episodes)}</dd></div></dl>;
}

export function AnimeDetail({ anime, media, loading = false }: { anime: Anime; media?: Media; loading?: boolean }) {
  return <section className="anime-detail"><div className="detail-heading"><Art src={media?.cover} alt={`Portada de ${anime.title}`} className="detail-poster" /><div><span className="eyebrow">FICHA · MAL {anime.anime_id}</span><h2>{anime.title}</h2><p>{anime.english_title && anime.english_title !== anime.title ? anime.english_title : anime.japanese_title}</p><div className="tags"><span>{format[anime.type] || anime.type}</span><span>{anime.start_date || "Fecha desconocida"}</span><span>{status[anime.status] || anime.status}</span></div></div></div>
    <Metrics anime={anime} /><div className="tags">{anime.genres.map(g => <span key={g}>{g}</span>)}</div><p className="synopsis">{loading ? "Cargando sinopsis…" : anime.synopsis || "Sin sinopsis disponible en esta captura."}</p><p className="muted">Estudios: {anime.studios.join(", ") || "No disponibles"}. Posición de popularidad: {number(anime.popularity)}.</p><div className="source-links"><a href={anime.source_url} target="_blank" rel="noreferrer">Ficha en MyAnimeList ↗</a>{media && <a href={media.source_url} target="_blank" rel="noreferrer">Imagen · AniList ↗</a>}</div></section>;
}
