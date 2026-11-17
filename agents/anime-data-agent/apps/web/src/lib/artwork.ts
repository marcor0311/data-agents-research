"use client";
import { useEffect, useState } from "react";
import type { Media, MediaIndex } from "./api";

const resolved = new Map<number, Media>();
const requests = new Map<string, Promise<Record<string, Media>>>();

async function lookup(ids: number[]) {
  const key = [...ids].sort((a,b) => a-b).join(",");
  if (!requests.has(key)) requests.set(key, (async () => {
    const response = await fetch("/api/artwork", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }), signal: AbortSignal.timeout(25000) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "No se pudieron completar las imágenes.");
    const images = payload.images as Record<string, Media>;
    for (const [id, media] of Object.entries(images)) resolved.set(Number(id), media);
    return images;
  })().finally(() => { requests.delete(key); }));
  return requests.get(key)!;
}

export function useArtwork(index: MediaIndex | null, loadId: string | undefined, ids: number[]) {
  const [live, setLive] = useState<Record<string, Media>>({});
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const key = [...new Set(ids)].join(",");
  useEffect(() => {
    let active = true;
    const requested = key ? key.split(",").map(Number) : [];
    setError("");
    const existing = Object.fromEntries(requested.filter(id => resolved.has(id)).map(id => [id, resolved.get(id)!]));
    setLive(existing);
    const missing = requested.filter(id => !resolved.has(id));
    void (async () => {
      for (let i = 0; i < missing.length && active; i += 20) {
        try { const found = await lookup(missing.slice(i, i+20)); if (active) setLive(previous => ({ ...previous, ...found })); }
        catch (e) { if (active) setError(e instanceof Error ? e.message : "No se pudieron completar las imágenes."); break; }
      }
    })();
    return () => { active = false; };
  }, [key, attempt]);
  const local = loadId && index?.load_id === loadId ? index.images : {};
  return { images: { ...local, ...live }, error, retry: () => setAttempt(n => n + 1) };
}
