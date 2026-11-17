import { createServer } from 'node:http';
import { createMcpHandler } from '@modelcontextprotocol/server';
import { localhostHostValidation, localhostOriginValidation, toNodeHandler } from '@modelcontextprotocol/node';
import { CatalogApi } from './api.js';
import { createCatalogServer } from './server.js';

export function createHttpServer(api = new CatalogApi()) {
  const handler = createMcpHandler(() => createCatalogServer(api), { responseMode: 'json' });
  const serve = toNodeHandler(handler);
  const validateHost = localhostHostValidation();
  const validateOrigin = localhostOriginValidation();
  const http = createServer((req, res) => {
    if (!validateHost(req, res) || !validateOrigin(req, res)) return;
    if (req.url === '/healthz' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ service: 'anime-data-agent-mcp', status: 'ok', api_verified: false }));
      return;
    }
    if (req.url !== '/mcp') { res.writeHead(404); res.end(); return; }
    void serve(req, res).catch(() => {
      if (!res.headersSent) res.writeHead(500);
      res.end();
    });
  });
  http.requestTimeout = 30000;
  http.headersTimeout = 10000;
  http.on('close', () => { void handler.close(); });
  return http;
}
