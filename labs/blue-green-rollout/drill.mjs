import assert from 'node:assert/strict';
import { startRouter } from './router.mjs';
import { startQuoteService } from './service.mjs';

const scenarios = [
  { name: 'Healthy candidate', fixture: {}, decision: 'promoted', passed: 5, attempted: 5 },
  { name: 'Readiness failure', fixture: { ready: false }, decision: 'held', passed: 0, attempted: 0 },
  {
    name: 'Third quote returns 503',
    fixture: { quote: count => count === 3 ? { status: 503 } : {} },
    decision: 'rolled back', passed: 2, attempted: 3,
  },
  {
    name: 'HTTP 200 with the wrong price',
    fixture: { quote: () => ({ totalCents: 250 }) },
    decision: 'rolled back', passed: 0, attempted: 1,
  },
];

console.log('# Blue-green rollout drill\n');
console.log('| Scenario | Decision | Green quotes passed / attempted | Final route | Observation |');
console.log('| --- | --- | --- | --- | --- |');
for (const scenario of scenarios) {
  const running = [];
  try {
    const blue = await startQuoteService('blue');
    running.push(blue);
    const green = await startQuoteService('green', scenario.fixture);
    running.push(green);
    const router = await startRouter(blue);
    running.push(router);

    const result = await router.deploy(green);
    assert.equal(result.decision, scenario.decision, scenario.name);
    assert.equal(result.passed, scenario.passed, scenario.name);
    assert.equal(result.attempted, scenario.attempted, scenario.name);

    // Read back the public route independently of the controller's decision.
    const response = await fetch(router.url + '/quote', { signal: AbortSignal.timeout(4000) });
    assert.equal(response.status, 200);
    const finalQuote = await response.json();
    const expectedRelease = scenario.decision === 'promoted' ? 'green' : 'blue';
    assert.deepEqual(finalQuote, { release: expectedRelease, quantity: 2, currency: 'USD', totalCents: 2500 });
    console.log(`| ${scenario.name} | ${result.decision} | ${result.passed}/${result.attempted} | ${finalQuote.release} | ${result.reason} |`);
  } finally {
    await Promise.all(running.map(service => service.close()));
  }
}
