import { listenLocal } from './router.mjs';

// Two items at 1250 cents each. A scenario can change one response on purpose.
export async function startQuoteService(release, { ready = true, quote = () => ({}) } = {}) {
  let count = 0;
  const service = await listenLocal(async (request, response) => {
    if (request.url === '/ready') {
      response.writeHead(ready ? 200 : 503, { 'content-type': 'application/json' });
      response.end(JSON.stringify({ release, ready }));
      return;
    }
    if (request.url !== '/quote') {
      response.writeHead(404).end();
      return;
    }
    try {
      const { status = 200, totalCents = 2 * 1250 } = await quote(++count);
      const body = status === 200
        ? { release, quantity: 2, currency: 'USD', totalCents }
        : { release, error: 'Quote unavailable' };
      response.writeHead(status, { 'content-type': 'application/json' }).end(JSON.stringify(body));
    } catch {
      response.writeHead(500).end();
    }
  });
  return { ...service, release };
}
