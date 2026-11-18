# PostgreSQL backup and restore drill

A backup job can finish successfully and still leave an open question for the on-call engineer. Can a fresh database serve the same rows, with the same values, as the source at the moment of the backup?

This drill starts an isolated PostgreSQL 17 cluster, seeds a job queue, and creates a logical backup. It restores that archive into a new database and exits with an error if any recovery check fails. It uses generated data and needs only Docker.

## Recorded result

On November 18, 2026, GitHub Actions restored all **250 of 250** synthetic jobs. The snapshot and restored database produced the same SHA-256 digest over every row and column.

```text
f400a5443e1c3eb44a087ad7deb752461c58d3ddde230af5bb3339a47c64d4ff
```

The source contained the post-backup marker and the restored copy contained zero. The drill rejected a damaged copy of the archive and detected a one-field change that preserved the row count. Creating the target, restoring the data, and verifying it took **54 ms** in this run on a disposable runner.

[Open the recorded GitHub Actions run](https://github.com/sunmzi4855/devops-cloud-portfolio/actions/runs/44419048693)

## Run the drill

From the repository root, run the following in a Bash-compatible shell.

```bash
docker run --rm -i --network none --user postgres \
  --entrypoint bash postgres:17-bookworm -s < labs/postgres-recovery/drill.sh
```

The first run downloads the official PostgreSQL image. The database process runs as the image's `postgres` user on a private Unix socket. Both databases and all temporary files disappear when the container exits.

## What the drill proves

| Check | How it is tested |
| --- | --- |
| The archive survived transfer | Capture the archive’s SHA-256 digest. Append bytes to a separate copy and require that copy to fail the same check applied before the restore. |
| All snapshot data came back | Export every column of all 250 jobs as CSV ordered by primary key. Compare the source and restored row counts and SHA-256 digests. |
| The backup boundary is visible | Insert job 251 after `pg_dump` finishes. Verify that it exists at the source and is absent in the recovered database. |
| Equal counts can hide a bad restore | Change one value in a transaction on the recovered database. Require a different digest, roll the change back, and recheck the original digest. |
| Restore time has a defined start and end | Start the timer at creation of the empty target database. Stop after the restored count, row digest, and marker checks pass. |

The workflow runs the same command for changes to this lab and publishes its measurements in the GitHub Actions job summary. The image pull and cluster startup are outside the timed interval.

## How to investigate a failed run

- **Archive checksum mismatch.** Retrieve a fresh copy and compare it to the digest recorded at backup time before attempting a restore.
- **Count matches but data digest differs.** Compare the ordered CSV exports by primary key. The drill includes every business column and fixes the sort order so a changed value is visible.
- **Post-backup marker appears in the target.** Check the archive selected and the target connection. Restore into a newly created empty database, then rerun the boundary check.

## Scope

The source and recovered databases live in one disposable cluster. This measures a logical restore of one small dataset. Estimating a production recovery objective would also require representative data, independent backup storage, and a timed service cutover. Recovering writes after this snapshot would require a different recovery strategy, such as continuous WAL archiving and point-in-time recovery.

[Recovery script](drill.sh) · [Workflow definition](../../.github/workflows/postgres-recovery.yml) · [PostgreSQL backup documentation](https://www.postgresql.org/docs/17/app-pgdump.html) · [PostgreSQL restore documentation](https://www.postgresql.org/docs/17/app-pgrestore.html)
