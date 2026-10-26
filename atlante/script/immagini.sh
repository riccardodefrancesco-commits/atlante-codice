#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
#
# Immagini delle schermate di Atlante, con un browser senza finestra (atlante/immagini/schermate.mjs).
# Esempio: sh atlante/script/immagini.sh --nome prima-12 --persona bruno --schermate clienti,nuovo-cliente
# Le immagini vanno in atlante/locale/immagini/<nome>/, escluse da git.
cd "$(dirname "$0")/../.."
if [ ! -d atlante/immagini/node_modules/playwright ]; then
  echo "Prima volta: installo Playwright nella sua cartella (atlante/immagini)."
  (cd atlante/immagini && npm ci --no-audit --no-fund --ignore-scripts && npx --no-install playwright install chromium-headless-shell) || exit 1
fi
exec node atlante/immagini/schermate.mjs "$@"
