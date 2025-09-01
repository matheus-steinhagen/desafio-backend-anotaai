#!/usr/bin/env bash
set -euo pipefail
echo ">> reset localstack: removendo diretório de dados localstack/"
rm -rf localstack || true
echo ">> pronto."