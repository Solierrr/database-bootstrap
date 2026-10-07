#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "uso: load-core-schema.sh <caminho do checkout de database-console>" >&2
  exit 64
fi

core_dir="$1/db/core"

for file in enums.sql schema.sql migrations/V10__technician_review_status.sql; do
  psql --set ON_ERROR_STOP=1 --quiet --file "$core_dir/$file"
done
