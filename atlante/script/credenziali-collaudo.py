#!/usr/bin/env python3
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The accounts of the online trial in the local credentials file (zeta3-progetti, docs/collaudo-0.3.md,
section 1): one strong password for each person, different for everyone, written only in
atlante/locale/credenziali-prova.md (excluded from git). It never prints a password.

    python3 atlante/script/credenziali-collaudo.py --email alessandra=<email di lavoro> [--email ...]
    python3 atlante/script/credenziali-collaudo.py --nuove-password    # new ones for everybody

Run again, it keeps the passwords already there and changes only the emails given. The command
atlante_dati_collaudo reads the same table.
"""

import argparse
import os
import secrets
from datetime import date
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "locale" / "credenziali-prova.md"
SECTION = "## Zeta3 Collaudo"
# Until Rick confirms them, the work emails are guessed as name@ this domain.
DOMAIN = "zeta3.it"
PEOPLE = {"rick": "Rick", "alessandra": "Alessandra", "virginia": "Virginia", "giulia": "Giulia"}
# Without letters and digits that look alike (l, 1, I, O, 0): they are copied by hand.
ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_password():
    """4 groups of 5 characters, about 115 bits."""
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(5)) for _ in range(4))


def read_rows(lines):
    rows, header = {}, None
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = [cell.casefold() for cell in cells]
        elif not set(line.strip()) <= set("|-: "):
            row = dict(zip(header, cells))
            rows[row.get("chi", "")] = row
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", action="append", default=[], metavar="CHI=EMAIL")
    parser.add_argument("--nuove-password", action="store_true")
    args = parser.parse_args()

    text = FILE.read_text(encoding="utf-8") if FILE.exists() else "# Credenziali di prova di Atlante\n"
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(SECTION)), None)
    end = len(lines)
    if start is not None:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    old = read_rows(lines[start:end]) if start is not None else {}

    emails = {}
    for item in args.email:
        who, _, email = item.partition("=")
        if who not in PEOPLE or "@" not in email:
            parser.error(f"--email vuole chi=indirizzo, con chi tra: {', '.join(PEOPLE)}")
        emails[who] = email.strip().lower()

    table = ["| Chi | Nome | Cognome | Email | Password |", "| --- | --- | --- | --- | --- |"]
    guessed = []
    for who, name in PEOPLE.items():
        row = old.get(who, {})
        password = row.get("password", "").strip("`")
        if args.nuove_password or not password:
            password = new_password()
        email = emails.get(who) or row.get("email") or f"{who}@{DOMAIN}"
        if email == f"{who}@{DOMAIN}" and who not in emails:
            guessed.append(who)
        table.append(f"| {who} | {row.get('nome') or name} | {row.get('cognome', '')} | {email} | `{password}` |")

    section = [
        SECTION,
        "",
        f"Collaudo online della 0.3: server di prova e anteprima sul Mac. Password generate il {date.today():%d/%m/%Y}.",
        "Solo qui: mai in chat, nei documenti, nei commit o nelle segnalazioni. Rick le manda a ciascuna, a parte;",
        "al primo accesso ognuna la cambia (Impostazioni del profilo, Sicurezza).",
        *([f"Email ipotizzate, da confermare con Rick: {', '.join(guessed)}."] if guessed else []),
        "",
        *table,
        "",
    ]
    if start is None:
        lines = [*lines, "", *section]
    else:
        lines = [*lines[:start], *section, *lines[end:]]
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    os.chmod(FILE, 0o600)
    print(f"Password pronte per {', '.join(PEOPLE)} in {FILE} (non mostrate qui).")


if __name__ == "__main__":
    main()
