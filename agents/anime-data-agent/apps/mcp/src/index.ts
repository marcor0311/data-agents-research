import { serveStdio } from '@modelcontextprotocol/server/stdio';
import { createCatalogServer } from './server.js';
import { createHttpServer } from './http.js';

try {
  const mode = process.argv[2];
  if (mode && mode !== '--stdio') throw new Error('Usá --stdio o ningún argumento para HTTP.');
  if (mode === '--stdio') {
    const handle = serveStdio(() => createCatalogServer());
    console.error('Anime MCP: stdio listo; consultas de solo lectura a Python.');
    process.on('SIGINT', () => { void handle.close(); });
    process.on('SIGTERM', () => { void handle.close(); });
  } else {
    const port = Number(process.env.ANIME_MCP_PORT || 3001);
    if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('ANIME_MCP_PORT inválido.');
    const http = createHttpServer();
    http.on('error', () => { console.error('No se pudo iniciar MCP; revisá si el puerto está ocupado.'); process.exitCode = 1; });
    http.listen(port, '127.0.0.1', () => console.error(`Anime MCP: http://127.0.0.1:${port}/mcp (solo loopback).`));
    const stop = () => { http.close(); http.closeIdleConnections(); };
    process.on('SIGINT', stop);
    process.on('SIGTERM', stop);
  }
} catch {
  console.error('Configuración MCP inválida. Revisá ANIME_API_URL, ANIME_MCP_PORT y los argumentos.');
  process.exitCode = 1;
}
