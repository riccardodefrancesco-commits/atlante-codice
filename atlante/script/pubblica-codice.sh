#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# The code of one version of Atlante in the public repository, for the AGPL license (decision of 21 October,
# zeta3-progetti#25): the working repository stays private; "Informazioni su Atlante" points to the public one.
#
# A clean copy of the saved commit: no history of the working repository, no local files, no working notes.
# Before anything leaves the Mac: Gitleaks and the secrets of this Mac (controllo-segreti.py --cartella),
# no address at zeta3.it, no file of the local folders.
#
#   sh atlante/script/pubblica-codice.sh 0.3.0-alfa              # only the checks: nothing leaves the Mac
#   sh atlante/script/pubblica-codice.sh 0.3.0-alfa --pubblica   # the checks, then the publication

set -eu
cd "$(git rev-parse --show-toplevel)"

VERSIONE=${1:?"Indica la versione, per esempio 0.3.0-alfa"}
PUBBLICA=${2:-}
PUBBLICO=riccardodefrancesco-commits/atlante-codice
# Working notes and screenshots: not part of the program, they stay in the private repository.
FUORI="CLAUDE.md atlante/immagini atlante/locale"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
	echo "Ci sono modifiche non salvate: si pubblica solo codice salvato in git."
	exit 1
fi
COMMIT=$(git rev-parse --short HEAD)
LAVORO=$(mktemp -d)
trap 'rm -rf "$LAVORO"' EXIT
mkdir "$LAVORO/codice"
git archive HEAD | tar -x -C "$LAVORO/codice"
for percorso in $FUORI; do rm -rf "${LAVORO:?}/codice/$percorso"; done

echo "Controlli sulla copia di Atlante $VERSIONE ($COMMIT):"
python3 -I atlante/script/controllo-segreti.py --cartella "$LAVORO/codice"
INDIRIZZI=$(grep -rIl -E '[A-Za-z0-9._%+-]+@zeta3\.it' "$LAVORO/codice" | sed "s|$LAVORO/codice/||" || true)
if [ -n "$INDIRIZZI" ]; then
	echo "Indirizzi email di Zeta3 in: $INDIRIZZI"
	exit 1
fi
echo "Nessun indirizzo email di Zeta3; fuori dalla copia: $FUORI."
[ -f "$LAVORO/codice/LICENSE.txt" ] && [ -f "$LAVORO/codice/COPYRIGHT.txt" ] || { echo "Mancano LICENSE.txt o COPYRIGHT.txt."; exit 1; }
echo "Licenza AGPL e note di Plane presenti."

if [ "$PUBBLICA" != "--pubblica" ]; then
	echo "Solo controlli: non ho pubblicato niente. Per pubblicare: aggiungi --pubblica."
	exit 0
fi

if ! gh repo view "$PUBBLICO" >/dev/null 2>&1; then
	gh repo create "$PUBBLICO" --public \
		--description "Codice sorgente di Atlante, programma interno di Zeta3 basato su Plane (AGPL-3.0)"
fi
gh repo clone "$PUBBLICO" "$LAVORO/pubblico" -- --quiet 2>/dev/null || mkdir -p "$LAVORO/pubblico"
cd "$LAVORO/pubblico"
[ -d .git ] || { git init --quiet -b main && git remote add origin "https://github.com/$PUBBLICO.git"; }
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$LAVORO/codice/." .
git add -A
git commit --quiet -m "Atlante $VERSIONE ($COMMIT)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git tag "v$VERSIONE"
git push --quiet origin main "v$VERSIONE"
echo "Pubblicato: https://github.com/$PUBBLICO, versione $VERSIONE ($COMMIT)."
