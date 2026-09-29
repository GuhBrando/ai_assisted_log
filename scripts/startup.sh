#!/usr/bin/env bash
# Sobe a API de Logs, o MongoDB e o Swagger UI do contrato com Docker Compose e espera tudo ficar no ar.
#
# Uso:   scripts/startup.sh
# Parar: docker compose down        (mantém os dados do MongoDB)
#        docker compose down -v     (apaga também o volume do MongoDB)
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker não encontrado. Instale o Docker e tente de novo." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "O daemon do Docker não está rodando. Inicie o Docker e tente de novo." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Criado .env a partir de .env.example."
fi

if ! grep -qE '^JWT_SECRET=[^[:space:]]+' .env; then
  secret=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
  grep -v '^JWT_SECRET=' .env > .env.tmp || true
  echo "JWT_SECRET=$secret" >> .env.tmp
  mv .env.tmp .env
  echo "Gerado um JWT_SECRET novo no .env."
fi

docker compose up -d --build --wait
docker compose ps

api_address=$(docker compose port api 8000)
swagger_address=$(docker compose port swagger 8080)
echo
echo "API:       http://$api_address"
echo "Swagger:   http://$api_address/docs"
echo "Health:    http://$api_address/health"
echo "Contrato:  http://$swagger_address"
