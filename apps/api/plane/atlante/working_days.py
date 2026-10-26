# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Working days for internal deadlines (docs/specifica/08-fasi-dei-contenuti.md, section 9): Saturdays,
Sundays and holidays are skipped. The client's 15 days to approve are calendar days, as in the contract.

Holidays: the Italian national ones, Easter Monday included, San Francesco (4 October, national
holiday from 2026, law 151 of 8 October 2025) and San Giovanni (24 June), the patron saint of Turin,
where Zeta3 works.
"""

from datetime import date, timedelta
from functools import cache

FIXED_HOLIDAYS = {
    (1, 1),  # Capodanno
    (1, 6),  # Epifania
    (4, 25),  # Liberazione
    (5, 1),  # Festa del lavoro
    (6, 2),  # Festa della Repubblica
    (6, 24),  # San Giovanni, patrono di Torino
    (8, 15),  # Ferragosto
    (11, 1),  # Ognissanti
    (12, 8),  # Immacolata
    (12, 25),  # Natale
    (12, 26),  # Santo Stefano
}
# Holidays that start in a given year: (month, day) -> first year.
NEW_HOLIDAYS = {(10, 4): 2026}  # San Francesco, legge 8 ottobre 2025 n. 151


def easter(year):
    """Easter Sunday (Gregorian calendar, Meeus/Jones/Butcher algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741 (the algorithm's own name)
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


@cache
def holidays(year):
    fixed = FIXED_HOLIDAYS | {day for day, first in NEW_HOLIDAYS.items() if year >= first}
    return {date(year, month, day) for month, day in fixed} | {easter(year) + timedelta(days=1)}


def is_working_day(day):
    return day.weekday() < 5 and day not in holidays(day.year)


def add_working_days(start, days):
    """The day that comes `days` working days after `start` (before it, if days is negative)."""
    step = 1 if days >= 0 else -1
    day, left = start, abs(days)
    while left:
        day += timedelta(days=step)
        if is_working_day(day):
            left -= 1
    return day
