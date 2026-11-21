import { once } from 'node:events';
import { createServer } from 'node:http';

const quoteChecks = 5;
const upstreamTimeoutMs = 2_000;

export async function listenLocal(handler) {
  const server = createServer(handler);
  const ready = once(server, 'listening');
  server.listen(0, '127.0.0.1');
  await ready;
  return {
    url: `http://127.0.0.1:${server.address().port}`,
    close: () => new Promise((resolve, reject) => {
      server.close(error => error ? reject(error) : resolve());
    }),
  };
}

async function readJson(url, path, release) {
  const response = await fetch(url + path, {
    redirect: 'error',
    signal: AbortSignal.timeout(upstreamTimeoutMs * 2),
  });
  if (response.status !== 200) {
    await response.body?.cancel();
    throw new Error(`${path} returned HTTP ${response.status}`);
  }
  const body = await response.json();
  if (body?.release !== release) {
    throw new Error(`${path} expected release ${release}, received ${body?.release}`);
  }
  return body;
}

async function verifyQuote(url, release) {
  const quote = await readJson(url, '/quote', release);
  if (quote.quantity !== 2 || quote.currency !== 'USD' || quote.totalCents !== 2500) {
    throw new Error(
      `HTTP 200 with an incorrect quote (${quote.quantity} items, ${quote.totalCents} cents, ${quote.currency}). Expected 2 items, 2500 cents, USD`,
    );
  }
}

export async function startRouter(initial) {
  let active = initial;
  let deploying = false;

  const listener = await listenLocal(async (request, response) => {
    if (request.method !== 'GET' || !['/quote', '/ready'].includes(request.url)) {
      response.writeHead(404).end();
      return;
    }
    // Each request keeps the upstream selected when it arrived.
    const target = active;
    try {
      const upstream = await fetch(target.url + request.url, {
        redirect: 'error',
        signal: AbortSignal.timeout(upstreamTimeoutMs),
      });
      const body = await upstream.text();
      response.writeHead(upstream.status, { 'content-type': 'application/json' }).end(body);
    } catch {
      response.writeHead(502, { 'content-type': 'application/json' }).end('{"error":"upstream unavailable"}');
    }
  });

  async function deploy(candidate) {
    if (deploying) throw new Error('A rollout is already in progress');
    deploying = true;
    const previous = active;
    try {
      await verifyQuote(listener.url, previous.release);
      try {
        const readiness = await readJson(candidate.url, '/ready', candidate.release);
        if (readiness.ready !== true) throw new Error('Candidate reported ready=false');
      } catch (error) {
        return { decision: 'held', passed: 0, attempted: 0, reason: error.message };
      }

      active = candidate;
      let passed = 0;
      try {
        for (; passed < quoteChecks; passed++) {
          await verifyQuote(listener.url, candidate.release);
        }
      } catch (error) {
        active = previous;
        try {
          await verifyQuote(listener.url, previous.release);
        } catch (recoveryError) {
          throw new Error(`Rollback to ${previous.release} could not be verified: ${recoveryError.message}. Original failure: ${error.message}`);
        }
        return { decision: 'rolled back', passed, attempted: passed + 1, reason: error.message };
      }
      return { decision: 'promoted', passed, attempted: passed, reason: `All ${passed} routed quotes matched` };
    } finally {
      deploying = false;
    }
  }

  return { ...listener, deploy };
}
