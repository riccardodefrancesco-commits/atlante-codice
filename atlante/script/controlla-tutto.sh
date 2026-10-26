#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
#
# Every check, before saving a piece or an update from Plane:
#   1. no passwords or keys in our saves (atlante/script/controllo-segreti.py, with Gitleaks)
#   2. no new known problems in the libraries (atlante/script/controllo-librerie.py, with OSV-Scanner)
#   3. the brand is applied and "Plane" is not visible (atlante/script/marchio.py --verifica), and the
#      Italian texts use the glossary's words (atlante/script/italiano.py --verifica)
#   4. the type check of ALL packages (not only the ones touched: the public pages broke once)
#   5. the tests of our interface code
#   6. all the server tests, Plane's and ours, in a clean test setup
# It stops at the first failure.
set -e
cd "$(dirname "$0")/../.."

echo "1/6 Ricerca di password e chiavi"
python3 -I atlante/script/controllo-segreti.py --tutto

echo "2/6 Controllo delle librerie"
python3 -I atlante/script/controllo-librerie.py

echo "3/6 Marchio e glossario"
python3 -I atlante/script/marchio.py --verifica
python3 -I atlante/script/italiano.py --verifica

echo "4/6 Controllo dei tipi di tutti i pacchetti"
pnpm turbo run check:types --output-logs=errors-only

echo "5/6 Test dell'interfaccia"
sh atlante/script/test-interfaccia.sh --reporter=dot

echo "6/6 Test del server (Plane e Atlante)"
# --build: if the server's libraries changed (apps/api/uv.lock), the tests run with the new ones.
docker compose -p atlante-test -f docker-compose-test.yml run --build --rm api-tests pytest -p no:cacheprovider -q
docker compose -p atlante-test -f docker-compose-test.yml down -v

echo "Tutti i controlli sono passati."
