# Marchio di Atlante

Qui stanno nome, colore, segno e icona di Atlante. Lo script `atlante/script/marchio.py` li applica sopra a Plane: logo in tutte le schermate, icone del browser e del telefono, colori, titoli, testi italiani e inglesi. Va rilanciato dopo ogni aggiornamento preso da Plane.

- `marchio.json`: nome, descrizione e colore principale. Dal colore lo script ricava tutte le sfumature dell'interfaccia, con la stessa luminosità di quelle di Plane, così la leggibilità resta uguale.
- `segno.svg`: il segno usato nell'interfaccia, disegnato con il colore del testo (`currentColor`): il logo di Zeta3, largo circa tre volte e mezza l'altezza. Lo script lo mette accanto al nome "Atlante", al centro delle icone e dell'anteprima, in qualunque proporzione.
- `icona.svg`: l'icona dell'app (sfondo colorato e logo bianco), da cui escono le icone del browser e del telefono in `icone/`.
- `originali/zeta3-logo-bianco.svg`: il logo di Zeta3 come l'ha mandato Rick il 21 ottobre 2026 (bianco). `segno.svg` e `icona.svg` vengono da qui.

**Logo e colore sono quelli definitivi** dal 21 ottobre 2026: il logo di Zeta3 e il verde petrolio #0F766E. Per cambiarli si sostituiscono `segno.svg`, `icona.svg` o il colore in `marchio.json`, e si rilancia lo script.

Comandi, dalla cartella del repository:

- Applicare il marchio: `python3 -I atlante/script/marchio.py`
- Solo controllare che non sia rimasto "Plane" nei punti visibili: `python3 -I atlante/script/marchio.py --verifica`

Le icone PNG si rigenerano solo su Mac (con `qlmanage`); altrove lo script usa quelle già salvate in `icone/`.
