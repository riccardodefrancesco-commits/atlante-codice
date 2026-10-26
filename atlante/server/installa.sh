#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# From the Mac: copies Atlante's saved code to the test server, builds it there and starts it. The first time
# it writes the secrets on the server (crea-segreti.sh) and creates "Zeta3 Collaudo" with the people of the
# local credentials file, sent through SSH and never written on the server's disk.
#
#   sh atlante/server/installa.sh atlante-collaudo collaudo.zeta3.it
#
# Never a copy of the Mac's database: the data are created from scratch by atlante_dati_collaudo.

set -eu
cd "$(git rev-parse --show-toplevel)"

SERVER=${1:?"Indica l'accesso, per esempio atlante@203.0.113.10"}
DOMINIO=${2:?"Indica il dominio, per esempio collaudo.zeta3.it"}
CREDENZIALI=atlante/locale/credenziali-prova.md
SERVIZI="cd ~/atlante/codice/atlante/server && docker compose -f docker-compose.collaudo.yml"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
	echo "Ci sono modifiche non salvate: sul server va solo codice salvato in git."
	exit 1
fi
COMMIT=$(git rev-parse --short HEAD)

echo "1. Copio il codice salvato ($COMMIT) sul server, tenendo i segreti che ci sono già."
git archive --format=tar HEAD | ssh "$SERVER" 'set -e
	rm -rf ~/atlante/nuovo && mkdir -p ~/atlante/nuovo && tar -x -C ~/atlante/nuovo
	for f in .env api.env live.env; do
		if [ -e ~/atlante/codice/atlante/server/$f ]; then cp -p ~/atlante/codice/atlante/server/$f ~/atlante/nuovo/atlante/server/; fi
	done
	rm -rf ~/atlante/vecchio
	if [ -d ~/atlante/codice ]; then mv ~/atlante/codice ~/atlante/vecchio; fi
	mv ~/atlante/nuovo ~/atlante/codice
	echo '"$COMMIT"' > ~/atlante/codice/VERSIONE'

echo "2. Segreti del server (solo la prima volta)."
ssh "$SERVER" "sh ~/atlante/codice/atlante/server/crea-segreti.sh '$DOMINIO'"

echo "3. Costruisco e avvio Atlante (la prima volta 15-20 minuti)."
ssh "$SERVER" "$SERVIZI up -d --build --remove-orphans"
ssh "$SERVER" "$SERVIZI wait migrator" >/dev/null

echo "4. Aspetto che il server di Atlante sia pronto."
PRONTO="from plane.license.models import Instance; import sys; sys.exit(0 if Instance.objects.exists() else 1)"
tentativi=0
until ssh "$SERVER" "$SERVIZI exec -T api python manage.py shell -c '$PRONTO'" >/dev/null 2>&1; do
	tentativi=$((tentativi + 1))
	[ "$tentativi" -lt 60 ] || { echo "Atlante non risponde dopo 5 minuti: guarda $SERVIZI logs api"; exit 1; }
	sleep 5
done

echo "5. Dati del collaudo."
ESISTE="from plane.db.models import Workspace; import sys; sys.exit(0 if Workspace.objects.filter(slug='zeta3-collaudo').exists() else 1)"
if ssh "$SERVER" "$SERVIZI exec -T api python manage.py shell -c \"$ESISTE\"" >/dev/null 2>&1; then
	echo "   Lo spazio Zeta3 Collaudo c'è già: non lo tocco."
else
	ssh "$SERVER" "$SERVIZI exec -T api python manage.py atlante_dati_collaudo --persone -" < "$CREDENZIALI" | grep -v '^{"levelname"'
fi
echo "Fatto: Atlante $COMMIT su https://$DOMINIO. Ora: sh atlante/server/controlla-server.sh $SERVER $DOMINIO"
