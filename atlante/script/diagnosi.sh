#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
#
# Diagnosi di Atlante in un comando (docs/regole/controllo-e-diagnosi.md, punto 2):
# tutti i pezzi, lo spazio sul disco, gli errori e le richieste lente delle ultime 24 ore.
# Si lancia quando qualcosa non va e nel controllo del lunedì. Resoconto in atlante/locale/diagnosi/.
cd "$(dirname "$0")/../.."
# Docker Desktop puts its commands here; a shell opened before Docker may not know it.
PATH="$PATH:$HOME/.docker/bin:/Applications/Docker.app/Contents/Resources/bin"
export PATH
exec python3 -I atlante/script/diagnosi.py "$@"
