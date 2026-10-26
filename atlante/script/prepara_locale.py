# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Prepares the local settings to run Atlante on a Mac for testing.

Usage, from the repository root:
    python3 -I atlante/script/prepara_locale.py

- Creates the .env files from Plane's .env.example files, if missing.
- Replaces Plane's sample passwords with random values, the same in every file.
- Adds the Atlante settings (test environment, telemetry endpoint to nowhere).
- Writes the test credentials in atlante/locale/credenziali-prova.md.

Secrets never leave this Mac: .env files and atlante/locale/ are excluded from git.
The script prints no secret values. Re-running it keeps the same values.
"""

import json
import secrets
import shutil
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "atlante" / "locale"
SECRETS_FILE = LOCAL / "segreti.json"
SERVICES = ["", "web", "api", "space", "admin", "live"]


def env_path(service):
    return ROOT / ".env" if service == "" else ROOT / "apps" / service / ".env"


def random_lower(n):
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def load_or_create_secrets():
    if SECRETS_FILE.exists():
        return json.loads(SECRETS_FILE.read_text())
    values = {
        "postgres_password": secrets.token_urlsafe(24),
        "rabbitmq_password": secrets.token_urlsafe(24),
        "s3_access_key": random_lower(16),
        "s3_secret_key": secrets.token_urlsafe(32),
        "live_secret": secrets.token_urlsafe(36),
        "django_secret": random_lower(50),
        "test_password": secrets.token_urlsafe(15),
    }
    LOCAL.mkdir(parents=True, exist_ok=True)
    SECRETS_FILE.write_text(json.dumps(values, indent=2))
    SECRETS_FILE.chmod(0o600)
    return values


def set_var(path, key, value):
    lines = path.read_text().splitlines()
    new_line = f'{key}="{value}"'
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)
    path.write_text("\n".join(lines) + "\n")


def main():
    for service in SERVICES:
        target = env_path(service)
        example = target.with_name(".env.example")
        if not target.exists():
            if not example.exists():
                sys.exit(f"Manca {example.relative_to(ROOT)}")
            shutil.copyfile(example, target)

    s = load_or_create_secrets()

    shared = {
        "POSTGRES_PASSWORD": s["postgres_password"],
        "RABBITMQ_PASSWORD": s["rabbitmq_password"],
        "AWS_ACCESS_KEY_ID": s["s3_access_key"],
        "AWS_SECRET_ACCESS_KEY": s["s3_secret_key"],
    }
    for key, value in shared.items():
        set_var(env_path(""), key, value)
        set_var(env_path("api"), key, value)

    api = {
        "SECRET_KEY": s["django_secret"],
        "LIVE_SERVER_SECRET_KEY": s["live_secret"],
        # Atlante: invented data allowed only here.
        "ATLANTE_AMBIENTE": "prova",
        "ATLANTE_PASSWORD_PROVA": s["test_password"],
        # Atlante: even a forgotten telemetry call goes nowhere.
        "OTLP_ENDPOINT": "http://127.0.0.1:9",
    }
    for key, value in api.items():
        set_var(env_path("api"), key, value)
    set_var(env_path("live"), "LIVE_SERVER_SECRET_KEY", s["live_secret"])
    # Atlante: the live server answers only this Mac, not the whole network.
    set_var(env_path("live"), "LISTEN_HOST", "127.0.0.1")

    credentials = LOCAL / "credenziali-prova.md"
    # The accounts of the online trial (credenziali-collaudo.py) are the same on the server: they stay.
    old = credentials.read_text() if credentials.exists() else ""
    trial = old[old.index("## Zeta3 Collaudo") :] if "## Zeta3 Collaudo" in old else ""
    credentials.write_text(
        "# Credenziali di prova di Atlante (solo su questo Mac)\n\n"
        "Solo persone inventate. Non usare mai queste credenziali per dati veri.\n\n"
        f"- Password di tutte le persone di prova: `{s['test_password']}`\n"
        "- Atlante: http://localhost:3000\n"
        "- Pannello amministratore: http://localhost:3001/god-mode/\n\n"
        "| Persona | Email | Ruolo |\n| --- | --- | --- |\n"
        "| Admin Prova | admin@esempio.it | Amministratore dello spazio e dell'installazione |\n"
        "| Anna Prova | anna@esempio.it | Amministratrice, account e project manager |\n"
        "| Bruno Prova | bruno@esempio.it | Membro, social media manager |\n"
        "| Carla Prova | carla@esempio.it | Membro, grafica |\n"
        "| Dario Prova | dario@esempio.it | Membro, videomaker |\n"
        "| Elena Prova | elena@esempio.it | Membro, editor video |\n"
        "| Fabio Ospite | fabio@esempio.it | Ospite (cliente finto), solo nel progetto ALFA |\n"
        + (f"\n{trial}" if trial else "")
    )
    credentials.chmod(0o600)

    print("Impostazioni locali pronte: .env di root, api, web, space, admin, live.")
    print("Credenziali di prova in atlante/locale/credenziali-prova.md (escluso da git).")


if __name__ == "__main__":
    main()
