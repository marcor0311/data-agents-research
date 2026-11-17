// Real SDK client -> MCP -> Python API; no model calls or credentials needed.
import assert from 'node:assert/strict';
import { Client, StreamableHTTPClientTransport } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { fileURLToPath } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { CatalogApi } from '../dist/api.js';

const args = process.argv.slice(2);
if (args.some(a => !['--stdio', '--web'].includes(a))) throw new Error('Argumentos admitidos: --stdio, --web.');
const api = new CatalogApi();
const web = args.includes('--web') ? new CatalogApi(process.env.ANIME_WEB_URL || 'http://127.0.0.1:3000') : null;
const client = new Client({ name: 'anime-phase9-acceptance', version: '0.1.0' });
const root = fileURLToPath(new URL('../../../', import.meta.url));
const transport = args.includes('--stdio')
  ? new StdioClientTransport({ command: process.execPath, args: [fileURLToPath(new URL('../dist/index.js', import.meta.url)), '--stdio'], env: { ANIME_API_URL: api.base.href } })
  : new StreamableHTTPClientTransport(new URL(process.env.ANIME_MCP_URL || 'http://127.0.0.1:3001/mcp'));
const report = { created_at: new Date().toISOString(), transport: args.includes('--stdio') ? 'stdio' : 'streamable_http', client: 'SDK test client; not ChatGPT', web_proxy: web ? 'included' : 'not_checked', model_calls: 0, checks: [] };
const deadline = setTimeout(() => { console.error('Prueba MCP excedió 90 segundos.'); process.exit(1); }, 90000);

try {
  await client.connect(transport);
  const { tools } = await client.listTools();
  assert.equal(tools.length, 6);
  report.tools = tools.map(t => t.name);
  const cases = [
    ['get_dataset_info', {}, undefined],
    ['search_anime', { title: 'Death Note', limit: 5 }, { kind: 'search', order_by: 'title', filters: { title: 'Death Note' }, limit: 5 }],
    ['rank_anime', { filters: { formats: ['tv'], genres: ['Fantasy'], max_episodes: 26 }, limit: 10 }, { kind: 'rank', filters: { formats: ['tv'], genres: ['Fantasy'], max_episodes: 26 }, limit: 10 }],
    ['get_anime_detail', { anime_id: 1535 }, { kind: 'detail', ids: [1535] }],
    ['compare_anime', { anime_ids: [1535, 16498] }, { kind: 'compare', ids: [1535, 16498] }],
    ['aggregate_anime', { group_by: 'year', filters: { formats: ['tv'], year_from: 2020 } }, { kind: 'aggregate', group_by: 'year', filters: { formats: ['tv'], year_from: 2020 } }],
    ['search_anime', { title: 'NoSuchAnimeXYZ123' }, { kind: 'search', order_by: 'title', filters: { title: 'NoSuchAnimeXYZ123' } }],
  ];
  for (const [name, parameters, query] of cases) {
    const response = await client.callTool({ name, arguments: parameters });
    assert.ok(!response.isError, JSON.stringify(response.content));
    const direct = await api.call(query ? '/api/query' : '/api/dataset', query);
    assert.deepEqual(response.structuredContent, direct, `${name}: MCP/API divergen`);
    if (web) assert.deepEqual(await web.call(query ? '/api/query' : '/api/dataset', query), direct, `${name}: web/API divergen`);
    report.checks.push({ name, arguments: parameters, status: 'passed', total: direct.total ?? direct.records,
      applied_query: direct.applied_query, evidence: direct.evidence,
      rows: direct.rows?.map(r => ({ anime_id: r.anime_id, title: r.title, score: r.score, scored_by: r.scored_by })), groups: direct.groups });
  }
  const invalid = await client.callTool({ name: 'rank_anime', arguments: { order_by: 'members' } });
  assert.equal(invalid.isError, true);
  report.checks.push({ name: 'invalid_metric', status: 'passed' });
  const unknown = await client.callTool({ name: 'get_anime_detail', arguments: { anime_id: 2147483647 } });
  assert.equal(unknown.isError, true);
  report.checks.push({ name: 'unknown_id', status: 'passed' });
  report.status = 'passed';
  console.log('OK: descubrimiento y 9 comprobaciones MCP/API; mismos resultados, filtros y evidencia. Sin llamadas al modelo.');
} catch (error) {
  report.status = 'failed';
  report.error = error instanceof Error ? error.message : 'Prueba incompleta';
  console.error('Prueba MCP incompleta:', report.error);
  process.exitCode = 1;
} finally {
  clearTimeout(deadline);
  await client.close();
  const folder = resolve(root, 'docs/evidence/phase9');
  await mkdir(folder, { recursive: true });
  const filename = `smoke-${Date.now()}-${report.transport}.json`;
  await writeFile(resolve(folder, filename), JSON.stringify(report, null, 2));
  console.log(`Evidencia: docs/evidence/phase9/${filename}`);
}
