import { test } from 'node:test';
import assert from 'node:assert/strict';
import { POST } from '../src/app/api/artwork/route.ts';

const call = ids => POST(new Request('http://localhost/api/artwork', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids }) }));
const fixture = id => ({ id: 888000 + id, idMal: id, siteUrl: `https://anilist.co/anime/${888000 + id}`, coverImage: { extraLarge: `https://s4.anilist.co/test/${id}.jpg` }, bannerImage: null });

test('rejects invalid or excessive IDs before contacting upstream', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = () => { throw new Error('must not contact upstream'); };
  try {
    for (const ids of [[], [-1], ['1535'], Array.from({ length: 21 }, (_,i) => i+1)]) assert.equal((await call(ids)).status, 422);
  } finally { globalThis.fetch = original; }
});

test('joins artwork by exact MAL ID and caches resolved metadata', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (url, options) => {
    calls++;
    assert.equal(url, 'https://graphql.anilist.co');
    const query = JSON.parse(options.body).query;
    assert.ok(query.includes('idMal: 1535'));
    assert.ok(!query.includes('averageScore'));
    return Response.json({ data: { anime1535: fixture(1535) } });
  };
  try {
    const response = await call([1535]);
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.images['1535'].cover, 'https://s4.anilist.co/test/1535.jpg');
    await call([1535]);
    assert.equal(calls, 1);
  } finally { globalThis.fetch = original; }
});

test('never attaches an image returned for another MAL ID', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ data: { anime999001: fixture(777001) } });
  try { assert.deepEqual((await (await call([999001])).json()).images, {}); }
  finally { globalThis.fetch = original; }
});

test('upstream outage is a controlled error; arbitrary image hosts are discarded', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('', { status: 429 });
    assert.equal((await call([999002])).status, 503);
    globalThis.fetch = async () => Response.json({ data: { anime999003: { ...fixture(999003), coverImage: { extraLarge: 'https://other.invalid/poster.jpg' } } } });
    assert.deepEqual((await (await call([999003])).json()).images, {});
  } finally { globalThis.fetch = original; }
});
