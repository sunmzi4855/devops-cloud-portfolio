# Terraform state migration for two PostgreSQL databases

The `orders` and `audit` databases start at numbered Terraform addresses. Naming them by workload makes the configuration easier to change, but a plain rename produces a plan to delete both databases and create two new ones. This lab rehearses the refactor against a live PostgreSQL container with 240 synthetic orders and 80 audit entries.

## Recorded result

Both databases retained their PostgreSQL OIDs and the full SHA-256 digests of their sorted rows. The second plan reported zero changes. The OIDs below are specific to this run. [View the verified run and download the JSON evidence](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/45721578199)

| Database | OID before and after | Rows before and after | SHA-256 prefix |
| --- | ---: | ---: | --- |
| Orders | 16385 | 240 | `b3af084bc9df` |
| Audit | 16384 | 80 | `1d7a8d0c18b8` |

## Plans under review

| Configuration | Plan | Decision |
| --- | --- | --- |
| Replace the numbered addresses with names | Two creates and two deletes | Reject before apply |
| Supply both address moves and change the orders connection limit | An in-place update is bundled into the migration | Reject before apply |
| Supply only the two reviewed moves | Both objects move in state with zero resource writes | Apply the reviewed plan file |

The Python guard reads the saved plan's JSON and compares each old and new address with an independently specified map. Every resource action must be a no-op. The guard also checks for imports, deferred changes, drift and output changes. It runs before the migration is applied. [Review the guard](plan_guard.py) · [Expected moves](expected-moves.json) · [Terraform moved blocks](config/after/moves.tf)

## How to verify the result

The Terraform provider identifies these databases by name. A new database can reuse an old name, so the drill also asks PostgreSQL for the catalog object ID (OID) of each database. It records each OID, connection limit, row count and SHA-256 digest of the ordered rows before the move and again afterward. Success also requires exactly the two new addresses in state and exit code `0` from a fresh `terraform plan -detailed-exitcode`.

## Run the lab

Use Terraform 1.12.2, Python 3.10 or newer, and a local Docker engine. Start in the repository root.

```sh
cd labs/terraform-state-migration
python3 -m unittest -v
python3 drill.py --evidence state-migration.json
```

The drill creates a temporary working directory for Terraform's local state and saved plans. It starts PostgreSQL 17 on a random loopback port and uses a fresh password for that run. It removes the container and working directory afterward. The evidence file contains the observed database identifiers, row counts, hashes, addresses and plan decisions.

The new configuration retains the `moved` blocks so an existing state that still uses the numbered addresses can follow the same migration. [Terraform's refactoring guide](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring)

[Run script](drill.py) · [Before configuration](config/before/databases.tf) · [After configuration](config/after/databases.tf) · [GitHub Actions workflow](../../.github/workflows/terraform-state-migration.yml)
