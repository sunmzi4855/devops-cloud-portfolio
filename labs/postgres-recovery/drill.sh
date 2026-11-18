#!/usr/bin/env bash
set -euo pipefail

# Start a disposable cluster on a private Unix socket inside the lab container.
export PATH="$(pg_config --bindir):$PATH"
export LC_ALL=C TZ=UTC PGUSER=postgres PGDATABASE=postgres
lab_dir=$(mktemp -d)
export PGHOST="$lab_dir/socket" PGPORT=5432
mkdir "$PGHOST"
cluster_started=false
cleanup() {
  if [[ $cluster_started == true ]]; then
    pg_ctl -D "$lab_dir/cluster" -m fast -w stop >/dev/null
  fi
  rm -rf -- "$lab_dir"
}
trap cleanup EXIT

initdb -D "$lab_dir/cluster" -U "$PGUSER" --auth-local=trust --auth-host=reject --no-locale >/dev/null
pg_ctl -D "$lab_dir/cluster" -l "$lab_dir/server.log" \
  -o "-k $PGHOST -p $PGPORT -c listen_addresses=''" -w start >/dev/null
cluster_started=true
cd "$lab_dir"

sql() {
  psql -X -qAt --set=ON_ERROR_STOP=1 --dbname="$1" --command="$2"
}
die() {
  printf 'Recovery check failed: %s\n' "$*" >&2
  exit 1
}
file_hash() {
  sha256sum "$1" | cut -d ' ' -f 1
}
# The explicit projection and primary-key order make this CSV deterministic.
export_rows='COPY (SELECT id, queue, status, attempts FROM jobs ORDER BY id) TO STDOUT WITH (FORMAT csv)'
fingerprint() {
  sql "$1" "$export_rows" | sha256sum | cut -d ' ' -f 1
}

createdb source_jobs
psql -X -q --set=ON_ERROR_STOP=1 --dbname=source_jobs <<'SQL'
CREATE TABLE jobs (
  id integer PRIMARY KEY,
  queue text NOT NULL,
  status text NOT NULL CHECK (status IN ('queued', 'running', 'done')),
  attempts integer NOT NULL CHECK (attempts >= 0)
);
INSERT INTO jobs
SELECT n, (ARRAY['ingest', 'export', 'notify'])[1 + n % 3],
       (ARRAY['done', 'queued', 'running'])[1 + n % 3], n % 5
FROM generate_series(1, 250) AS series(n);
SQL

count_query='SELECT count(*) FROM jobs'
marker_query="SELECT count(*) FROM jobs WHERE id = 251 AND queue = 'post-backup'"
expected_rows=$(sql source_jobs "$count_query")
[[ $expected_rows == 250 ]] || die "unexpected number of seed rows"
expected_hash=$(fingerprint source_jobs)
pg_dump --format=custom --file=jobs.dump source_jobs
archive_hash=$(file_hash jobs.dump)

# This write distinguishes a logical backup from the current source database.
sql source_jobs "INSERT INTO jobs VALUES (251, 'post-backup', 'queued', 0)"
source_marker=$(sql source_jobs "$marker_query")
[[ $source_marker == 1 ]] || die "post-backup marker missing at source"

# A damaged archive must fail the same gate used on the real restore.
archive_matches() {
  local actual_hash
  actual_hash=$(file_hash "$1") || return 1
  [[ $actual_hash == "$archive_hash" ]]
}
cp jobs.dump damaged.dump
printf 'simulated transfer damage\n' >> damaged.dump
if archive_matches damaged.dump; then
  die "damaged archive passed the integrity check"
fi
archive_matches jobs.dump || die "backup archive checksum mismatch"

start_ms=$(date +%s%3N)
createdb -T template0 recovered_jobs
pg_restore --exit-on-error --single-transaction --dbname=recovered_jobs jobs.dump
restored_rows=$(sql recovered_jobs "$count_query")
restored_hash=$(fingerprint recovered_jobs)
restored_marker=$(sql recovered_jobs "$marker_query")
[[ $restored_rows == "$expected_rows" ]] || die "row count changed"
[[ $restored_hash == "$expected_hash" ]] || die "row contents changed"
[[ $restored_marker == 0 ]] || die "a post-backup write appeared in the restore"
elapsed_ms=$(( $(date +%s%3N) - start_ms ))

# Keep the row count fixed and change one value inside a rolled-back transaction.
# The data check must catch what a row-count-only check would miss.
altered_hash=$(sql recovered_jobs "BEGIN; UPDATE jobs SET attempts = attempts + 1 WHERE id = 1; $export_rows; ROLLBACK;" | sha256sum | cut -d ' ' -f 1)
[[ $altered_hash != "$expected_hash" ]] || die "one changed value went undetected"
final_hash=$(fingerprint recovered_jobs)
[[ $final_hash == "$expected_hash" ]] || die "the negative control changed the recovered database"

cat <<REPORT
## PostgreSQL recovery drill

| Check | Observed result |
| --- | --- |
| Snapshot rows / restored rows | $expected_rows / $restored_rows |
| Snapshot data SHA-256 | `$expected_hash` |
| Restored data SHA-256 | `$restored_hash` |
| Post-backup marker in source / restore | $source_marker / $restored_marker |
| Damaged archive | Rejected before restore |
| Single changed value, same row count | Detected and rolled back |
| Create target, restore, and verify | $elapsed_ms ms |

PostgreSQL $(sql source_jobs "SHOW server_version") in a disposable local cluster.
REPORT
