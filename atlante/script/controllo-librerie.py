# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Checks Atlante's libraries against the public database of known problems (OSV), with
OSV-Scanner (Apache 2.0 license, by Google). docs/regole/sicurezza.md, level 1 points 6 and 10.

What goes out: only the names and versions of the libraries, to api.osv.dev. No data of Zeta3
(decided with Rick on 21 October 2026).

The problems already known and evaluated are in atlante/sicurezza/librerie-note.json, each with
the reason: they do not block. A new problem, or a known one in another library, blocks.

Usage, from the repository root:
    python3 -I atlante/script/controllo-librerie.py            # controlla-tutto: blocks only new problems
    python3 -I atlante/script/controllo-librerie.py --elenco   # the Monday check: all problems, known and new
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWN_FILE = ROOT / "atlante" / "sicurezza" / "librerie-note.json"
# Lockfile: (short name, as it reads in "N libraries of ...").
LOCKFILES = {
    "pnpm-lock.yaml": ("interfaccia", "dell'interfaccia"),
    "apps/api/uv.lock": ("server", "del server"),
    "atlante/immagini/package-lock.json": ("strumento delle immagini", "dello strumento delle immagini"),
}


def number(n):
    return f"{n:,}".replace(",", ".")


def severity(score):
    if score >= 9:
        return "critica"
    if score >= 7:
        return "alta"
    if score >= 4:
        return "media"
    return "bassa" if score > 0 else "senza voto"


def scan():
    if shutil.which("osv-scanner") is None:
        sys.exit("Controllo delle librerie: manca OSV-Scanner. Installalo con: brew install osv-scanner")
    lockfiles = [path for path in LOCKFILES if (ROOT / path).exists()]
    with tempfile.TemporaryDirectory() as folder:
        output = Path(folder) / "osv.json"
        args = ["osv-scanner", "scan", "source", "--format", "json", "--output-file", str(output)]
        for path in lockfiles:
            args += ["-L", path]
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        # 0: no problems, 1: problems found. Anything else means the check did not happen.
        if result.returncode not in (0, 1) or not output.exists():
            sys.exit(
                "Controllo delle librerie: non riuscito (serve la connessione a internet).\n"
                + (result.stderr.strip().splitlines() or [""])[-1]
            )
        data = json.loads(output.read_text())
    counted = {}
    for line in (result.stdout + result.stderr).splitlines():
        # "Scanned <path> file and found N packages"
        if line.startswith("Scanned ") and " and found " in line:
            path = line.split("Scanned ", 1)[1].split(" file and found ")[0]
            counted[str(Path(path).relative_to(ROOT))] = int(line.rsplit(" and found ", 1)[1].split()[0])
    problems = []
    for item in data.get("results", []):
        source = str(Path(item["source"]["path"]).relative_to(ROOT))
        for package in item.get("packages", []):
            details = {v["id"]: v for v in package.get("vulnerabilities", [])}
            for group in package.get("groups", []):
                ids = group["ids"]
                main = next((details[i] for i in ids if i in details), {})
                problems.append(
                    {
                        "ids": ids,
                        "libreria": package["package"]["name"],
                        "versione": package["package"]["version"],
                        "dove": LOCKFILES.get(source, (source,))[0],
                        "gravita": severity(float(group.get("max_severity") or 0)),
                        "titolo": main.get("summary", ""),
                    }
                )
    return counted, problems


def main():
    listing = sys.argv[1:] == ["--elenco"]
    if sys.argv[1:] not in ([], ["--elenco"]):
        sys.exit(__doc__)
    known = json.loads(KNOWN_FILE.read_text())["problemi"]
    known_keys = {(k["libreria"], i) for k in known for i in k["ids"]}
    counted, problems = scan()

    new = [p for p in problems if not any((p["libreria"], i) in known_keys for i in p["ids"])]
    old = [p for p in problems if p not in new]
    solved = [k for k in known if not any(k["libreria"] == p["libreria"] and set(k["ids"]) & set(p["ids"]) for p in problems)]

    checked = ", ".join(f"{number(n)} {LOCKFILES.get(path, (path, path))[1]}" for path, n in counted.items())
    print(f"Controllo delle librerie: {checked}.")
    print(f"  Problemi noti già valutati: {len(old)}. Problemi nuovi: {len(new)}. Noti e ora risolti: {len(solved)}.")

    def show(items, title):
        if items:
            print(f"  {title}:")
            for p in sorted(items, key=lambda p: (p["dove"], p["libreria"])):
                print(f"    - {p['libreria']} {p['versione']} ({p['dove']}), gravità {p['gravita']}: {p['titolo']} [{p['ids'][0]}]")

    show(new, "NUOVI, da valutare prima di salvare")
    if listing:
        reasons = {(k["libreria"], i): k["perche"] for k in known for i in k["ids"]}
        for p in old:
            p["titolo"] += " Valutazione: " + next(reasons[(p["libreria"], i)] for i in p["ids"] if (p["libreria"], i) in reasons)
        show(old, "Già noti")
        for k in solved:
            print(f"  Risolto: {k['libreria']} [{k['ids'][0]}], si può togliere da {KNOWN_FILE.relative_to(ROOT)}")
    if new:
        print(f"  Ogni problema nuovo va valutato e, se si accetta, scritto in {KNOWN_FILE.relative_to(ROOT)} con il perché.")
        sys.exit(1)


if __name__ == "__main__":
    main()
