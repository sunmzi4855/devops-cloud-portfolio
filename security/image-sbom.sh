#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: bash security/image-sbom.sh LOCAL_IMAGE OUTPUT_DIRECTORY" >&2
  exit 2
fi

output_dir=$2
work_dir=$(mktemp -d)
trap 'rm -rf -- "$work_dir"' EXIT

docker image inspect "$1" > "$work_dir/inspect.json"
image_id=$(jq -er '.[0].Id' "$work_dir/inspect.json")
revision=$(jq -r '.[0].Config.Labels["org.opencontainers.image.revision"] // "unlabeled"' "$work_dir/inspect.json")
docker image save --output "$work_dir/image.tar" "$image_id"
"${SYFT_CMD:-syft}" scan "docker-archive:$work_dir/image.tar" \
  --source-name cloud-devops-demo --output "spdx-json=$work_dir/image.spdx.json"

# The Debian-based runtime includes dpkg. Its presence checks that OS packages were cataloged.
package_count=$(jq -er '
  if .spdxVersion == "SPDX-2.3" and
     any(.packages[]?; .name == "dpkg" and ((.versionInfo // "") | length) > 0)
  then (.packages | length)
  else error("Expected an SPDX 2.3 inventory containing a versioned dpkg package")
  end
' "$work_dir/image.spdx.json")

printf 'Image ID: %s\nSource revision: %s\nSPDX package entries: %s\n' \
  "$image_id" "$revision" "$package_count" > "$work_dir/build-info.txt"
(cd "$work_dir" && sha256sum image.spdx.json build-info.txt > SHA256SUMS)
mkdir -p -- "$output_dir"
cp -- "$work_dir"/{image.spdx.json,build-info.txt,SHA256SUMS} "$output_dir/"
cat "$output_dir/build-info.txt"
