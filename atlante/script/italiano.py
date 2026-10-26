# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Applies Atlante's glossary (docs/regole/coerenza.md) to Plane's Italian translations.

Plane says "elemento di lavoro" for a work item and "Accoglienza" for Intake; the team says "task"
(feminine: "la task", "le task") and "Richieste in arrivo". The script rewrites the Italian texts of
packages/i18n/src/locales/it/ with rules that also fix articles and agreements ("un nuovo elemento
di lavoro creato" becomes "una nuova task creata"), then applies the exact texts of
atlante/testi/italiano.json for the sentences the rules cannot handle.

Usage, from the repository root (re-run after every update from Plane, like marchio.py):
    python3 -I atlante/script/italiano.py             # apply
    python3 -I atlante/script/italiano.py --verifica  # only check: exit 1 if a word outside the glossary is left
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCALE = ROOT / "packages" / "i18n" / "src" / "locales" / "it"
EXACT = ROOT / "atlante" / "testi" / "italiano.json"
SKIP = {"atlante.json"}  # ours, already in Atlante's words

# Words that must not be left (with what to use instead), checked by --verifica.
FORBIDDEN = [
    (re.compile(r"\belement[oi] di lavoro\b", re.I), "task"),
    (re.compile(r"\bsotto-element[oi]\b", re.I), "sotto-task"),
    (re.compile(r"\baccoglienza\b", re.I), "Richieste in arrivo"),
    (re.compile(r"\bIntake\b"), "Richieste in arrivo"),
    (re.compile(r"\bwork items?\b", re.I), "task"),
    (re.compile(r"\bassegnatari[oi]?\b", re.I), "esecutore, esecutori"),
    (re.compile(r"\bRicezione\b|\bAbilita ricezione\b"), "Richieste in arrivo"),
    (re.compile(r"\bPriorità\b"), "Urgenza"),
    (re.compile(r"\bmodul[oi]\b", re.I), "sezione, sezioni (i moduli da compilare restano moduli)"),
]
# Plane's modules are Atlante's sections (glossary, request 38); "moduli" stays only for the forms of
# Richieste in arrivo, which are forms to fill in.
FORM_KEYS = re.compile(r"(^|:)forms?$|\.intake\.form\.")

W = r"[Ee]lement[oi] di [Ll]avoro"
# Agreement of the words right after the noun: masculine participles and adjectives become feminine.
AFTER = (
    r"(creat|aggiornat|rimoss|copiat|archiviat|trovat|assegnat|selezionat|eliminat|spostat|collegat|chius|"
    r"apert|aggiunt|duplicat|importat|esportat|bloccat|completat|annullat|programmat|ripristinat|salvat|"
    r"mostrat|visualizzat|filtrat|raggruppat|ordinat|nascost|modificat|incollat|associat|interconness|"
    r"segnalat|condivis|iscritt|scadut|ritardat|inviat|caricat|convertit|pubblicat|nuov|sottoscritt|inattiv|mappat|divers)"
)

# (pattern, replacement) in order: the longest phrases first. \g<c> keeps the capital letter.
RULES = [
    # agreement right after the noun: "elemento di lavoro creato" -> "task creata"
    (rf"\b(?P<w>{W})\s+{AFTER}o\b", lambda m: f"{m['w']} {m[2]}a"),
    (rf"\b(?P<w>{W})\s+{AFTER}i\b", lambda m: f"{m['w']} {m[2]}e"),
    # capitals inside titles ("Tipi di Elementi di Lavoro")
    (r"\bElementi di Lavoro\b", "elementi di lavoro"),
    (r"\bElemento di Lavoro\b", "elemento di lavoro"),
    # sub-items
    (r"\b(?P<c>[Uu])n sotto-elemento( di lavoro)?\b", lambda m: m["c"] + "na sotto-task"),
    (r"\b(?P<c>[Ii]) suoi sotto-element[oi]( di lavoro)?\b", lambda m: ("L" if m["c"] == "I" else "l") + "e sue sotto-task"),
    (r"\b(?P<c>[Tt])utti i sotto-elementi( di lavoro)?\b", lambda m: ("T" if m["c"] == "T" else "t") + "utte le sotto-task"),
    (r"\b(?P<c>[Nn])essun sotto-elemento( di lavoro)?\b", lambda m: m["c"] + "essuna sotto-task"),
    (r"\b(?P<c>[Dd])el sotto-elemento( di lavoro)?\b", lambda m: m["c"] + "ella sotto-task"),
    (r"\b(?P<c>[Dd])ei sotto-elementi( di lavoro)?\b", lambda m: m["c"] + "elle sotto-task"),
    (r"\b(?P<c>[Aa])l sotto-elemento( di lavoro)?\b", lambda m: m["c"] + "lla sotto-task"),
    (r"\b(?P<c>[Ii]l) sotto-elemento( di lavoro)?\b", lambda m: ("L" if m["c"][0] == "I" else "l") + "a sotto-task"),
    (r"\b(?P<c>[Ii]) sotto-elementi( di lavoro)?\b", lambda m: ("L" if m["c"] == "I" else "l") + "e sotto-task"),
    (r"\b(?P<c>[Tt])utti i nuovi elementi di lavoro\b", lambda m: ("T" if m["c"] == "T" else "t") + "utte le nuove task"),
    (r"\b(?P<c>[Ss])otto-elementi di lavoro\b", r"\g<c>otto-task"),
    (r"\b(?P<c>[Ss])otto-elemento di lavoro\b", r"\g<c>otto-task"),
    (r"\b(?P<c>[Ss])otto-elementi\b", r"\g<c>otto-task"),
    (r"\b(?P<c>[Ss])otto-elemento\b", r"\g<c>otto-task"),
    # determiners and possessives, plural
    (r"\b(?P<c>[Tt])utti gli elementi di lavoro\b", lambda m: ("T" if m["c"] == "T" else "t") + "utte le task"),
    (r"\b(?P<c>[Ii]) tuoi elementi di lavoro\b", lambda m: ("L" if m["c"] == "I" else "l") + "e tue task"),
    (r"\b(?P<c>[Dd])ei tuoi elementi di lavoro\b", lambda m: m["c"] + "elle tue task"),
    (r"\b(?P<c>[Aa])i tuoi elementi di lavoro\b", lambda m: m["c"] + "lle tue task"),
    (r"\b(?P<c>[Ii]) miei elementi di lavoro\b", lambda m: ("L" if m["c"] == "I" else "l") + "e mie task"),
    (r"\b(?P<c>[Gg])li elementi di lavoro\b", lambda m: ("L" if m["c"] == "G" else "l") + "e task"),
    (r"\b(?P<c>[Dd])egli elementi di lavoro\b", lambda m: m["c"] + "elle task"),
    (r"\b(?P<c>[Aa])gli elementi di lavoro\b", lambda m: m["c"] + "lle task"),
    (r"\b(?P<c>[Nn])egli elementi di lavoro\b", lambda m: m["c"] + "elle task"),
    (r"\b(?P<c>[Ss])ugli elementi di lavoro\b", lambda m: m["c"] + "ulle task"),
    (r"\b(?P<c>[Dd])agli elementi di lavoro\b", lambda m: m["c"] + "alle task"),
    (r"\b(?P<c>[Qq])uesti elementi di lavoro\b", lambda m: m["c"] + "ueste task"),
    (r"\b(?P<c>[Aa])lcuni elementi di lavoro\b", lambda m: m["c"] + "lcune task"),
    (r"\b(?P<c>[Mm])olti elementi di lavoro\b", lambda m: m["c"] + "olte task"),
    (r"\b(?P<c>[Nn])uovi elementi di lavoro\b", lambda m: m["c"] + "uove task"),
    (r"\b(?P<c>[Pp])iù elementi di lavoro\b", lambda m: m["c"] + "iù task"),
    (r"\b(?P<c>[Ii]) (?=elementi di lavoro)", lambda m: ("L" if m["c"] == "I" else "l") + "e "),
    # determiners and possessives, singular
    (r"\b(?P<c>[Ii]l tuo primo) elemento di lavoro\b", lambda m: ("L" if m["c"][0] == "I" else "l") + "a tua prima task"),
    (r"\b(?P<c>[Tt])uo primo elemento di lavoro\b", lambda m: m["c"] + "ua prima task"),
    (r"\b(?P<c>[Uu])n nuovo elemento di lavoro\b", lambda m: m["c"] + "na nuova task"),
    (r"\b(?P<c>[Nn])uovo elemento di lavoro\b", lambda m: m["c"] + "uova task"),
    (r"\b(?P<c>[Uu])n elemento di lavoro\b", lambda m: m["c"] + "na task"),
    (r"\b(?P<c>[Nn])essun elemento di lavoro\b", lambda m: m["c"] + "essuna task"),
    (r"\b(?P<c>[Qq])uesto elemento di lavoro\b", lambda m: m["c"] + "uesta task"),
    (r"\b(?P<c>[Qq])uell'elemento di lavoro\b", lambda m: m["c"] + "uella task"),
    (r"\b(?P<c>[Ii]l tuo) elemento di lavoro\b", lambda m: ("L" if m["c"][0] == "I" else "l") + "a tua task"),
    (r"\b(?P<c>[Tt])uo elemento di lavoro\b", lambda m: m["c"] + "ua task"),
    (r"\b(?P<c>[Ss])uo elemento di lavoro\b", lambda m: m["c"] + "ua task"),
    (r"\b(?P<c>[Ll])'elemento di lavoro\b", lambda m: m["c"] + "a task"),
    (r"\b(?P<c>[Dd])ell'elemento di lavoro\b", lambda m: m["c"] + "ella task"),
    (r"\b(?P<c>[Aa])ll'elemento di lavoro\b", lambda m: m["c"] + "lla task"),
    (r"\b(?P<c>[Nn])ell'elemento di lavoro\b", lambda m: m["c"] + "ella task"),
    (r"\b(?P<c>[Ss])ull'elemento di lavoro\b", lambda m: m["c"] + "ulla task"),
    (r"\b(?P<c>[Dd])all'elemento di lavoro\b", lambda m: m["c"] + "alla task"),
    (r"\b(?P<c>[Ii]l) (?=elemento di lavoro)", lambda m: ("L" if m["c"][0] == "I" else "l") + "a "),
    (r"\b(?P<c>[Dd])el (?=elemento di lavoro)", lambda m: m["c"] + "ella "),
    (r"\b(?P<c>[Aa])l (?=elemento di lavoro)", lambda m: m["c"] + "lla "),
    # the noun itself, at last
    (r"\bElementi di lavoro\b", "Task"),
    (r"\bElemento di lavoro\b", "Task"),
    (r"\belementi di lavoro\b", "task"),
    (r"\belemento di lavoro\b", "task"),
    # agreement after "task" (also in texts already rewritten): task creata, una task è completata,
    # le task sono state spostate
    (rf"\b(?P<w>[Tt]ask)\s+{AFTER}o\b", lambda m: f"{m['w']} {m[2]}a"),
    (rf"\b(?P<w>[Tt]ask)\s+{AFTER}i\b", lambda m: f"{m['w']} {m[2]}e"),
    (rf"\b(?P<w>(?:[Uu]na|[Ll]a|[Qq]uesta|[Nn]essuna) task) (?P<v>è|viene|verrà|sarà|è stato|è stata) {AFTER}o\b",
     lambda m: f"{m['w']} {m['v'].replace('stato', 'stata')} {m[3]}a"),
    (rf"\b(?P<w>le task) (?P<v>sono|vengono|verranno|saranno|sono stati|sono state) {AFTER}i\b",
     lambda m: f"{m['w']} {m['v'].replace('stati', 'state')} {m[3]}e"),
    # plural adjectives in -ci after "le task": critici -> critiche, specifici -> specifiche
    (r"\b(?P<w>(?:le|tue|mie|delle|alle|sulle) task) (?P<a>critic|specific)i\b", lambda m: f"{m['w']} {m['a']}he"),
    (r"\b(?P<w>esportare task) specifici\b", lambda m: f"{m['w']} specifiche"),
    # Fase instead of Stato (docs/regole/coerenza.md), only where "stato" is surely the noun: with an
    # article or a determiner, or as a whole label. Never "stato di avanzamento" (progress) or "è stato".
    (r"^Stato$", "Fase"),
    (r"^Stati$", "Fasi"),
    (r"^Stato predefinito$", "Fase predefinita"),
    (r"\b(?P<c>[Ll])o stato(?! di avanzamento)\b", lambda m: ("L" if m["c"] == "L" else "l") + "a fase"),
    (r"\b(?P<c>[Gg])li stati\b", lambda m: ("L" if m["c"] == "G" else "l") + "e fasi"),
    (r"\b(?P<c>[Dd])ello stato(?! di avanzamento)\b", lambda m: m["c"] + "ella fase"),
    (r"\b(?P<c>[Dd])egli stati\b", lambda m: m["c"] + "elle fasi"),
    (r"\b(?P<c>[Aa])llo stato\b", lambda m: m["c"] + "lla fase"),
    (r"\b(?P<c>[Aa])gli stati\b", lambda m: m["c"] + "lle fasi"),
    (r"\b(?P<c>[Nn])ello stato\b", lambda m: m["c"] + "ella fase"),
    (r"\b(?P<c>[Nn])egli stati\b", lambda m: m["c"] + "elle fasi"),
    (r"\b(?P<c>[Ss])ullo stato\b", lambda m: m["c"] + "ulla fase"),
    (r"\b(?P<c>[Uu])n nuovo stato\b", lambda m: m["c"] + "na nuova fase"),
    (r"\b(?P<c>[Uu])no stato\b", lambda m: m["c"] + "na fase"),
    (r"\b(?P<c>[Nn])essuno stato\b", lambda m: m["c"] + "essuna fase"),
    (r"\b(?P<c>[Qq])uesto stato\b", lambda m: m["c"] + "uesta fase"),
    (r"\b(?P<c>[Qq])uesti stati\b", lambda m: m["c"] + "ueste fasi"),
    (r"\b(?P<c>[Pp])er stato\b", lambda m: m["c"] + "er fase"),
    (r"\b(?P<c>[Cc])ambia stato\b", lambda m: m["c"] + "ambia fase"),
    (r"\b(?P<c>[Aa])ggiungi stati\b", lambda m: m["c"] + "ggiungi fasi"),
    (r"\b(?P<c>[Ss])tati del flusso\b", lambda m: ("F" if m["c"] == "S" else "f") + "asi del flusso"),
    (r"\b(?P<c>[Gg])ruppo di stati\b", lambda m: m["c"] + "ruppo di fasi"),
    (r"\b(?P<c>[Gg])ruppi di stati\b", lambda m: m["c"] + "ruppi di fasi"),
    (r"\b(?P<c>[Gg])ruppo stati\b", lambda m: m["c"] + "ruppo di fasi"),
    (rf"\b(?P<w>[Ff]ase)\s+{AFTER}o\b", lambda m: f"{m['w']} {m[2]}a"),
    (rf"\b(?P<w>[Ff]asi)\s+{AFTER}i\b", lambda m: f"{m['w']} {m[2]}e"),
    # English left inside Italian sentences
    (r"\b[Ww]ork [Ii]tems?\b", "task"),
    # Intake
    (r"\b(?P<c>[Ll])'accoglienza\b", lambda m: ("Le" if m["c"] == "L" else "le") + " richieste in arrivo"),
    (r"\b(?P<c>[Dd])ell'accoglienza\b", lambda m: m["c"] + "elle richieste in arrivo"),
    (r"\b(?P<c>[Pp])er l'accoglienza\b", lambda m: m["c"] + "er le richieste in arrivo"),
    (r"\bAccoglienza\b", "Richieste in arrivo"),
    (r"\baccoglienza\b", "richieste in arrivo"),
    (r"\bIntake\b", "Richieste in arrivo"),
    # Plane's assignees are the executors: the task also has a responsible person and reviewers
    (r"\b(?P<c>[Aa])ssegnatari\b", lambda m: ("E" if m["c"] == "A" else "e") + "secutori"),
    (r"\b(?P<c>[Aa])ssegnatario\b", lambda m: ("E" if m["c"] == "A" else "e") + "secutore"),
    (r"\be (?=esecutor)", "ed "),
    # Plane's priority is the urgency, with Asana's words and days (Rick, 22 October); "alta priorità"
    # and "dare priorità" are common words, not the field
    (r"\bPriorità\b", "Urgenza"),
    (r"(?<!alta )(?<!dare )(?<!di )(?<!le )\bpriorità\b", "urgenza"),
]
COMPILED = [(re.compile(pattern), replacement) for pattern, replacement in RULES]


def _cap(word):
    return lambda m: (word[0].upper() + word[1:]) if m["c"].isupper() else word


# Modulo (masculine) becomes sezione (feminine): articles, prepositions and agreements first.
SECTION_RULES = [
    (r"\b(?P<c>[Nn])essun [Mm]odulo archiviato\b", _cap("nessuna sezione archiviata")),
    (r"\b(?P<c>[Nn])essun [Mm]odulo\b", _cap("nessuna sezione")),
    (r"\b(?P<c>[Uu])n [Mm]odulo\b", _cap("una sezione")),
    (r"\b(?P<c>[Ii])l tuo primo [Mm]odulo\b", _cap("la tua prima sezione")),
    (r"\b(?P<c>[Ii])l [Mm]odulo\b", _cap("la sezione")),
    (r"\b(?P<c>[Ii]) [Mm]oduli\b", _cap("le sezioni")),
    (r"\b(?P<c>[Dd])ei [Mm]oduli\b", _cap("delle sezioni")),
    (r"\b(?P<c>[Dd])el [Mm]odulo\b", _cap("della sezione")),
    (r"\b(?P<c>[Aa])i [Mm]oduli\b", lambda m: ("Alle" if m["c"] == "A" else "alle") + (" Sezioni" if m[0].endswith("Moduli") else " sezioni")),
    (r"\b(?P<c>[Aa])l [Mm]odulo\b", _cap("alla sezione")),
    (r"\b(?P<c>[Nn])el [Mm]odulo\b", _cap("nella sezione")),
    (r"\b(?P<c>[Dd])al [Mm]odulo\b", _cap("dalla sezione")),
    (r"\b(?P<c>[Qq])uesto [Mm]odulo\b", _cap("questa sezione")),
    (r"\b(?P<c>[Nn])uovo [Mm]odulo\b", _cap("nuova sezione")),
    (r"\b(?P<c>[Mm])odulo (?P<w>archiviato|eliminato|copiato)\b", lambda m: ("Sezione " if m["c"] == "M" else "sezione ") + m["w"][:-1] + "a"),
    (r"\b(?P<c>[Mm])oduli (?P<w>completati|annullati)\b", lambda m: ("Sezioni " if m["c"] == "M" else "sezioni ") + m["w"][:-1] + "e"),
    (r"\b(?P<w>[Ss]ezioni)( non)? sono (?P<p>\w+(?:at|it|ut))i\b", lambda m: f"{m['w']}{m[2] or ''} sono {m['p']}e"),
    (r"\bModuli\b", "Sezioni"),
    (r"\bModulo\b", "Sezione"),
    (r"\bmoduli\b", "sezioni"),
    (r"\bmodulo\b", "sezione"),
]
SECTION_COMPILED = [(re.compile(pattern), replacement) for pattern, replacement in SECTION_RULES]


def apply_glossary(text, key=""):
    for pattern, replacement in COMPILED:
        text = pattern.sub(replacement, text)
    if not FORM_KEYS.search(key):
        for pattern, replacement in SECTION_COMPILED:
            text = pattern.sub(replacement, text)
    return text


def walk(node, change, path=""):
    if isinstance(node, dict):
        return {key: walk(value, change, f"{path}.{key}" if path else key) for key, value in node.items()}
    if isinstance(node, str):
        return change(node, path)
    return node


def main():
    exact = json.loads(EXACT.read_text(encoding="utf-8")) if EXACT.exists() else {}
    checking = "--verifica" in sys.argv
    changed_files, changed_texts, problems = 0, 0, []
    for path in sorted(LOCALE.glob("*.json")):
        if path.name in SKIP:
            continue
        original = json.loads(path.read_text(encoding="utf-8"))
        counter = [0]

        def change(text, key, name=path.name):
            new = exact.get(f"{name}:{key}", apply_glossary(text, f"{name}:{key}"))
            if new != text:
                counter[0] += 1
            for pattern, use in FORBIDDEN:
                if pattern.pattern.startswith("\\bmodul") and FORM_KEYS.search(f"{name}:{key}"):
                    continue
                if pattern.search(new):
                    problems.append(f"{name}: {key} ({pattern.pattern} -> {use}): {new[:90]}")
            return new

        updated = walk(original, change)
        if counter[0] and not checking:
            path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed_files += 1
            changed_texts += counter[0]
        elif counter[0]:
            problems.append(f"{path.name}: {counter[0]} testi non ancora con il glossario (rilanciare lo script)")
    if not checking:
        print(f"Glossario applicato: {changed_texts} testi in {changed_files} file di traduzione.")
    for problem in problems:
        print(f"  Fuori glossario: {problem}")
    if problems:
        sys.exit(1)
    print("Verifica: i testi italiani usano le parole del glossario.")


if __name__ == "__main__":
    main()
