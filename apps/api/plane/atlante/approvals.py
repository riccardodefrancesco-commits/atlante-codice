# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Assaggio F: the client's approval inside the task (Condizioni Generali 3.0, articles 8.2 and 9.1;
docs/specifica/08-fasi-dei-contenuti.md, section 2; design system, table 15).

Until the portal (release 0.10), as decided by Rick on 22 October:
- a task that enters a phase where the work waits for the client is "ready to send"; the 15 calendar
  days start when someone in the team presses "Inviato al cliente". The day of sending does not
  count: sent on 20 October, the client has until 4 November included. The reminder is the twelfth day;
- "Approva" takes the task to the next phase; "Chiedi modifiche" takes it back to the production phase
  with the same urgency, and the revision round goes up if it is a full round (file _2), not a micro
  fix. The rounds included are those of the client's contract; the others are paid;
- from the sixteenth day the content is approved by silent consent, but Atlante does not approve by
  itself: it shows "Silenzio-assenso da confermare" and a person confirms it. The presentations of
  strategy, brand and site need an explicit yes: the task stays where it is;
- the whole team of the project records the client's answer; the history says who did.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from plane.atlante.models import Client, ClientApproval, PhaseBinding
from plane.atlante.phases import (
    _notify,
    _record,
    _state_name,
    italian_date,
    person_name,
    phase_of,
    responsible,
    today,
    work_type,
)
from plane.atlante.services import effective_client_id
from plane.db.models import Issue, State

ANSWER_DAYS, REMINDER_DAY = 15, 12
DEFAULT_ROUNDS = 2  # a task without client: the usual contract
OPEN = (ClientApproval.READY, ClientApproval.WAITING)


def client_of(issue):
    client_id = effective_client_id(issue)
    return Client.objects.filter(pk=client_id).first() if client_id else None


def included_rounds(issue):
    client = client_of(issue)
    return client.included_revisions if client else DEFAULT_ROUNDS


def used_rounds(issue):
    return ClientApproval.objects.filter(issue=issue, status=ClientApproval.CHANGES, counts_round=True).count()


def open_approval(issue):
    """The approval of the task that is ready to send or waits for the client, if any."""
    return ClientApproval.objects.filter(issue=issue, status__in=OPEN).first()


def silent_consent_due(approval, day=None):
    """The client did not answer in time: silent consent, to be confirmed by a person (not for an
    explicit yes)."""
    day = day or today()
    return approval.status == ClientApproval.WAITING and not approval.consent and day > approval.due_on


def phase_entered(issue, phase):
    """Called for every new phase of a task: what was open elsewhere is passed; a phase where the work
    waits for the client makes it ready to send."""
    ClientApproval.objects.filter(issue=issue, status__in=OPEN).exclude(state_id=issue.state_id).update(
        status=ClientApproval.PASSED
    )
    if phase is None or phase.back is None or open_approval(issue) is not None:
        return None
    return ClientApproval.objects.create(
        issue=issue,
        state_id=issue.state_id,
        phase=phase.key,
        consent=phase.consent,
        round=used_rounds(issue) + 1,
    )


def answer_days(sent):
    """(reminder day, last day included) for a work sent on `sent`: the day of sending does not count.
    Sent on 20 October: reminder on 1 November, the client has until 4 November included."""
    return sent + timedelta(days=REMINDER_DAY), sent + timedelta(days=ANSWER_DAYS)


def send(issue, approval, user):
    """ "Inviato al cliente": the 15 days start, from the day after."""
    sent = today()
    approval.status = ClientApproval.WAITING
    approval.sent_on = sent
    approval.sent_by = user
    approval.reminder_on, approval.due_on = answer_days(sent)
    approval.save()
    if approval.consent:
        until = "serve il suo sì, senza silenzio-assenso"
    else:
        until = f"ha tempo fino al {italian_date(approval.due_on)} compreso per rispondere"
    _record(issue, _state_name(issue), f"Inviato al cliente da {person_name(user)}: {until}.")
    return approval


def _target_state(issue, template, phase, approved):
    """Approved: the next phase of the template (a cover is done). Changes: the production phase."""
    keys = [item.key for item in template.phases]
    cover = work_type(issue) == "copertina"
    if approved:
        key = "fatto" if cover else keys[keys.index(phase.key) + 1]
    else:
        key = template.cover_phase if cover and template.cover_phase else phase.back
    binding = PhaseBinding.objects.filter(
        project_id=issue.project_id, phase=key, state__deleted_at__isnull=True
    ).first()
    return State.objects.filter(pk=binding.state_id).first() if binding else None


def approval_target_name(issue, approval):
    """The name of the phase the task goes to if the client approves."""
    template, phase = phase_of(approval.state_id)
    target = _target_state(issue, template, phase, True) if phase else None
    return target.name if target else None


def decide(issue, approval, *, approved, user, note="", counts=True, silent=False):
    """The client's answer, or the silent consent confirmed by a person: the task moves on, or goes
    back, by itself. Returns the approval."""
    template, phase = phase_of(approval.state_id)
    target = _target_state(issue, template, phase, approved) if phase else None
    with transaction.atomic():
        approval.status = (
            ClientApproval.AUTO_APPROVED if silent else ClientApproval.APPROVED if approved else ClientApproval.CHANGES
        )
        approval.decided_at = timezone.now()
        approval.decided_by = user
        approval.next_state = target
        if not approved:
            approval.note = note.strip()
            approval.counts_round = counts
        approval.save()
        where = f" La task passa alla fase {target.name}." if target else ""
        if silent:
            text = (
                f"Approvata per silenzio-assenso: sono passati {ANSWER_DAYS} giorni dall'invio senza risposta del "
                f"cliente (articolo 9.1 delle Condizioni Generali). Confermata da {person_name(user)}.{where}"
            )
        elif approved:
            text = f"Approvata dal cliente, registrato da {person_name(user)}.{where}"
        else:
            included, used = included_rounds(issue), used_rounds(issue)
            asked = f": «{approval.note}»" if approval.note else ""
            if not counts:
                rounds = "Micro correzione: il giro non conta."
            elif used + 1 <= included:
                rounds = f"Comincia il giro di revisione {used + 1} di {included} inclusi."
            else:
                rounds = f"Comincia un giro extra, a pagamento: il contratto comprende {included} giri."
            back = f" La task torna alla fase {target.name} con la stessa urgenza." if target else ""
            text = f"Il cliente ha chiesto modifiche{asked}, registrato da {person_name(user)}. {rounds}{back}"
        _record(issue, _state_name(issue), text)
        if target is not None:
            issue.state = target
            issue.save()
    return approval


def daily(day=None, workspace_id=None):
    """Every morning: the reminder of the twelfth day and, from the sixteenth, the notice to the
    responsible person: silent consent to confirm, or an explicit yes that is late. Atlante never
    approves by itself. Returns what it did, for the log. With workspace_id, only that workspace
    (the mornings of invented data being prepared)."""
    day = day or today()
    done = {"reminders": 0, "to_confirm": 0, "late": 0}
    waiting = ClientApproval.objects.filter(status=ClientApproval.WAITING)
    if workspace_id is not None:
        waiting = waiting.filter(issue__workspace_id=workspace_id)
    for approval in waiting:
        issue = Issue.issue_objects.filter(pk=approval.issue_id).first()
        if issue is None:
            continue
        member, _ = responsible(issue)
        if day > approval.due_on:
            if approval.late_notice_at is not None:
                continue
            approval.late_notice_at = timezone.now()
            approval.save(update_fields=["late_notice_at", "updated_at"])
            if approval.consent:
                text = (
                    f"Sono passati {ANSWER_DAYS} giorni senza risposta: per questo lavoro serve il sì del cliente, "
                    "la task resta ferma. Va sollecitato il cliente."
                )
                field, key = "atlante_client_late", "late"
            else:
                text = (
                    f"Sono passati {ANSWER_DAYS} giorni senza risposta del cliente: silenzio-assenso da confermare "
                    "(articolo 9.1)."
                )
                field, key = "atlante_silent_consent", "to_confirm"
            _record(issue, _state_name(issue), text)
            _notify(issue, [member], field, _state_name(issue), text)
            done[key] += 1
        elif day >= approval.reminder_on and approval.reminded_at is None:
            approval.reminded_at = timezone.now()
            approval.save(update_fields=["reminded_at", "updated_at"])
            if approval.consent:
                text = (
                    "Giorno del promemoria: va ricordato al cliente. "
                    "Serve il suo sì: senza risposta la task resta ferma."
                )
            else:
                due, after = italian_date(approval.due_on), italian_date(approval.due_on + timedelta(days=1))
                text = (
                    f"Giorno del promemoria: va ricordato al cliente. Se non risponde entro il {due}, dal {after} "
                    "il lavoro si considera approvato (articolo 9.1)."
                )
            _record(issue, _state_name(issue), text)
            _notify(issue, [member], "atlante_client_reminder", _state_name(issue), text)
            done["reminders"] += 1
    return done
