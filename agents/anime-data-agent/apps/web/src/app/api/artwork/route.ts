/** On-demand artwork references for visible IDs only; never imports ratings. */
export const runtime = "nodejs";

type Artwork = { cover: string | null; banner: string | null; source_url: string; collected_at: string; anilist_id: string };
const cache = new Map<number, { value: Artwork | null; expires: number }>();
let pending: Promise<void> = Promise.resolve();

function image(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try { const u = new URL(value); return u.protocol === "https:" && ["s4.anilist.co", "s.anilist.co", "cdn.anilist.co"].includes(u.hostname) ? u.href : null; }
  catch { return null; }
}

export async function POST(request: Request) {
  let body: unknown;
  try { body = await request.json(); } catch { return Response.json({ detail: "JSON inválido." }, { status: 400 }); }
  const values = (body as { ids?: unknown } | null)?.ids;
  if (!Array.isArray(values) || !values.length || values.length > 20 || values.some(x => !Number.isSafeInteger(x) || x <= 0 || x > 10000000)) {
    return Response.json({ detail: "Indicá entre 1 y 20 IDs válidos." }, { status: 422 });
  }
  const ids = [...new Set(values as number[])];
  // Serialize upstream calls and re-check cache after acquiring the queue.
  const previous = pending;
  let release!: () => void;
  pending = new Promise<void>(resolve => { release = resolve; });
  try {
    await previous;
    const missing = ids.filter(id => !cache.has(id) || cache.get(id)!.expires <= Date.now());
    if (missing.length) {
      const fields = missing.map(id => `anime${id}: Media(idMal: ${id}, type: ANIME) { id idMal siteUrl bannerImage coverImage { extraLarge large } }`).join("\n");
      const upstream = await fetch("https://graphql.anilist.co", {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ query: `{ ${fields} }` }), cache: "no-store", signal: AbortSignal.timeout(12000),
      });
      if (!upstream.ok) return Response.json({ detail: "La fuente de imágenes no respondió. Los datos del anime siguen disponibles." }, { status: 503 });
      const payload = await upstream.json();
      if (!payload.data || typeof payload.data !== "object") return Response.json({ detail: "No se pudo comprobar la fuente de imágenes." }, { status: 503 });
      for (const id of missing) {
        const value = payload.data[`anime${id}`];
        if (value?.idMal !== id || !Number.isSafeInteger(value.id) || !value.siteUrl?.startsWith("https://anilist.co/anime/")) continue;
        const cover = image(value.coverImage?.extraLarge) || image(value.coverImage?.large);
        const banner = image(value.bannerImage);
        cache.set(id, { value: cover || banner ? { cover, banner, source_url: value.siteUrl, collected_at: new Date().toISOString(), anilist_id: String(value.id) } : null, expires: Date.now() + 86400000 });
      }
    }
    return Response.json({ images: Object.fromEntries(ids.filter(id => cache.get(id)?.value).map(id => [id, cache.get(id)!.value])), source: "AniList, artwork only" });
  } catch {
    return Response.json({ detail: "No se pudo conectar con la fuente de imágenes. Podés reintentar; el catálogo no depende de ella." }, { status: 503 });
  } finally { release(); }
}
