# Accendere Atlante sul Mac, per le prove

Solo dati inventati. I comandi si lanciano dalla cartella del repository `atlante`.

La cartella sta in `~/Sviluppo/atlante`, **fuori dalla cartella Documenti**: Documenti è sincronizzata con iCloud, che segnala come cambiati file mai toccati (l'interfaccia si ricaricava da sola) e può togliere dal Mac i file poco usati. Il repository non va mai rimesso dentro Documenti o Scrivania.

## Una volta sola

1. **Docker Desktop** installato e aperto, con 12 GB di memoria (Impostazioni › Risorse).
2. **Node 22.22 e pnpm 11** (Node con nvm: `nvm install 22.22.0`; pnpm con `corepack enable`).
3. **Librerie dell'interfaccia:** `pnpm install`.
4. **Impostazioni locali:** `python3 -I atlante/script/prepara_locale.py`. Crea i file `.env` con password casuali e scrive le credenziali di prova in `atlante/locale/credenziali-prova.md`. Tutto resta sul Mac, escluso da git.

## Ogni volta

1. **Database, archivio file, coda e server:** `docker compose -f docker-compose-local.yml up -d`. La prima volta Docker scarica e prepara tutto: 15-30 minuti.
2. **Interfaccia:** `pnpm dev`. Atlante si apre su http://localhost:3000, il pannello amministratore su http://localhost:3001/god-mode/.
3. **Dati inventati, solo la prima volta:** `docker compose -f docker-compose-local.yml exec api python manage.py atlante_dati_prova --settings=plane.settings.local`.
4. **Per spegnere:** Ctrl+C dove gira `pnpm dev`, poi `docker compose -f docker-compose-local.yml stop`.
5. **Dopo un cambio di ramo** (git checkout) il server può fermarsi, perché si ricarica mentre i file cambiano: `docker compose -f docker-compose-local.yml restart api worker beat-worker`.

## Test

- Test di Atlante, veloci, dentro il server acceso: `docker compose -f docker-compose-local.yml exec -e REDIS_URL=redis://plane-redis:6379/9 api python -m pytest plane/atlante/tests -p no:cacheprovider`. Lo spazio 9 della memoria veloce tiene i test lontani da quella di Atlante acceso: senza, un test può lasciare risposte finte che Atlante poi mostra.
- Tutti i test (Plane e nostri), in un ambiente pulito: `docker compose -p atlante-test -f docker-compose-test.yml run --rm api-tests pytest -p no:cacheprovider`, poi `docker compose -p atlante-test -f docker-compose-test.yml down -v`. Il nome `atlante-test` tiene i contenitori di prova separati da quelli di Atlante acceso.

## Prima di salvare un pezzo o un aggiornamento da Plane

- `sh atlante/script/controlla-tutto.sh`: marchio, controllo dei tipi di **tutti** i pacchetti, test dell'interfaccia e tutti i test del server. Si ferma al primo errore. Ci vogliono circa 5 minuti.
- Il controllo automatico a ogni salvataggio (git commit) è più leggero: formatta, blocca gli avvisi nuovi e fa girare i test dell'interfaccia.

## Sicurezza in locale

- Database, memoria rapida, archivio file, server e server delle pagine condivise rispondono **solo al Mac** (`127.0.0.1`), mai agli altri dispositivi della rete Wi-Fi. Prima rispondevano a tutta la rete: segnalazione zeta3-progetti#10.
- La registrazione libera è spenta: si entra solo con le persone di prova o su invito. I dati inventati (`atlante_dati_prova`) la spengono anche in un'installazione nuova.
- Il firewall del Mac (Impostazioni di Sistema › Rete › Firewall) è una protezione in più, consigliata: la decide Rick.

## Cosa non c'è in locale

- L'accesso con Google: serve il progetto su Google Cloud, si farà sul server di prova. In locale si entra con email e password di prova.
- Le email: in locale non partono.
