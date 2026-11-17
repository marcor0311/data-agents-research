export type Anime = {
  anime_id: number; title: string; english_title: string | null; japanese_title: string | null;
  type: string; episodes: number | null; duration_seconds: number | null; status: string;
  studios: string[]; genres: string[]; score: number | null; scored_by: number;
  popularity: number | null; rank: number | null; start_year: number | null;
  start_date: string | null; future_start: boolean | null; synopsis?: string | null;
  source_url: string; quality_flags: string[];
};
export type QuerySpec = {
  kind?: "search" | "rank" | "detail" | "compare" | "aggregate";
  filters?: Record<string, unknown>; order_by?: string; direction?: string | null;
  limit?: number; ids?: number[]; group_by?: string;
};
export type QueryResult = {
  status: "result" | "empty"; kind: string; total: number; matched_total: number;
  omitted_missing_metric: number; applied_query: QuerySpec; rows: Anime[];
  groups: { key: string; count: number }[];
  definitions: Record<string, string>;
  evidence: { load_id: string; source_file_date: string; selected_ids: number[]; shown_ids: number[]; [key: string]: unknown };
};
export type AgentResponse = {
  status: "result" | "empty" | "clarification"; explanation: string;
  result: QueryResult | null;
  state: { query: QuerySpec | null; selected_ids: number[]; load_id: string | null };
  visualization_action: string; interpreter: string;
  model_run?: { model: string; requests: number; input_tokens: number; output_tokens: number; duration_ms: number } | null;
};
export type Health = { model_warning?: string | null; agent_mode: "rules" | "openai"; model_status: string; model_name: string | null; model_last_verified_at: string | null };
export type Turn = { id: string; parent_turn_id: string | null; created_at: string; message: string; response: AgentResponse };
export type Conversation = { id: string; active_turn_id: string | null; created_at: string; turns: Turn[] };
export type Media = { cover: string | null; banner: string | null; source_url: string; collected_at: string; anilist_id: string };
export type MediaIndex = { load_id: string; images: Record<string, Media> };
export type Dataset = { load_id: string; records: number; source_file_date: string; reference_date: string; formats: string[]; genres: string[] };

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T>(path: string, body?: unknown, timeout = 30000): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? "GET" : "POST", cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeout),
  });
  let data: unknown;
  try { data = await response.json(); } catch { throw new ApiError("La API no respondió. Comprobá que esté ejecutándose.", response.status); }
  if (!response.ok) {
    const detail = (data as { detail?: unknown }).detail;
    throw new ApiError(typeof detail === "string" ? detail : "La consulta contiene parámetros inválidos.", response.status);
  }
  return data as T;
}

export async function loadMedia(): Promise<MediaIndex | null> {
  try { const r = await fetch("/media-index.json"); return r.ok ? await r.json() : null; } catch { return null; }
}
export const query = (body: QuerySpec) => api<QueryResult>("/query", body);
export const number = (value: number | null | undefined) => value == null ? "—" : value.toLocaleString("es-CR");
export const score = (value: number | null) => value == null ? "Sin puntuación" : value.toFixed(2);
export const format: Record<string, string> = { tv: "Serie TV", movie: "Película", music: "Música", ova: "OVA", ona: "ONA", special: "Especial", tv_special: "Especial TV", cm: "CM", pv: "PV", unknown: "Sin formato" };
export const status: Record<string, string> = { finished_airing: "Finalizado", currently_airing: "En emisión", not_yet_aired: "Próximo estreno" };
