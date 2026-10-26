# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A short code for every error (docs/regole/controllo-e-diagnosi.md, point 1; decided by Rick on
22 October 2026, docs/proposta-codici-errore.md).

Whoever meets an error sees "Qualcosa non ha funzionato. Codice: ATL-7F3K. Riprova o segnalalo.",
and the same code is in the server log with page, action, the person's id, time and error. The log
never gets passwords, request bodies, task contents or clients' data: only what Plane already logs
about the error itself, plus these few fields.
"""

import secrets

from crum import get_current_request

# No 0/O and 1/I: the code is read aloud and typed by hand.
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
PREFIX = "ATL-"
LENGTH = 4


def new_code():
    return PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def message(code):
    return f"Qualcosa non ha funzionato. Codice: {code}. Riprova o segnalalo."


def log_fields(code):
    """What goes into the log line with the code: never the request body or query values."""
    request = get_current_request()
    user = getattr(request, "user", None) if request is not None else None
    return {
        "codice": code,
        "path": getattr(request, "path", None),
        "method": getattr(request, "method", None),
        "user_id": str(user.id) if getattr(user, "is_authenticated", False) else None,
    }
