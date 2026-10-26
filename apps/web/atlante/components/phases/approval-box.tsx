/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { InfoOutline, TickOutline, WarningCircleOutline, ChatOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { cn, renderFormattedDate } from "@plane/utils";
import { atlantePhasesService, useAtlanteCanSeePhases, useAtlanteRefreshTask } from "@/atlante/hooks/use-phases";
import { approvalKey } from "@/atlante/store/phase-refresh";
import type { TAtlanteApproval } from "@/atlante/types";

type Tone = "info" | "warning" | "success" | "danger";

const TONES: Record<Tone, string> = {
  info: "bg-info-subtle text-info-primary",
  warning: "bg-warning-subtle text-warning-primary",
  success: "bg-success-subtle text-success-primary",
  danger: "bg-danger-subtle text-danger-primary",
};

type TBox = {
  tone: Tone;
  title: string;
  text: string;
  quote?: string;
  badge?: boolean;
  /** What the team can do: send it, record the client's answer, confirm the silent consent. */
  action?: "send" | "answer" | "confirm";
};

/** Which box, with which words (design system, table 15, updated by Rick on 22 October). */
function useBoxContent(approval: TAtlanteApproval): TBox {
  const { t } = useTranslation();
  const date = (value: string | null) => (value ? (renderFormattedDate(value) ?? value) : "");
  const client = approval.client_name ?? t("atlante.approval.the_client");
  const phase = approval.next_state_name ?? approval.approve_to ?? "";
  const lastRound = approval.included > 0 && approval.round >= approval.included;

  if (approval.status === "approvata")
    return {
      tone: "success",
      title: t("atlante.approval.approved_title"),
      text: t("atlante.approval.approved_text", {
        client,
        who: approval.decided_by ?? "",
        date: date(approval.decided_at),
        phase,
      }),
    };
  if (approval.status === "approvata_auto")
    return {
      tone: "success",
      title: t("atlante.approval.silent_done_title"),
      text: t("atlante.approval.silent_done_text", {
        who: approval.decided_by ?? "",
        date: date(approval.decided_at),
        phase,
      }),
    };
  if (approval.status === "modifiche") {
    const next = approval.used + 1;
    const rounds = !approval.counts_round
      ? t("atlante.approval.changes_micro")
      : next <= approval.included
        ? t("atlante.approval.changes_round", { next, included: approval.included })
        : t("atlante.approval.changes_extra", { included: approval.included });
    return {
      tone: "warning",
      title: t("atlante.approval.changes_title"),
      text: t("atlante.approval.changes_text", {
        who: approval.decided_by ?? "",
        date: date(approval.decided_at),
        rounds,
        phase,
      }),
      quote: approval.note,
    };
  }
  if (approval.status === "da_inviare")
    return {
      tone: "info",
      title: t("atlante.approval.ready_title"),
      text: t(approval.consent ? "atlante.approval.ready_text_consent" : "atlante.approval.ready_text", {
        for: approval.client_name ? t("atlante.approval.for_named", { client: approval.client_name }) : "",
      }),
      action: "send",
    };
  if (approval.to_confirm)
    return {
      tone: "warning",
      title: t("atlante.approval.silent_title"),
      text: t("atlante.approval.silent_text", { phase }),
      action: "confirm",
    };
  if (approval.consent)
    return {
      tone: "info",
      title: t("atlante.approval.consent_title"),
      text: approval.late
        ? t("atlante.approval.consent_late")
        : t("atlante.approval.consent_text", { sent: date(approval.sent_on) }),
      badge: true,
      action: "answer",
    };
  if (lastRound)
    return {
      tone: "danger",
      title: t("atlante.approval.rounds_over_title"),
      text: t("atlante.approval.rounds_over_text", {
        with: approval.client_name
          ? t("atlante.approval.with_named", { client: approval.client_name })
          : t("atlante.approval.with_client"),
        included: approval.included,
      }),
      badge: true,
      action: "answer",
    };
  if (approval.reminder_day)
    return {
      tone: "warning",
      title:
        approval.days_left === 1
          ? t("atlante.approval.reminder_title_one")
          : t("atlante.approval.reminder_title", { days: Math.max(approval.days_left ?? 0, 0) }),
      text: t("atlante.approval.reminder_text", {
        reminder: date(approval.reminder_on),
        due: date(approval.due_on),
        after: date(approval.approved_from),
      }),
      badge: true,
      action: "answer",
    };
  return {
    tone: "info",
    title: t("atlante.approval.waiting_title"),
    text: t("atlante.approval.waiting_text", {
      to: approval.client_name
        ? t("atlante.approval.to_named", { client: approval.client_name })
        : t("atlante.approval.to_client"),
      sent: date(approval.sent_on),
      who: approval.sent_by ?? "",
      due: date(approval.due_on),
    }),
    badge: true,
    action: "answer",
  };
}

const ICONS: Record<Tone, typeof InfoOutline> = {
  info: InfoOutline,
  warning: WarningCircleOutline,
  success: TickOutline,
  danger: WarningCircleOutline,
};

type Props = { workspaceSlug: string; projectId: string; issueId: string; disabled: boolean };

/** Under the title of the task, above the description: what the client is doing with the work, and
 * the buttons to record the answer until the portal (assaggio F). */
export const AtlanteApprovalBox = observer(function AtlanteApprovalBox(props: Props) {
  const { workspaceSlug, projectId, issueId } = props;
  const canSee = useAtlanteCanSeePhases(workspaceSlug, projectId);
  const { data, mutate } = useSWR(canSee && issueId ? approvalKey(issueId) : null, () =>
    atlantePhasesService.getApproval(workspaceSlug, projectId, issueId)
  );
  const approval = data?.approval;
  if (!approval || !approval.visible) return null;
  return (
    <ApprovalContent {...props} approval={approval} onAnswered={(next) => void mutate(next, { revalidate: false })} />
  );
});

function ApprovalContent({
  workspaceSlug,
  projectId,
  issueId,
  disabled,
  approval,
  onAnswered,
}: Props & { approval: TAtlanteApproval; onAnswered: (next: { approval: TAtlanteApproval | null }) => void }) {
  const { t } = useTranslation();
  const refreshTask = useAtlanteRefreshTask();
  const content = useBoxContent(approval);
  const [asking, setAsking] = useState(false);
  const [note, setNote] = useState("");
  const [counts, setCounts] = useState(true);
  const [busy, setBusy] = useState(false);
  const Icon = content.tone === "warning" && approval.status === "modifiche" ? ChatOutline : ICONS[content.tone];

  const answer = async (esito: "inviata" | "approvata" | "modifiche" | "silenzio_assenso") => {
    setBusy(true);
    try {
      const next = await atlantePhasesService.answerApproval(workspaceSlug, projectId, issueId, {
        esito,
        nota: note,
        conta: counts,
      });
      onAnswered(next);
      setAsking(false);
      await refreshTask(workspaceSlug, projectId, issueId);
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error ?? "";
      setToast({ type: "error", title: t("atlante.approval.error"), message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={cn("my-3 flex flex-col gap-2.5 rounded-lg border border-subtle px-4 py-3.5", TONES[content.tone])}
      data-atlante="approval-box"
      data-status={approval.status}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Icon width={18} height={18} className="shrink-0" />
          <span className="text-body-sm-medium">{content.title}</span>
        </div>
        {content.badge && (
          <span className="shrink-0 rounded-sm border border-subtle bg-surface-1 px-1.5 py-0.5 text-caption-sm-medium text-secondary">
            {approval.round > approval.included
              ? t("atlante.approval.badge_extra")
              : t("atlante.approval.badge", { round: approval.round, included: approval.included })}
          </span>
        )}
      </div>
      <p className="ml-7 text-body-xs-regular text-secondary">{content.text}</p>
      {content.quote && (
        <div className="ml-7 rounded-sm border-l-2 border-subtle bg-surface-1 px-3 py-2 text-body-xs-regular text-secondary">
          “{content.quote}”
        </div>
      )}
      {content.action && !disabled && !asking && (
        <div className="ml-7 flex flex-wrap items-center justify-between gap-2">
          <span className="text-caption-sm-regular text-tertiary">{t("atlante.approval.hint")}</span>
          <div className="flex gap-2">
            {content.action === "answer" && (
              <Button
                variant="secondary"
                size="md"
                stretch="auto"
                onClick={() => setAsking(true)}
                label={t("atlante.approval.ask_changes")}
              />
            )}
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              loading={busy}
              onClick={() =>
                void answer(
                  content.action === "send"
                    ? "inviata"
                    : content.action === "confirm"
                      ? "silenzio_assenso"
                      : "approvata"
                )
              }
              label={t(
                content.action === "send"
                  ? "atlante.approval.sent"
                  : content.action === "confirm"
                    ? "atlante.approval.confirm"
                    : "atlante.approval.approve"
              )}
            />
          </div>
        </div>
      )}
      {asking && (
        <div className="ml-7 flex flex-col gap-2">
          <label className="flex flex-col gap-1 text-caption-sm-medium text-secondary">
            {t("atlante.approval.note_label")}
            <textarea
              className="min-h-16 rounded-md border border-subtle bg-surface-1 px-2 py-1.5 text-body-xs-regular text-primary outline-none focus:border-accent-strong"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              data-atlante="approval-note"
            />
          </label>
          <label className="flex items-center gap-2 text-body-xs-regular text-secondary">
            <input type="checkbox" checked={counts} onChange={(event) => setCounts(event.target.checked)} />
            {t("atlante.approval.counts")}
          </label>
          <span className="text-caption-sm-regular text-tertiary">{t("atlante.approval.counts_hint")}</span>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              size="md"
              stretch="auto"
              onClick={() => setAsking(false)}
              label={t("atlante.approval.cancel")}
            />
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              loading={busy}
              onClick={() => void answer("modifiche")}
              label={t("atlante.approval.send_changes")}
            />
          </div>
        </div>
      )}
    </div>
  );
}
