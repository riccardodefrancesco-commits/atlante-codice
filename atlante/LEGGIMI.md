# Atlante

Programma di gestione progetti interno di Zeta3. È una copia indipendente di Plane (https://github.com/makeplane/plane), con licenza AGPL-3.0: Atlante è basato su Plane e ne mantiene la licenza.

## Cosa c'è in questa cartella

| File o cartella        | A cosa serve                                                                                                                                 |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `LEGGIMI.md`           | Questo file                                                                                                                                  |
| `modifiche-a-plane.md` | L'elenco di ogni file di Plane che abbiamo modificato, con il motivo. È la prima cosa da guardare quando si prende un aggiornamento da Plane |
| `aggiornamenti.md`     | Il registro degli aggiornamenti presi da Plane: correzioni di sicurezza del lunedì e nuove versioni                                          |
| `avvio-locale.md`      | Come si accende Atlante sul Mac per le prove                                                                                                 |
| `locale/`              | Impostazioni e credenziali di prova solo per questo Mac. Esclusa da git                                                                      |
| `server/`              | Il server di prova del collaudo online: come si prepara, si installa e si controlla (`server/LEGGIMI.md`)                                    |

## Dove sta il resto

- Le nostre parti di server: `apps/api/plane/atlante/`.
- Le nostre parti di interfaccia: `apps/web/atlante/`.
- I documenti del progetto (specifica, decisioni, stato, registro della prova): repository `zeta3-progetti`.
