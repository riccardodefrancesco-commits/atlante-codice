#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# The security points of the test server, each with its result (zeta3-progetti, docs/collaudo-0.3.md,
# section 1; docs/regole/sicurezza.md, level 2). From the Mac, before the people sign in:
#
#   sh atlante/server/controlla-server.sh atlante@<server> collaudo.zeta3.it
#
# Some checks look from the internet, as anybody could; the others look inside the server. At the end it
# checks on the data every row of "Cosa deve succedere" (atlante_verifica_collaudo), without changing them.
# It never prints a secret. It exits with 1 if a point is not in order.

set -u
cd "$(git rev-parse --show-toplevel)"

SERVER=${1:?"Indica l'accesso, per esempio atlante@203.0.113.10"}
DOMINIO=${2:?"Indica il dominio, per esempio collaudo.zeta3.it"}
SITO="https://$DOMINIO"
CODICE="https://github.com/riccardodefrancesco-commits/atlante"
SERVIZI="cd ~/atlante/codice/atlante/server && docker compose -f docker-compose.collaudo.yml"
PROBLEMI=0

ok() { printf 'OK  %s\n' "$1"; }
no() { printf 'NO  %s\n' "$1"; PROBLEMI=$((PROBLEMI + 1)); }
da_vedere() { printf '??  %s\n' "$1"; }
dentro() { ssh -o BatchMode=yes "$SERVER" "$@" 2>/dev/null; }
stato() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@"; }

echo "Server di prova di Atlante: $DOMINIO, $(date '+%d/%m/%Y %H:%M')"
echo

echo "1. Server in Unione Europea"
ZONA=$(dentro curl -s --max-time 3 http://169.254.169.254/hetzner/v1/metadata/availability-zone)
case "$ZONA" in
	nbg1*) ok "Hetzner, Norimberga (Germania): $ZONA" ;;
	fsn1*) ok "Hetzner, Falkenstein (Germania): $ZONA" ;;
	hel1*) ok "Hetzner, Helsinki (Finlandia): $ZONA" ;;
	"")
		# Other providers: the public register of IP addresses (RIPE) says whose the address is, and where.
		IP=$(ssh -G "$SERVER" 2>/dev/null | awk '$1 == "hostname" {print $2}')
		REGISTRO=$(whois "$IP" 2>/dev/null)
		PAESE=$(echo "$REGISTRO" | awk -F: 'tolower($1) == "country" {gsub(/ /, "", $2); print $2; exit}')
		CHI=$(echo "$REGISTRO" | awk -F: 'tolower($1) == "descr" {sub(/^ +/, "", $2); print $2; exit}')
		case " AT BE BG CY CZ DE DK EE ES FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK " in
			*" $PAESE "*) ok "$IP: $CHI, paese $PAESE" ;;
			*) [ -n "$PAESE" ] && no "$IP: paese $PAESE, non in Unione Europea" || da_vedere "regione non letta: controllala sull'ordine" ;;
		esac
		;;
	*) no "zona $ZONA: non è in Unione Europea" ;;
esac

echo "2. Solo HTTPS, con un certificato valido"
if [ "$(stato "$SITO/")" = 200 ]; then
	EMITTENTE=$(echo | openssl s_client -connect "$DOMINIO:443" -servername "$DOMINIO" 2>/dev/null | openssl x509 -noout -issuer -enddate 2>/dev/null | tr '\n' ' ')
	ok "$SITO risponde con un certificato valido ($EMITTENTE)"
else
	no "$SITO non risponde con un certificato valido"
fi
DOVE=$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 15 "http://$DOMINIO/")
case "$DOVE" in
	30[178]" https://"*) ok "la porta 80 manda solo a HTTPS ($DOVE)" ;;
	*) no "la porta 80 non manda a HTTPS: $DOVE" ;;
esac
HSTS=$(curl -s -D - -o /dev/null --max-time 15 "$SITO/" | grep -ci '^strict-transport-security')
[ "$HSTS" -ge 1 ] && ok "il browser ricorda di usare solo HTTPS (HSTS)" || no "manca HSTS"

echo "3. Da fuori si raggiunge solo la porta del sito"
APERTE=""
for porta in 22 80 443 3000 3100 5432 5672 6379 8000 8080 9000 9090 15672; do
	nc -z -G 3 "$DOMINIO" "$porta" >/dev/null 2>&1 && APERTE="$APERTE $porta"
done
[ "$APERTE" = " 22 80 443" ] && ok "aperte solo 22 (accesso tecnico con chiave), 80 e 443" || no "porte aperte da fuori:$APERTE"
PUBBLICATE=$(dentro "$SERVIZI ps --format '{{.Service}} {{.Ports}}'" | grep -E '0\.0\.0\.0|\[::\]|127\.0\.0\.1' | awk '{print $1}' | sort -u | tr '\n' ' ')
[ "$PUBBLICATE" = "proxy " ] && ok "database, code, archivio file e memoria rapida senza porte: solo il proxy ne ha" \
	|| no "servizi con porte: $PUBBLICATE"
REGOLE=$(dentro sudo ufw status | grep -c ALLOW)
dentro sudo ufw status | grep -q "Status: active" && ok "firewall attivo ($REGOLE regole: 22, 80, 443)" || no "firewall spento"

echo "4. Registrazione libera spenta"
CONFIG=$(curl -s --max-time 15 "$SITO/api/instances/")
echo "$CONFIG" | python3 -c 'import json,sys; c=json.load(sys.stdin).get("config",{}); sys.exit(0 if c.get("enable_signup") is False else 1)' \
	&& ok "Atlante dice: registrazione spenta" || no "Atlante dice che la registrazione è accesa"
[ "$(stato -X POST "$SITO/auth/sign-up/")" = 404 ] && ok "la pagina di registrazione non esiste da fuori" || no "la registrazione risponde da fuori"

echo "5. Pannello amministratore non raggiungibile da internet"
[ "$(stato "$SITO/god-mode/")" = 404 ] && [ "$(stato "$SITO/api/instances/admins/me/")" = 404 ] \
	&& ok "da internet il pannello e le sue richieste non esistono (404)" || no "il pannello risponde da internet"
[ "$(dentro curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/god-mode/)" = 200 ] \
	&& ok "dal server, solo con il tunnel SSH, il pannello c'è" || da_vedere "il pannello non risponde neanche dal tunnel"

echo "6. Server in ordine"
dentro apt-config dump | grep -q 'APT::Periodic::Unattended-Upgrade "1"' && dentro systemctl is-active --quiet unattended-upgrades \
	&& ok "aggiornamenti di sistema automatici, riavvio se serve alle 4" || no "aggiornamenti automatici spenti"
SSHD=$(dentro sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication) ' | sort | tr '\n' ' ')
[ "$SSHD" = "kbdinteractiveauthentication no passwordauthentication no permitrootlogin no " ] \
	&& ok "accesso tecnico solo con chiave, niente root, niente password" || no "SSH: $SSHD"
PERMESSI=$(dentro "cd ~/atlante/codice/atlante/server && stat -c '%a' .env api.env live.env" | sort -u | tr '\n' ' ')
[ "$PERMESSI" = "600 " ] && ok "segreti solo nei file del server, leggibili solo dal suo utente" || no "permessi dei segreti: $PERMESSI"

echo "7. Interfaccia costruita, non quella di sviluppo (#27)"
PAGINA=$(curl -s --max-time 15 "$SITO/")
if echo "$PAGINA" | grep -q '/@vite/client'; then
	no "è l'interfaccia di sviluppo"
elif echo "$PAGINA" | grep -q '/assets/'; then
	ok "interfaccia costruita: file statici, versione $(dentro cat ~/atlante/codice/VERSIONE)"
else
	no "la pagina non sembra Atlante"
fi

echo "8. Codice pubblico per la licenza AGPL (#25)"
[ "$(stato "$CODICE")" = 200 ] && ok "$CODICE è pubblico" || no "$CODICE non è pubblico"

echo "9. Solo dati inventati, telemetria spenta"
DATI=$(dentro "$SERVIZI exec -T api python manage.py shell" <<'PY'
from plane.atlante.models import Client
from plane.db.models import User, Workspace
from plane.license.models import Instance

spaces = sorted(Workspace.objects.values_list("slug", flat=True))
clients = sorted(set(Client.objects.values_list("name", flat=True)))
people = User.objects.filter(is_bot=False)
invented = people.filter(email__endswith="@collaudo.esempio.it").count()
instance = Instance.objects.first()
print("spazi", ",".join(spaces))
print("clienti", ",".join(clients))
print("persone", people.count(), "inventate", invented)
print("telemetria", bool(instance and instance.is_telemetry_enabled))
PY
)
SPAZI=$(echo "$DATI" | awk '$1=="spazi"{print $2}')
CLIENTI=$(echo "$DATI" | awk '$1=="clienti"{$1=""; print substr($0,2)}')
case "$SPAZI" in
	zeta3-collaudo | zeta3-collaudo,zeta3-collaudo-giro-*) ok "spazi: $SPAZI" ;;
	*) no "spazi inattesi: $SPAZI" ;;
esac
[ "$CLIENTI" = "Alfa Biscotti,Zeta Gelati" ] && ok "clienti inventati: $CLIENTI" || no "clienti: $CLIENTI"
PERSONE=$(echo "$DATI" | awk '$1=="persone"{print $2" persone, di cui "$4" colleghi inventati"}')
[ -n "$PERSONE" ] && ok "$PERSONE (le altre sono Rick, Alessandra, Virginia e Giulia)" || no "persone non lette"
echo "$DATI" | grep -q "^telemetria False" && ok "telemetria verso Plane spenta" || no "telemetria accesa o non letta"

echo "10. Cosa deve succedere (sezione 3), provato sui dati e poi annullato"
VERIFICA=$(dentro "$SERVIZI exec -T api python manage.py atlante_verifica_collaudo" | grep -E '^(OK|NO) ')
RIGHE_OK=$(echo "$VERIFICA" | grep -c '^OK ')
RIGHE_NO=$(echo "$VERIFICA" | grep -c '^NO ')
[ "$RIGHE_NO" -eq 0 ] && [ "$RIGHE_OK" -gt 0 ] && ok "$RIGHE_OK righe su $RIGHE_OK come scritto" \
	|| no "$RIGHE_NO righe diverse: $(echo "$VERIFICA" | grep '^NO ' | cut -c5- | tr '\n' ';')"

echo
if [ "$PROBLEMI" -eq 0 ]; then
	echo "Tutto in ordine: si possono mandare le credenziali."
else
	echo "$PROBLEMI punti da sistemare prima di far entrare qualcuno."
	exit 1
fi
