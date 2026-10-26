# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project names and codes, as decided by Rick on 21 October 2026.

Names (zeta3-progetti#17): as simple and free as possible for whoever writes them, for example
"Delta Vini - Social". Plane refused 21 characters, the dash and the apostrophe among them. Atlante
refuses only what can do harm: < and > (pieces of web pages) anywhere, and = + - @ at the start
(a spreadsheet would read them as a formula when the name is exported).

Codes (zeta3-progetti#18): the first four consonants of the name, in capitals ("Delta Vini - Social"
becomes DLTV); with a number when the code is taken (DLTV2, DLTV3...). Always editable by hand.
"""

import re
import unicodedata

from plane.db.models import Project, ProjectIdentifier

FORBIDDEN_NAME = re.compile(r"[<>]|^\s*[=+\-@]")
VOWELS = frozenset("AEIOU")
CODE_LENGTH = 4
# When the name has no letter or digit at all.
EMPTY_CODE = "PROG"


def is_forbidden_name(name):
    return bool(FORBIDDEN_NAME.search(name or ""))


def code_from_name(name):
    """The first four consonants, in capitals. Accents are dropped (Città gives CTT). With fewer than
    four consonants the code is completed with the other letters and digits, in order."""
    plain = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().upper()
    characters = [c for c in plain if c.isascii() and c.isalnum()]
    consonants = [c for c in characters if c.isalpha() and c not in VOWELS]
    others = [c for c in characters if not (c.isalpha() and c not in VOWELS)]
    code = "".join((consonants + others)[:CODE_LENGTH]) if len(consonants) < CODE_LENGTH else "".join(consonants[:CODE_LENGTH])
    return code or EMPTY_CODE


def first_free(base, taken):
    """base if free, otherwise base2, base3... (codes are compared in capitals)."""
    taken = {code.upper() for code in taken}
    if base not in taken:
        return base
    number = 2
    while f"{base}{number}" in taken:
        number += 1
    return f"{base}{number}"


def suggest_code(workspace_id, name):
    """The code for a new project of this workspace. Codes of archived projects count as taken, like
    the codes Plane keeps in its register of project codes."""
    taken = set(ProjectIdentifier.objects.filter(workspace_id=workspace_id).values_list("name", flat=True))
    taken |= set(Project.objects.filter(workspace_id=workspace_id).values_list("identifier", flat=True))
    return first_free(code_from_name(name), taken)
