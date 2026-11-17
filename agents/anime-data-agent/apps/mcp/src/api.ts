export class ApiFailure extends Error {
  constructor(public code: string, message: string) { super(message); }
}

export class CatalogApi {
  readonly base: URL;
  constructor(base = process.env.ANIME_API_URL || 'http://127.0.0.1:8000',
              readonly timeout = 15000, readonly request: typeof fetch = fetch) {
    this.base = new URL(base);
    if (!['http:', 'https:'].includes(this.base.protocol) || this.base.username || this.base.password
        || this.base.search || this.base.hash || this.base.pathname !== '/') {
      throw new Error('ANIME_API_URL debe ser un origen HTTP sin credenciales, ruta ni parámetros.');
    }
  }

  async call(path: '/api/query' | '/api/dataset', payload?: Record<string, unknown>): Promise<Record<string, unknown>> {
    try {
      const response = await this.request(new URL(path, this.base), {
        method: payload ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: payload ? JSON.stringify(payload) : undefined,
        signal: AbortSignal.timeout(this.timeout), redirect: 'error',
      });
      if (!response.ok) {
        // Never reflect upstream bodies, credentials or arbitrary exception text.
        if (response.status === 422) throw new ApiFailure('invalid_query', 'La API rechazó los filtros o IDs. Consultá get_dataset_info para valores admitidos.');
        if (response.status === 404) throw new ApiFailure('not_found', 'Ruta o registro no encontrado en la API.');
        throw new ApiFailure('api_unavailable', 'La API no puede atender la consulta. Revisá el dataset y el servidor Python.');
      }
      const reader = response.body?.getReader();
      if (!reader) throw new ApiFailure('invalid_response', 'La API devolvió una respuesta vacía.');
      const chunks: Uint8Array[] = [];
      let bytes = 0;
      try {
        while (true) {
          const part = await reader.read();
          if (part.done) break;
          bytes += part.value.byteLength;
          if (bytes > 2 * 1024 * 1024) throw new ApiFailure('response_too_large', 'El resultado supera 2 MiB; acotá la consulta.');
          chunks.push(part.value);
        }
      } finally { await reader.cancel().catch(() => {}); }
      const value = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid object');
      return value;
    } catch (error) {
      if (error instanceof ApiFailure) throw error;
      if (error instanceof Error && ['TimeoutError', 'AbortError'].includes(error.name)) {
        throw new ApiFailure('timeout', 'La API superó el tiempo de espera; intentá nuevamente.');
      }
      throw new ApiFailure('connection_or_response', 'No se pudo consultar la API local o su respuesta no es válida. Iniciá scripts/start_api.py --mode rules.');
    }
  }
}
