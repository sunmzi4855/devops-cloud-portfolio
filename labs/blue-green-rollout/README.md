# Blue-green deployment with automatic rollback

A new version of a pricing service passes readiness and returns HTTP 200. Then it quotes **$2.50 for a $25.00 order**. Can the deployment catch the error, send the next request back to the old version, and verify the recovery?

This lab runs two versions of a quote API behind one HTTP endpoint. Blue starts as the active release. A rollout controller checks green, switches the route, and reads back a known two-item quote through the same endpoint a customer would use. The HTTP servers listen on separate loopback ports and run in one Node.js process.

## Run it

Use Node.js 22 or newer. Run the following from the repository root.

```sh
cd labs/blue-green-rollout
node drill.mjs
node --test router.test.mjs
```

Both commands use only Node’s standard library. Each run starts fresh servers on available ports and closes them when it finishes. The drill verifies its results and exits with an error if a decision or the final quote differs from expectations.

## Reproduced outcomes

| Green candidate | What the controller saw through the route | Decision | Who served the final $25.00 quote? |
| --- | --- | --- | --- |
| Healthy | All five quotes had the expected release, quantity, currency and total | Promote | Green |
| Not ready | Green returned 503 to the direct readiness check, so it received zero routed quotes | Hold | Blue |
| Intermittent error | The first two quotes passed. The third returned 503 | Roll back | Blue |
| Incorrect price | The first quote returned HTTP 200 with a total of 250 cents. The expected total was 2,500 cents | Roll back | Blue |

## How the switch works

1. Verify the current release through the shared endpoint and check the candidate’s own `/ready` response.
2. Switch the active upstream. Each request keeps the upstream it received when it arrived.
3. Read five quotes through the shared endpoint. For two items at $12.50 each, check the release identifier, quantity, currency and total in integer cents.
4. On the first failure, restore the previous upstream and read another quote through the shared endpoint. If recovery also fails, surface both failures.

The tests hold a request open on blue, promote green, and check that a new request reaches green before the original request finishes on blue. They also exercise concurrent rollout attempts, an unhealthy baseline, a mismatched release identifier, failed recovery verification and a successful retry after repair.

## Scope

This is a local deployment simulation with synthetic orders and an in-memory route. A failed candidate can serve incorrect quotes between cutover and rollback. The five probes cover one known transaction. For a multi-instance deployment, route changes and rollout ownership would need to survive process restarts.

[Rollout controller](router.mjs) · [Quote service](service.mjs) · [Executable drill](drill.mjs) · [Integration tests](router.test.mjs) · [GitHub Actions workflow](../../.github/workflows/blue-green-rollout.yml)
