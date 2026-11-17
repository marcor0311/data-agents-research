import test from 'node:test';
import assert from 'node:assert/strict';
import { Client, StreamableHTTPClientTransport } from '@modelcontextprotocol/client';
import { createMcpHandler } from '@modelcontextprotocol/server';
import { CatalogApi } from '../dist/api.js';
import { createCatalogServer } from '../dist/server.js';
import { createHttpServer } from '../dist/http.js';

const result = {
  contract_version: '1.0', status: 'result', kind: 'rank', applied_query: {}, total: 1,
  matched_total: 1, omitted_missing_metric: 0, rows: [{ anime_id: 1535, score: 8.62 }], groups: [],
  evidence: { load_id: 'fixture', selected_ids: [1535], shown_ids: [1535], query_sha256: 'fixture' }, definitions: {},
};

async function session(t, api) {
  const handler = createMcpHandler(() => createCatalogServer(api), { responseMode: 'json' });
  const client = new Client({ name: 'phase9-tests', version: '1.0.0' });
  const transport = new StreamableHTTPClientTransport(new URL('http://localhost/mcp'), {
    fetch: (url, init) => handler.fetch(new Request(url, init)),
  });
  t.after(async () => { await client.close(); await handler.close(); });
  await client.connect(transport);
  return client;
}

test('MCP discovery advertises six read-only tools with input/output schemas', async t => {
  const client = await session(t, { call: () => { throw new Error('Discovery must not call Python'); } });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map(x => x.name).sort(), ['aggregate_anime', 'compare_anime', 'get_anime_detail', 'get_dataset_info', 'rank_anime', 'search_anime']);
  for (const tool of tools) {
    assert.equal(tool.annotations.readOnlyHint, true);
    assert.equal(tool.annotations.destructiveHint, false);
    assert.ok(tool.inputSchema);
    assert.ok(tool.outputSchema);
  }
});

test('ranking returns Python result and evidence unchanged, without adding a vote floor', async t => {
  let received;
  const client = await session(t, { call: async (path, query) => { received = { path, query }; return result; } });
  const response = await client.callTool({ name: 'rank_anime', arguments: { filters: { genres: ['Fantasy'], formats: ['tv'], max_episodes: 26 }, limit: 10 } });
  assert.equal(response.isError, undefined);
  assert.deepEqual(response.structuredContent, result);
  assert.deepEqual(JSON.parse(response.content[0].text), result);
  assert.equal(received.path, '/api/query');
  assert.equal(received.query.kind, 'rank');
  assert.equal(received.query.filters.min_votes, undefined);
});

test('strict schemas reject unsupported fields, disabled metrics, duplicate IDs and oversized lists before API calls', async t => {
  let calls = 0;
  const client = await session(t, { call: async () => { calls++; return result; } });
  const invalid = [
    ['rank_anime', { order_by: 'members' }],
    ['rank_anime', { limit: 101 }],
    ['rank_anime', { filters: { genres: Array(11).fill('Fantasy') } }],
    ['rank_anime', { url: 'http://evil.example' }],
    ['compare_anime', { anime_ids: [1535, 1535] }],
    ['get_anime_detail', { anime_id: -1 }],
  ];
  for (const [name, args] of invalid) assert.equal((await client.callTool({ name, arguments: args })).isError, true);
  assert.equal(calls, 0);
});

test('tool calls are stateless and delegate search, detail, compare and aggregation', async t => {
  const calls = [];
  const client = await session(t, { call: async (path, q) => { calls.push(q); return result; } });
  await client.callTool({ name: 'search_anime', arguments: { title: 'Death Note', filters: { formats: ['tv'] } } });
  await client.callTool({ name: 'get_anime_detail', arguments: { anime_id: 1535 } });
  await client.callTool({ name: 'compare_anime', arguments: { anime_ids: [1535, 16498] } });
  await client.callTool({ name: 'aggregate_anime', arguments: { group_by: 'year', filters: { year_from: 2020 } } });
  assert.equal(calls[0].filters.title, 'Death Note');
  assert.equal(calls[0].filters.formats[0], 'tv');
  assert.deepEqual(calls[1], { kind: 'detail', ids: [1535] });
  assert.deepEqual(calls[2], { kind: 'compare', ids: [1535, 16498] });
  assert.deepEqual(calls[3], { kind: 'aggregate', group_by: 'year', filters: { year_from: 2020 } });
});

test('dataset metadata is read from Python, not invented by the MCP', async t => {
  const meta = { load_id: 'fixture', records: 1, formats: ['tv'], genres: ['Fantasy'], studios: [], statuses: [], disabled_metrics: ['members'], definitions: {} };
  const client = await session(t, { call: async path => { assert.equal(path, '/api/dataset'); return meta; } });
  assert.deepEqual((await client.callTool({ name: 'get_dataset_info', arguments: {} })).structuredContent, meta);
});

test('upstream rejection and connection failure become readable errors without leaking bodies', async t => {
  for (const status of [422, 503]) {
    const api = new CatalogApi('http://127.0.0.1:8000', 1000, async () => new Response('sk-secret-provider-body', { status }));
    const client = await session(t, api);
    const response = await client.callTool({ name: 'rank_anime', arguments: {} });
    assert.equal(response.isError, true);
    assert.doesNotMatch(JSON.stringify(response), /sk-secret/);
  }
  const client = await session(t, new CatalogApi(undefined, 1000, async () => { throw new Error('secret network detail'); }));
  const response = await client.callTool({ name: 'rank_anime', arguments: {} });
  assert.equal(response.isError, true);
  assert.doesNotMatch(JSON.stringify(response), /secret network/);
});

test('timeout and malformed response are controlled failures', async t => {
  const cases = [
    async () => { throw new DOMException('private detail', 'TimeoutError'); },
    async () => new Response('not-json'),
    async () => new Response(JSON.stringify({ wrong_contract: true })),
  ];
  for (const request of cases) {
    const client = await session(t, new CatalogApi(undefined, 1000, request));
    assert.equal((await client.callTool({ name: 'rank_anime', arguments: {} })).isError, true);
  }
});

test('API URL is operator configuration and redirects are forbidden; response size is bounded', async () => {
  for (const url of ['file:///etc/passwd', 'http://user:secret@localhost', 'http://localhost/elsewhere']) {
    assert.throws(() => new CatalogApi(url));
  }
  const api = new CatalogApi(undefined, 1000, async (url, options) => {
    assert.equal(options.redirect, 'error');
    assert.equal(url.pathname, '/api/query');
    assert.equal(options.method, 'POST');
    return new Response(' '.repeat(2 * 1024 * 1024 + 1));
  });
  await assert.rejects(api.call('/api/query', {}), /2 MiB/);
});

test('loopback HTTP guards reject an unrelated Host or Origin before processing', () => {
  const http = createHttpServer({ call: () => { throw new Error('Must not run'); } });
  for (const headers of [{ host: 'evil.example' }, { host: '127.0.0.1:3001', origin: 'https://evil.example' }]) {
    let status;
    const res = { writeHead: value => { status = value; }, end: () => {} };
    http.emit('request', { headers, method: 'POST', url: '/mcp' }, res);
    assert.equal(status, 403);
  }
  http.close();
});

test('legacy 2025 MCP initialize, discovery and call remain supported', async t => {
  const handler = createMcpHandler(() => createCatalogServer({ call: async () => result }));
  t.after(() => handler.close());
  const send = async (method, params, id) => {
    const response = await handler.fetch(new Request('http://localhost/mcp', {
      method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-06-18' },
      body: JSON.stringify({ jsonrpc: '2.0', id, method, params }),
    }));
    const text = await response.text();
    const json = text.startsWith('event:') || text.startsWith('data:') ? JSON.parse(text.split('\n').find(x => x.startsWith('data:')).slice(5)) : JSON.parse(text);
    return json.result;
  };
  const initialized = await send('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'legacy-test', version: '1' } }, 1);
  assert.equal(initialized.protocolVersion, '2025-06-18');
  assert.equal((await send('tools/list', {}, 2)).tools.length, 6);
  assert.deepEqual((await send('tools/call', { name: 'rank_anime', arguments: {} }, 3)).structuredContent, result);
});
