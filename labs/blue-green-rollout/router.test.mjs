import assert from 'node:assert/strict';
import test from 'node:test';
import { startRouter } from './router.mjs';
import { startQuoteService } from './service.mjs';

async function startLab(t, blueOptions = {}, greenOptions = {}) {
  const blue = await startQuoteService('blue', blueOptions);
  t.after(blue.close);
  const green = await startQuoteService('green', greenOptions);
  t.after(green.close);
  const router = await startRouter(blue);
  t.after(router.close);
  return { router, green };
}

async function routedQuote(router) {
  const response = await fetch(router.url + '/quote', { signal: AbortSignal.timeout(4000) });
  return { status: response.status, body: await response.json() };
}

// An explicit barrier makes the overlap deterministic without sleeps.
function pauseFirstQuote() {
  const arrived = Promise.withResolvers();
  const resume = Promise.withResolvers();
  return {
    arrived: arrived.promise,
    resume: resume.resolve,
    quote: async count => {
      if (count === 1) {
        arrived.resolve();
        await resume.promise;
      }
      return {};
    },
  };
}

test('an in-flight request finishes on blue while a new request reaches green', async t => {
  const pause = pauseFirstQuote();
  const { router, green } = await startLab(t, { quote: pause.quote });
  const inFlight = routedQuote(router);
  try {
    await Promise.race([pause.arrived, inFlight.then(() => assert.fail('Blue failed to hold the request'))]);
    assert.equal((await router.deploy(green)).decision, 'promoted');
    assert.equal((await routedQuote(router)).body.release, 'green');
  } finally {
    pause.resume();
  }
  const original = await inFlight;
  assert.equal(original.status, 200);
  assert.equal(original.body.release, 'blue');
});

test('overlapping deploy calls cannot change the route mid-rollout', async t => {
  const pause = pauseFirstQuote();
  const { router, green } = await startLab(t, {}, { quote: pause.quote });
  const rolling = router.deploy(green);
  try {
    await Promise.race([pause.arrived, rolling.then(() => assert.fail('Green failed to hold the first probe'))]);
    await assert.rejects(router.deploy(green), /already in progress/);
  } finally {
    pause.resume();
  }
  assert.equal((await rolling).decision, 'promoted');
});

test('a failed rollback verification surfaces both failures', async t => {
  const { router, green } = await startLab(t,
    { quote: count => count === 1 ? {} : { status: 503 } },
    { quote: () => ({ totalCents: 250 }) });
  await assert.rejects(router.deploy(green), /Rollback to blue could not be verified.*503.*incorrect quote/);
  const current = await routedQuote(router);
  assert.equal(current.status, 503);
  assert.equal(current.body.release, 'blue');
});

test('an unhealthy baseline stops the rollout before cutover', async t => {
  const { router, green } = await startLab(t, { quote: () => ({ status: 503 }) });
  await assert.rejects(router.deploy(green), /503/);
  assert.equal((await routedQuote(router)).body.release, 'blue');
});

test('a readiness response from the wrong release holds the current route', async t => {
  const { router, green } = await startLab(t);
  const result = await router.deploy({ ...green, release: 'another-build' });
  assert.equal(result.decision, 'held');
  assert.equal(result.attempted, 0);
  assert.match(result.reason, /expected release another-build, received green/);
  assert.equal((await routedQuote(router)).body.release, 'blue');
});

test('a repaired candidate can be retried after a verified rollback', async t => {
  let broken = true;
  const { router, green } = await startLab(t, {}, {
    quote: () => broken ? { totalCents: 250 } : {},
  });
  assert.equal((await router.deploy(green)).decision, 'rolled back');
  assert.equal((await routedQuote(router)).body.release, 'blue');
  broken = false;
  assert.equal((await router.deploy(green)).decision, 'promoted');
  assert.equal((await routedQuote(router)).body.release, 'green');
});
