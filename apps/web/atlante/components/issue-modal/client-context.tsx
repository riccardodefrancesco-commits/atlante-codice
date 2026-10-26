/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext, useContext, useState } from "react";
import { observer } from "mobx-react";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { AtlanteClientBadge } from "@/atlante/components/client-badge";
import { AtlanteClientSelect } from "@/atlante/components/client-select";
import { useAtlanteClient } from "@/atlante/hooks/use-atlante-client";
import { useAtlanteClientPermissions } from "@/atlante/hooks/use-client-permissions";
import { useAtlanteIssueClientInMemory, useAtlanteSetIssueClient } from "@/atlante/hooks/use-issue-client";

type TSaveProps = { issueId: string; projectId: string; workspaceSlug: string; isDraft?: boolean };

type TAtlanteIssueModalClient = {
  /** The client chosen in the window; undefined while nobody touched it. */
  chosen: string | null | undefined;
  setChosen: (clientId: string | null) => void;
  /** Called by Plane's window after it saved the work item. */
  save: (props: TSaveProps) => Promise<void>;
};

/** What to do with the client once Plane saved the work item:
 * - a draft is not a work item yet: nothing;
 * - in a project with a client the server already gives the item that client: only the screen needs it;
 * - otherwise save the chosen client, if somebody chose one. */
export const clientSaveStep = (props: {
  isDraft: boolean;
  chosen: string | null | undefined;
  projectClientId: string | undefined;
}): "nothing" | "screen-only" | "server" => {
  if (props.isDraft) return "nothing";
  if (props.projectClientId) return "screen-only";
  return props.chosen === undefined ? "nothing" : "server";
};

const AtlanteIssueModalClientContext = createContext<TAtlanteIssueModalClient | undefined>(undefined);

/** The client chosen in Plane's "new work item" window, saved right after Plane saves the item. */
export const useAtlanteIssueModalClientState = (): TAtlanteIssueModalClient => {
  const { t } = useTranslation();
  const { getProjectClientId } = useAtlanteClient();
  const setIssueClient = useAtlanteSetIssueClient();
  const putInMemory = useAtlanteIssueClientInMemory();
  const [chosen, setChosen] = useState<string | null | undefined>(undefined);

  const save = async ({ issueId, projectId, workspaceSlug, isDraft }: TSaveProps) => {
    const projectClientId = getProjectClientId(projectId);
    const step = clientSaveStep({ isDraft: !!isDraft, chosen, projectClientId });
    if (step === "nothing") return;
    if (step === "screen-only") {
      putInMemory(issueId, projectClientId ?? null);
      return;
    }
    try {
      await setIssueClient(workspaceSlug, projectId, issueId, chosen ?? null);
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error ?? "";
      setToast({ type: "error", title: t("atlante.client.toast.error"), message });
    }
  };

  return { chosen, setChosen, save };
};

export const AtlanteIssueModalClientProvider = AtlanteIssueModalClientContext.Provider;

type TPillProps = { projectId: string | null; issueId: string | undefined; isDraft: boolean };

/** The client in the window's row of properties: shown when the project has one, chosen otherwise. */
export const AtlanteIssueModalClientPill = observer(function AtlanteIssueModalClientPill(props: TPillProps) {
  const { projectId, issueId, isDraft } = props;
  const context = useContext(AtlanteIssueModalClientContext);
  const { canView } = useAtlanteClientPermissions();
  const { getProjectClientId } = useAtlanteClient();
  const {
    issue: { getIssueById },
  } = useIssueDetail();

  if (!context || !canView || !projectId || isDraft) return null;

  const projectClientId = getProjectClientId(projectId);
  if (projectClientId)
    return (
      <span className="flex h-7 items-center" data-atlante="issue-modal-client">
        <AtlanteClientBadge clientId={projectClientId} variant="name" />
      </span>
    );

  const current =
    context.chosen !== undefined ? context.chosen : issueId ? getIssueById(issueId)?.atlante_client_id : null;
  return (
    <AtlanteClientSelect
      value={current ?? null}
      onChange={(clientId) => context.setChosen(clientId)}
      variant="pill-md"
    />
  );
});
