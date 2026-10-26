/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import { runInAction } from "mobx";
import useSWR, { mutate } from "swr";
import { useIssuesStore } from "@/hooks/use-issue-layout-store";
import { StoreContext } from "@/lib/store-context";
import { AtlanteClientService } from "@/atlante/services/client.service";

const clientService = new AtlanteClientService();

export const issueClientKey = (issueId: string) => `ATLANTE_ISSUE_CLIENT_${issueId}`;

/** The list stores that place items in groups (drafts have no groups). */
type TGroupedListStore = {
  groupedIssueIds: unknown;
  addIssueToList: (issueId: string) => void;
  removeIssueFromList: (issueId: string) => void;
};

const isGroupedListStore = (store: unknown): store is TGroupedListStore =>
  !!store &&
  typeof (store as TGroupedListStore).addIssueToList === "function" &&
  typeof (store as TGroupedListStore).removeIssueFromList === "function";

/** Out of the old group, new client, into the new group. Only lists already loaded are touched. */
export const moveIssueToClient = (
  listStore: unknown,
  updateIssue: (issueId: string, data: { atlante_client_id: string | null }) => void,
  issueId: string,
  clientId: string | null
) => {
  const list = isGroupedListStore(listStore) && listStore.groupedIssueIds ? listStore : undefined;
  list?.removeIssueFromList(issueId);
  updateIssue(issueId, { atlante_client_id: clientId });
  list?.addIssueToList(issueId);
};

/** The client of one work item, as the server sees it. */
export const useAtlanteIssueClient = (workspaceSlug: string, projectId: string, issueId: string) =>
  useSWR(workspaceSlug && projectId && issueId ? issueClientKey(issueId) : null, () =>
    clientService.getIssueClient(workspaceSlug, projectId, issueId)
  );

/** Puts the client into the work item in memory and moves it to the right group of the list on
 * screen, the same way Plane moves an item when its state changes. */
export const useAtlanteIssueClientInMemory = () => {
  const context = useContext(StoreContext);
  const { issues: listStore } = useIssuesStore();

  return (issueId: string, clientId: string | null) =>
    runInAction(() => moveIssueToClient(listStore, context?.issue.issues.updateIssue ?? (() => {}), issueId, clientId));
};

/** Changes the client of a work item: the server first (it may refuse), then the screen. */
export const useAtlanteSetIssueClient = () => {
  const context = useContext(StoreContext);
  const putInMemory = useAtlanteIssueClientInMemory();

  return async (workspaceSlug: string, projectId: string, issueId: string, clientId: string | null) => {
    await clientService.setIssueClient(workspaceSlug, projectId, issueId, clientId);
    putInMemory(issueId, clientId);
    await mutate(issueClientKey(issueId));
    // The server wrote a line in the history: show it, as Plane does after its own changes.
    void context?.issue.issueDetail.activity.fetchActivities(workspaceSlug, projectId, issueId);
  };
};
