# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Diagnosis in one command (docs/regole/controllo-e-diagnosi.md, point 2).

Checks every part of Atlante, the free disk space, the errors and the slowest requests of the
last 24 hours, and writes a report in Italian: what works, what does not, what to check.
Claude Code runs it when Rick says "qualcosa non va" and in the Monday check.

Usage, from the repository root (atlante/script/diagnosi.sh does the same):
    python3 -I atlante/script/diagnosi.py

The report is also saved in atlante/locale/diagnosi/ (excluded from git): it never contains
passwords, people's ids, addresses, or the content of tasks. It exits with 1 when something is red.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", os.environ.get("ATLANTE_COMPOSE_FILE", "docker-compose-local.yml")]
SERVICES = {
    "plane-db": "Database",
    "plane-redis": "Memoria rapida",
    "plane-mq": "Code di lavoro",
    "plane-minio": "Archivio dei file",
    "api": "Server",
    "worker": "Lavori in sottofondo",
    "beat-worker": "Lavori a orario fisso",
}
LOGGED = ["api", "worker", "beat-worker"]
# Port: what answers there. None of them must answer the whole network (zeta3-progetti#10).
PORTS = {
    5432: "database",
    6379: "memoria rapida",
    5672: "code di lavoro",
    15672: "pannello delle code",
    9000: "archivio dei file",
    9090: "pannello dell'archivio",
    8000: "server",
    3000: "interfaccia",
    3001: "pannello amministratore",
    3002: "pagine pubbliche",
    3100: "server delle pagine condivise",
}
PAGES = {
    "Interfaccia": "http://127.0.0.1:3000/",
    "Pannello amministratore": "http://127.0.0.1:3001/god-mode/",
    "Pagine pubbliche": "http://127.0.0.1:3002/",
    "Server delle pagine condivise": "http://127.0.0.1:3100/live/health/",
}
DISK_LIMIT = 80  # percent used, as in docs/regole/controllo-e-diagnosi.md point 5
SLOW_MS = 1000
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
NUMBER = re.compile(r"\b\d+\b")
QUERY = re.compile(r"\?.*$")

OK, WARN, BAD = "ok", "attenzione", "non va"
results = []  # (state, part, detail)
running_since = {}  # service -> start time of its container


def note(state, part, detail):
    results.append((state, part, detail))


def run(args, timeout=30):
    try:
        done = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return done.returncode, (done.stdout + done.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)


def number(n):
    return f"{n:,}".replace(",", ".")


def decimal(x, digits=2):
    return f"{x:.{digits}f}".replace(".", ",")


def times(n, one, many):
    return f"{number(n)} {one if n == 1 else many}"


def size(text):
    """Docker and Valkey sizes ("3.362GB", "1.10M") the Italian way ("3,4 GB", "1,1 MB")."""
    match = re.match(r"^([\d.]+)\s*([kKMGT]?)i?B?$", text.strip())
    if not match:
        return text
    unit = {"": "byte", "k": "kB", "K": "kB", "M": "MB", "G": "GB", "T": "TB"}[match.group(2)]
    return f"{decimal(float(match.group(1)), 1)} {unit}"


def utc_time(text):
    """Docker's times ("2026-10-20T22:21:28.123456789Z"), without the fractions of a second."""
    return datetime.fromisoformat(text.strip().rstrip("Z").partition(".")[0] + "+00:00")


def seconds_text(seconds):
    return "in meno di un decimo di secondo" if seconds < 0.1 else f"in {decimal(seconds)} secondi"


def since(start):
    minutes = int((datetime.now(start.tzinfo) - start).total_seconds() // 60)
    if minutes < 60:
        return times(minutes, "minuto", "minuti")
    if minutes < 48 * 60:
        return times(minutes // 60, "ora", "ore")
    return times(minutes // (24 * 60), "giorno", "giorni")


def env_value(path, key):
    for line in (ROOT / path).read_text().splitlines() if (ROOT / path).exists() else []:
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def get(url, timeout=10):
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read(), time.monotonic() - start
    except Exception as error:  # the report says what went wrong, it never stops
        return getattr(error, "code", None), b"", time.monotonic() - start


def check_containers():
    code, out = run(["docker", "info", "--format", "{{.ServerVersion}}"])
    if code != 0:
        note(BAD, "Docker", "Docker non risponde: aprire Docker Desktop. Senza Docker non funziona niente.")
        return False
    code, out = run(COMPOSE + ["ps", "--all", "--format", "json"])
    found = {}
    for line in out.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        found[item.get("Service")] = item
    for service, name in SERVICES.items():
        item = found.get(service)
        if item is None:
            note(BAD, name, f"il contenitore {service} non esiste: docker compose -f docker-compose-local.yml up -d")
        elif item.get("State") != "running":
            note(BAD, name, f"fermo: si riaccende con docker compose -f docker-compose-local.yml up -d {service}")
        else:
            code, out = run(["docker", "inspect", "--format", "{{.RestartCount}} {{.State.StartedAt}}", item["Name"]])
            restarts, _, started = out.partition(" ")
            if code == 0:
                running_since[service] = utc_time(started)
            if restarts.isdigit() and int(restarts) > 0:
                note(WARN, name, f"acceso, ma ripartito da solo {times(int(restarts), 'volta', 'volte')}: guardare gli errori sotto")
    return True


def alive(service):
    return f"; in funzione da {since(running_since[service])}" if service in running_since else ""


def check_parts():
    user = env_value(".env", "POSTGRES_USER") or "plane"
    database = env_value(".env", "POSTGRES_DB") or "plane"
    code, out = run(COMPOSE + ["exec", "-T", "plane-db", "pg_isready", "-U", user, "-d", database])
    if code == 0:
        code, out_size = run(COMPOSE + ["exec", "-T", "plane-db", "psql", "-U", user, "-d", database, "-tAc",
                                    "select pg_size_pretty(pg_database_size(current_database()))"])
        note(OK, "Database", f"risponde; occupa {size(out_size.strip()) if code == 0 else '?'}{alive('plane-db')}")
    else:
        note(BAD, "Database", "non risponde alle richieste")

    code, out = run(COMPOSE + ["exec", "-T", "plane-redis", "valkey-cli", "info", "memory"])
    memory = re.search(r"used_memory_human:(\S+)", out)
    if code == 0 and memory:
        note(OK, "Memoria rapida", f"risponde; usa {size(memory.group(1))}{alive('plane-redis')}")
    else:
        note(BAD, "Memoria rapida", "non risponde")

    vhost = env_value(".env", "RABBITMQ_VHOST") or "/"
    code, out = run(COMPOSE + ["exec", "-T", "plane-mq", "rabbitmqctl", "-q", "list_queues", "-p", vhost, "name", "messages"])
    if code == 0:
        waiting = sum(int(parts[-1]) for parts in (l.split() for l in out.splitlines()) if parts and parts[-1].isdigit())
        state = WARN if waiting > 100 else OK
        note(state, "Code di lavoro", f"rispondono; {times(waiting, 'lavoro', 'lavori')} in attesa" + (" (tanti: i lavori in sottofondo non stanno al passo)" if state == WARN else "") + alive("plane-mq"))
    else:
        note(BAD, "Code di lavoro", "non rispondono")

    status, _, _ = get("http://127.0.0.1:9000/minio/health/live")
    note(OK if status == 200 else BAD, "Archivio dei file", ("risponde" + alive("plane-minio")) if status == 200 else "non risponde")

    status, body, seconds = get("http://127.0.0.1:8000/api/instances/")
    if status == 200:
        note(OK if seconds < 1 else WARN, "Server", f"risponde {seconds_text(seconds)}{alive('api')}")
        try:
            signup = json.loads(body)["config"].get("enable_signup")
        except (ValueError, KeyError):
            signup = None
        if signup:
            note(BAD, "Registrazione libera", "accesa: chiunque raggiunga il server può crearsi un account (zeta3-progetti#10)")
        else:
            note(OK, "Registrazione libera", "spenta: si entra solo su invito")
    else:
        note(BAD, "Server", f"non risponde (codice {status})")

    code, out = run(COMPOSE + ["exec", "-T", "worker", "celery", "-A", "plane", "inspect", "ping", "--timeout", "5"], timeout=40)
    note(OK if "pong" in out else BAD, "Lavori in sottofondo", ("rispondono" + alive("worker")) if "pong" in out else "non rispondono al controllo")
    if "beat-worker" in running_since:
        note(OK, "Lavori a orario fisso", f"in funzione da {since(running_since['beat-worker'])}")

    for name, url in PAGES.items():
        status, _, seconds = get(url)
        if status == 200:
            note(OK, name, f"risponde {seconds_text(seconds)}")
        else:
            note(BAD, name, "non risponde: è acceso pnpm dev?")


def lan_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 9))  # no packet is sent: it only picks the network card
            address = probe.getsockname()[0]
        except OSError:
            return None
    return None if address.startswith("127.") else address


def check_network():
    address = lan_address()
    if address is None:
        note(OK, "Porte verso la rete", "il Mac non è collegato a una rete: niente da controllare")
        return
    open_ports = []
    for port, name in PORTS.items():
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex((address, port)) == 0:
                open_ports.append(f"{port} ({name})")
    if open_ports:
        note(BAD, "Porte verso la rete", "rispondono a tutta la rete Wi-Fi: " + ", ".join(open_ports) + ". Devono rispondere solo al Mac (127.0.0.1)")
    else:
        note(OK, "Porte verso la rete", f"nessuna delle {len(PORTS)} porte di Atlante risponde agli altri dispositivi della rete")


def check_disk():
    path = "/System/Volumes/Data" if Path("/System/Volumes/Data").exists() else "/"
    usage = shutil.disk_usage(path)
    used = 100 * (usage.total - usage.free) / usage.total
    free = usage.free / 1024**3
    state = BAD if used > 90 else WARN if used >= DISK_LIMIT else OK
    detail = f"liberi {free:.0f} GB su {usage.total / 1024**3:.0f} ({used:.0f}% usato)"
    if state != OK:
        detail += f": oltre il limite dell'{DISK_LIMIT}%, liberare spazio (per esempio la cache di Docker, sotto)"
    elif used >= DISK_LIMIT - 5:
        detail += f", vicino al limite dell'{DISK_LIMIT}%"
    note(state, "Disco", detail)
    code, out = run(["docker", "system", "df", "--format", "{{.Type}}\t{{.Size}}\t{{.Reclaimable}}"])
    if code == 0:
        names = {"Images": "immagini", "Containers": "contenitori", "Local Volumes": "dati", "Build Cache": "cache di costruzione"}
        parts = [f"{names.get(t, t)} {size(s)}" for t, s, _ in (line.split("\t") for line in out.splitlines() if line.count("\t") == 2)]
        note(OK, "Spazio di Docker", ", ".join(parts))


def normalize(text):
    return NUMBER.sub("N", UUID.sub("{id}", QUERY.sub("", text)))[:140]


def read_logs():
    errors = Counter()
    codes = defaultdict(list)  # error type -> its codes (docs/proposta-codici-errore.md)
    server_errors = Counter()
    slow = defaultdict(list)
    for service in LOGGED:
        code, out = run(COMPOSE + ["logs", "--no-color", "--no-log-prefix", "--since", "24h", service], timeout=60)
        if code != 0:
            continue
        for line in out.splitlines():
            if not line.startswith("{"):
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            level = item.get("levelname")
            if item.get("name") == "plane.api.request":
                path = normalize(item.get("path", ""))
                key = f"{item.get('method')} {path}"
                slow[key].append(int(item.get("duration_ms") or 0))
                if int(item.get("status_code") or 0) >= 500:
                    server_errors[f"{key} (codice {item.get('status_code')})"] += 1
            elif level in ("ERROR", "CRITICAL"):
                message = (item.get("message") or "").splitlines()[0] if item.get("message") else ""
                key = f"{SERVICES.get(service, service)}: {item.get('name')}: {normalize(message)}"
                errors[key] += 1
                if item.get("codice"):
                    codes[key].append(item["codice"])
    return errors, server_errors, slow, codes


def report():
    now = datetime.now()
    errors, server_errors, slow, codes = read_logs()
    total_errors = sum(errors.values()) + sum(server_errors.values())
    coverage = ""
    starts = [running_since[s] for s in LOGGED if s in running_since]
    if starts and (datetime.now(min(starts).tzinfo) - min(starts)).total_seconds() < 24 * 3600:
        coverage = f" (il registro c'è solo da {since(min(starts))}: Docker lo azzera quando un contenitore si ricrea)"
    note(OK if total_errors == 0 else WARN, "Errori delle ultime 24 ore", f"{number(total_errors)}" + (", dettagli sotto" if total_errors else "") + coverage)

    version_file = ROOT / "apps" / "web" / "atlante" / "version.ts"
    found = dict(re.findall(r'export const ATLANTE_(VERSION|STAGE)[^=]*= "([^"]*)"', version_file.read_text())) if version_file.exists() else {}
    version = " ".join(v for v in (found.get("VERSION"), found.get("STAGE")) if v) or "sconosciuta"
    code, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    code, commit = run(["git", "log", "-1", "--format=%h del %cd", "--date=format:%d/%m/%Y"])
    monday = "mai fatto"
    updates = ROOT / "atlante" / "aggiornamenti.md"
    rows = [l for l in updates.read_text().splitlines() if re.match(r"^\| \d", l)] if updates.exists() else []
    if rows:
        monday = rows[-1].split("|")[1].strip()

    lines = [f"# Diagnosi di Atlante, {now.strftime('%d/%m/%Y alle %H:%M')}", ""]
    bad = [r for r in results if r[0] == BAD]
    warn = [r for r in results if r[0] == WARN]
    if bad:
        lines.append(f"**Qualcosa non va:** {times(len(bad), 'punto rosso', 'punti rossi')}, {number(len(warn))} da guardare.")
    elif warn:
        lines.append(f"**Funziona,** con {times(len(warn), 'punto', 'punti')} da guardare.")
    else:
        lines.append("**Tutto funziona.**")
    lines += ["", f"Versione {version}: ramo `{branch}`, salvataggio {commit}. Ultimo controllo del lunedì: {monday}.", ""]

    for title, state in (("Non va", BAD), ("Da guardare", WARN), ("Funziona", OK)):
        items = [r for r in results if r[0] == state]
        if items:
            lines.append(f"## {title}")
            lines += [f"- **{part}:** {detail}" for _, part, detail in items]
            lines.append("")

    if errors or server_errors:
        lines.append("## Errori delle ultime 24 ore, per tipo")
        for text, count in (errors + server_errors).most_common(15):
            last = codes.get(text, [])[-3:]
            with_codes = f" (codici: {', '.join(last)})" if last else ""
            lines.append(f"- {times(count, 'volta', 'volte')}: {text}{with_codes}")
        lines.append("")

    ranking = sorted(((max(v), len(v), sum(v) / len(v), k) for k, v in slow.items()), reverse=True)[:10]
    if ranking:
        requests = sum(len(v) for v in slow.values())
        slow_count = sum(1 for v in slow.values() for ms in v if ms >= SLOW_MS)
        lines.append(f"## Le richieste più lente delle ultime 24 ore ({times(requests, 'richiesta', 'richieste')}, {number(slow_count)} sopra il secondo)")
        for top, count, average, key in ranking:
            lines.append(f"- {decimal(top / 1000)} s al massimo, {decimal(average / 1000)} s in media, {times(count, 'volta', 'volte')}: `{key}`")
        lines.append("")

    lines.append("## Cosa controllare")
    advice = [f"{part}: {detail}" for state, part, detail in results if state in (BAD, WARN)]
    lines += [f"- {a}" for a in advice] if advice else ["- Niente: tutto in ordine."]
    lines.append("")
    lines.append("Il registro degli errori in locale è quello di Docker (console). Non contiene password né contenuto delle task; nel resoconto gli identificativi sono sostituiti da {id}.")
    text = "\n".join(lines) + "\n"

    folder = ROOT / "atlante" / "locale" / "diagnosi"
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / f"diagnosi-{now.strftime('%Y-%m-%d-%H%M')}.md"
    saved.write_text(text)
    print(text)
    print(f"Resoconto salvato in {saved.relative_to(ROOT)}")
    return 1 if bad else 0


def main():
    if check_containers():
        check_parts()
    check_network()
    check_disk()
    sys.exit(report())


if __name__ == "__main__":
    main()
