#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
#
# Mette le immagini di una cartella di atlante/locale/immagini/ nel ramo "immagini" di GitHub,
# separato dal codice, e stampa i link da incollare nella richiesta di unione (prima e dopo).
# Esempio: sh atlante/script/pubblica-immagini.sh prima-12 dopo-12
# Solo immagini con dati inventati.
set -e
cd "$(dirname "$0")/../.."
[ $# -gt 0 ] || { echo "Uso: sh atlante/script/pubblica-immagini.sh <cartella> [<cartella>...]"; exit 1; }
REPO=riccardodefrancesco-commits/atlante
BRANCH=$(git rev-parse --abbrev-ref HEAD)
TREE=atlante/locale/ramo-immagini
if [ ! -d "$TREE" ]; then
  if git ls-remote --exit-code --heads origin immagini >/dev/null 2>&1; then
    git fetch -q origin immagini
    git worktree add -q "$TREE" immagini
  else
    git worktree add -q --orphan -b immagini "$TREE"
  fi
fi
for NAME in "$@"; do
  [ -d "atlante/locale/immagini/$NAME" ] || { echo "Manca la cartella atlante/locale/immagini/$NAME"; exit 1; }
  mkdir -p "$TREE/$BRANCH/$NAME"
  cp atlante/locale/immagini/"$NAME"/*.png "$TREE/$BRANCH/$NAME/"
done
git -C "$TREE" add -A
git -C "$TREE" commit -q -m "Immagini di $BRANCH: $*" || echo "Nessuna immagine nuova."
git -C "$TREE" push -q -u origin immagini
echo "Link da incollare:"
for NAME in "$@"; do
  for FILE in "$TREE/$BRANCH/$NAME"/*.png; do
    echo "![$NAME $(basename "$FILE" .png)](https://github.com/$REPO/blob/immagini/$BRANCH/$NAME/$(basename "$FILE")?raw=true)"
  done
done
