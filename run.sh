#!/usr/bin/env bash
# Run the Lab 11 analysis.
#
# CENSUS_API_KEY is read from .env if that file exists (it is gitignored), or
# from the environment. With no key the script still runs: it prints
# "Census API fallback: ..." and uses the published 2020 county totals.
set -euo pipefail

cd "$(dirname "$0")"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

exec python3 analysis.py "$@"
