#!/usr/bin/env sh

cd "$(dirname "$0")" || exit

docker run --rm \
    -v "${PWD}":/usr/src/app:z,cached \
    -w /usr/src/app \
    ghcr.io/astral-sh/ruff:0.1.13 \
    "$@"
exit $?
