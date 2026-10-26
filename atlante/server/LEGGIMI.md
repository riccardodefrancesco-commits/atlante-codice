# Server di prova del collaudo online

Il server su cui Alessandra, Virginia e Giulia provano Atlante 0.3 (documento `docs/collaudo-0.3.md` in `zeta3-progetti`, sezione 1). Solo dati inventati, per poche persone e poche settimane: i punti del livello 2 di `docs/regole/sicurezza.md` rimandati qui (accesso con Google, verifica in due passaggi, copie di sicurezza, avvisi automatici, limite dei file, mittente delle email) restano obbligatori prima di qualsiasi dato vero.

| File                          | A cosa serve                                                                                                                     |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `prepara-server.sh`           | Mette in ordine un Ubuntu 24.04 nuovo: utente `atlante` con chiave, firewall, aggiornamenti automatici, Docker; poi chiude SSH   |
| `crea-segreti.sh`             | Scrive sul server le password interne (database, code, archivio file) in `.env`, `api.env`, `live.env`: casuali, mai in git      |
| `docker-compose.collaudo.yml` | Atlante costruito dal nostro codice: interfaccia costruita, una sola porta verso internet (il proxy), tutto il resto senza porte |
| `Caddyfile`                   | Il proxy: HTTPS con certificato automatico, pannello amministratore e registrazione chiusi verso internet                        |
| `installa.sh`                 | Dal Mac: copia il codice salvato, costruisce, avvia e la prima volta crea "Zeta3 Collaudo"                                       |
| `controlla-server.sh`         | Dal Mac: i punti di sicurezza, ognuno con il suo esito, e la prova di ogni riga di "Cosa deve succedere"                         |

## I passi

1. **Rick** compra il server (Unione Europea, dentro i 50 € al mese: per il collaudo un Cloud VPS O4A8 di Aruba, in Italia) con Ubuntu 24.04 e la chiave pubblica `~/.ssh/atlante_collaudo.pub` del Mac; aggiunge su Register.it il record A di `collaudo.zeta3.it` con l'indirizzo IP del server.
2. **Claude Code**, dal Mac. Prima in `~/.ssh/config` due nomi brevi con l'IP e la chiave `~/.ssh/atlante_collaudo`: `atlante-collaudo-root` (utente root, solo per questo passo) e `atlante-collaudo` (utente `atlante`). Poi:
   ```sh
   scp atlante/server/prepara-server.sh atlante-collaudo-root:/root/
   # 10-15 minuti di aggiornamenti: staccato dal collegamento, finisce anche se si interrompe
   ssh atlante-collaudo-root 'nohup sh /root/prepara-server.sh utente > /root/prepara-utente.log 2>&1 < /dev/null &'
   ssh atlante-collaudo-root tail -1 /root/prepara-utente.log   # aspettare la riga "Fatto: ..."
   ssh atlante-collaudo sudo true                                 # deve funzionare prima di chiudere
   ssh atlante-collaudo-root sh /root/prepara-server.sh chiudi
   ssh atlante-collaudo sudo systemctl reboot                     # il sistema aggiornato riparte
   ```
   Fatto il 26 ottobre sul VPS Aruba O4A8 (Ubuntu 24.04): Aruba ha già il firewall acceso con solo SSH e fail2ban, che blocca chi prova a indovinare l'accesso.
3. `sh atlante/script/pubblica-codice.sh 0.3.0-alfa` (solo controlli), poi con `--pubblica`: il codice della versione nel repository pubblico `atlante-codice`, a cui rimanda "Informazioni su Atlante".
4. `sh atlante/server/installa.sh atlante-collaudo collaudo.zeta3.it`: le persone del collaudo arrivano dal file `atlante/locale/credenziali-prova.md` attraverso SSH e non si scrivono mai sul disco del server.
5. `sh atlante/server/controlla-server.sh atlante-collaudo collaudo.zeta3.it`: la lista per Rick, punto per punto. Solo con tutto "OK" Rick manda le credenziali.

Il pannello amministratore (`/god-mode`) da internet non esiste; serve solo a Claude Code, con il tunnel: `ssh -L 8080:127.0.0.1:8080 atlante-collaudo`, poi `http://localhost:8080/god-mode/`.

Mai copiare il database del Mac sul server: i dati li crea da zero `atlante_dati_collaudo`, e non si rilancia durante la prova. Per un secondo giro, dopo le correzioni: `--nuovo-giro`, che archivia il primo (rinominato, senza membri) e non cancella niente.
