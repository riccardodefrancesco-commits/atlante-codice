# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Searches for passwords and keys before they reach git (docs/regole/sicurezza.md, level 1 point 5).

Two searches, both needed:
- Gitleaks (MIT license): the known shapes of keys, tokens and passwords;
- the real secrets of this Mac (atlante/locale/segreti.json and the .env files): they must never
  appear in a saved file, whatever their shape.

Usage, from the repository root:
    python3 -I atlante/script/controllo-segreti.py --salvataggio   # what is being saved (git commit)
    python3 -I atlante/script/controllo-segreti.py --tutto         # all our saves since Plane's base
    python3 -I atlante/script/controllo-segreti.py --cartella DIR  # a copy about to be published

It never prints a secret value. It exits with 1 when it finds something.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Plane's commit Atlante starts from (atlante/aggiornamenti.md): only our saves come after it.
PLANE_BASE = "6c16585"
ENV_FILES = [ROOT / ".env"] + [ROOT / "apps" / app / ".env" for app in ("api", "web", "space", "admin", "live")]
# The secrets of a test server, when they are written on this Mac for a rehearsal (atlante/server/crea-segreti.sh).
ENV_FILES += [ROOT / "atlante" / "server" / name for name in (".env", "api.env", "live.env")]
# The passwords of the test accounts: between backticks in the local credentials file.
CREDENTIALS = ROOT / "atlante" / "locale" / "credenziali-prova.md"
# Placeholders in Plane's own files, unchanged and already public in Plane's repository: not secrets.
PLANE_EXAMPLES = ROOT / "atlante" / "sicurezza" / ".gitleaksignore"
SECRET_WORDS = ("PASSWORD", "SECRET", "KEY", "TOKEN")


def git(*args, binary=False):
    output = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout
    return output if binary else output.decode("utf-8", "replace")


def local_secrets():
    """The secret values of this Mac, at least 8 characters long (shorter ones are not secrets)."""
    values = set()
    secrets_file = ROOT / "atlante" / "locale" / "segreti.json"
    if secrets_file.exists():
        values.update(str(v) for v in json.loads(secrets_file.read_text()).values())
    for env in ENV_FILES:
        if not env.exists():
            continue
        for line in env.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and any(word in key.upper() for word in SECRET_WORDS):
                values.add(value.strip().strip("\"'"))
    if CREDENTIALS.exists():
        values.update(re.findall(r"`([^`\s]+)`", CREDENTIALS.read_text()))
    # A value written in the public examples is not a secret (API_KEY_RATE_LIMIT=60/minute has KEY in its name).
    public = "".join(path.read_text() for path in [ROOT / ".env.example", *ROOT.glob("apps/*/.env.example")])
    return {v for v in values if len(v) >= 8 and v not in public}


def gitleaks(args, mode="git", cwd=ROOT):
    if shutil.which("gitleaks") is None:
        sys.exit("Ricerca di password e chiavi: manca Gitleaks. Installalo con: brew install gitleaks")
    result = subprocess.run(
        ["gitleaks", mode, "--no-banner", "--redact", "--verbose", "--log-level", "error", "--exit-code", "1", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        sys.exit(f"Ricerca di password e chiavi: Gitleaks non è riuscito a controllare.\n{result.stderr}")
    # With --redact the report says rule, file and line, never the value.
    keep = ("RuleID", "File", "Line", "Commit")
    report = [line.strip() for line in (result.stdout + result.stderr).splitlines() if line.strip().startswith(keep)]
    return result.returncode == 1, "\n".join(report)


def added_lines(diff):
    return "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))


def folder_text(folder):
    """Every text file of a folder, one after the other (binary files do not hold the secrets we look for)."""
    parts = []
    for path in sorted(Path(folder).rglob("*")):
        if path.is_file() and path.stat().st_size < 5_000_000:
            data = path.read_bytes()
            if b"\0" not in data[:4096]:
                parts.append(data.decode("utf-8", "replace"))
    return "\n".join(parts)


def main():
    folder = sys.argv[2] if len(sys.argv) == 3 and sys.argv[1] == "--cartella" else None
    if folder is None and (len(sys.argv) != 2 or sys.argv[1] not in ("--salvataggio", "--tutto")):
        sys.exit(__doc__)
    saving = sys.argv[1] == "--salvataggio"
    problems = []

    if folder is not None:
        # Paths as in the repository, so the known examples of Plane's own files are recognized.
        found, report = gitleaks(["--gitleaks-ignore-path", str(PLANE_EXAMPLES), "."], mode="dir", cwd=folder)
        texts = {"nella copia da pubblicare": folder_text(folder)}
    elif saving:
        names = [n for n in git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split("\0") if n]
        for name in names:
            # Never saved, even when forced with git add -f.
            local_env = Path(name).name.startswith(".env") and not name.endswith(".env.example")
            server_env = name.startswith("atlante/server/") and name.endswith(".env")
            if local_env or server_env or name.startswith("atlante/locale/"):
                problems.append(f"{name}: file di impostazioni locali, non si salva mai in git")
        found, report = gitleaks(["--pre-commit", "--staged"])
        texts = {"nelle modifiche da salvare": added_lines(git("diff", "--cached", "-U0", "--no-color"))}
    else:
        found, report = gitleaks([f"--log-opts={PLANE_BASE}..HEAD"])
        if not found:
            found, report = gitleaks(["--pre-commit"])  # changes not saved yet
        texts = {
            "nei nostri salvataggi": added_lines(git("log", "-p", "--no-color", "-U0", f"{PLANE_BASE}..HEAD")),
            "nelle modifiche non ancora salvate": added_lines(git("diff", "-U0", "--no-color")),
        }
    if found:
        problems.append("Gitleaks ha trovato qualcosa che sembra una password o una chiave:\n      " + report.replace("\n", "\n      "))

    secrets = local_secrets()
    for where, text in texts.items():
        hits = sum(1 for value in secrets if value in text)
        if hits:
            what = "un segreto di questo Mac compare" if hits == 1 else f"{hits} segreti di questo Mac compaiono"
            problems.append(f"{what} {where} (i valori non si stampano)")

    if problems:
        print("Ricerca di password e chiavi: TROVATO qualcosa. Ci si ferma qui.")
        for problem in problems:
            print(f"  - {problem}")
        print("Togli il segreto dal file (va solo nei .env o in atlante/locale/) e riprova.")
        sys.exit(1)
    known = f"{len(secrets)} segreti di questo Mac" if secrets else "nessun segreto locale da cercare"
    print(f"Ricerca di password e chiavi: niente trovato (Gitleaks e {known}).")


if __name__ == "__main__":
    main()
