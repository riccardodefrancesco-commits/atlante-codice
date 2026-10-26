/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { orderBy } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
import { AtlanteClientService } from "@/atlante/services/client.service";
import type { TAtlanteClient, TAtlanteClientFormData } from "@/atlante/types";

export interface IAtlanteClientStore {
  clientMap: Record<string, TAtlanteClient>;
  projectClientMap: Record<string, string>;
  fetchedWorkspaceSlug: string | null;
  activeClients: TAtlanteClient[];
  archivedClients: TAtlanteClient[];
  getClientById: (clientId: string | null | undefined) => TAtlanteClient | undefined;
  getProjectClientId: (projectId: string | null | undefined) => string | undefined;
  getClientProjectIds: (clientId: string) => string[];
  fetchClients: (workspaceSlug: string) => Promise<void>;
  createClient: (workspaceSlug: string, data: Partial<TAtlanteClientFormData>) => Promise<TAtlanteClient>;
  updateClient: (
    workspaceSlug: string,
    clientId: string,
    data: Partial<TAtlanteClientFormData>
  ) => Promise<TAtlanteClient>;
  archiveClient: (workspaceSlug: string, clientId: string) => Promise<void>;
  restoreClient: (workspaceSlug: string, clientId: string) => Promise<void>;
  setProjectClient: (workspaceSlug: string, projectId: string, clientId: string | null) => Promise<void>;
  reset: () => void;
}

const byName = (clients: TAtlanteClient[]) => orderBy(clients, (client) => client.name.toLocaleLowerCase("it"));

/** The clients of the current workspace and the "project -> client" map, kept in memory.
 * Changes show at once and go back as they were if the server refuses them. */
export class AtlanteClientStore implements IAtlanteClientStore {
  clientMap: Record<string, TAtlanteClient> = {};
  projectClientMap: Record<string, string> = {};
  fetchedWorkspaceSlug: string | null = null;
  clientService: AtlanteClientService;

  constructor(clientService: AtlanteClientService = new AtlanteClientService()) {
    makeObservable(this, {
      clientMap: observable,
      projectClientMap: observable,
      fetchedWorkspaceSlug: observable.ref,
      activeClients: computed,
      archivedClients: computed,
      fetchClients: action,
      createClient: action,
      updateClient: action,
      archiveClient: action,
      restoreClient: action,
      setProjectClient: action,
      reset: action,
    });
    this.clientService = clientService;
  }

  /** Clients not archived, by name: the ones offered as choices. */
  get activeClients() {
    return byName(Object.values(this.clientMap).filter((client) => !client.archived_at));
  }

  get archivedClients() {
    return byName(Object.values(this.clientMap).filter((client) => !!client.archived_at));
  }

  getClientById = computedFn((clientId: string | null | undefined) =>
    clientId ? this.clientMap[clientId] : undefined
  );

  getProjectClientId = computedFn((projectId: string | null | undefined) =>
    projectId ? this.projectClientMap[projectId] : undefined
  );

  getClientProjectIds = computedFn((clientId: string) =>
    Object.entries(this.projectClientMap)
      .filter(([, linkedClientId]) => linkedClientId === clientId)
      .map(([projectId]) => projectId)
  );

  fetchClients = async (workspaceSlug: string) => {
    const [clients, links] = await Promise.all([
      this.clientService.getClients(workspaceSlug),
      this.clientService.getProjectClients(workspaceSlug),
    ]);
    runInAction(() => {
      this.clientMap = Object.fromEntries(clients.map((client) => [client.id, client]));
      this.projectClientMap = Object.fromEntries(links.map((link) => [link.project_id, link.client_id]));
      this.fetchedWorkspaceSlug = workspaceSlug;
    });
  };

  createClient = async (workspaceSlug: string, data: Partial<TAtlanteClientFormData>) => {
    const created = await this.clientService.createClient(workspaceSlug, data);
    const client = { project_count: 0, open_issues: 0, overdue_issues: 0, ...created };
    runInAction(() => {
      this.clientMap[client.id] = client;
    });
    return client;
  };

  /** The server answers without the numbers (projects, open items): the ones in memory stay. */
  private keepNumbers(clientId: string, saved: TAtlanteClient) {
    this.clientMap[clientId] = { ...this.clientMap[clientId], ...saved };
  }

  private async changeAndRollBack(
    clientId: string,
    change: Partial<TAtlanteClient>,
    save: () => Promise<TAtlanteClient>
  ) {
    const before = this.clientMap[clientId];
    if (!before) throw new Error("Cliente non trovato.");
    runInAction(() => {
      this.clientMap[clientId] = { ...before, ...change };
    });
    try {
      const saved = await save();
      runInAction(() => this.keepNumbers(clientId, saved));
      return this.clientMap[clientId];
    } catch (error) {
      runInAction(() => {
        this.clientMap[clientId] = before;
      });
      throw error;
    }
  }

  updateClient = async (workspaceSlug: string, clientId: string, data: Partial<TAtlanteClientFormData>) =>
    this.changeAndRollBack(clientId, data, () => this.clientService.updateClient(workspaceSlug, clientId, data));

  archiveClient = async (workspaceSlug: string, clientId: string) => {
    await this.changeAndRollBack(clientId, { archived_at: new Date().toISOString() }, () =>
      this.clientService.archiveClient(workspaceSlug, clientId)
    );
  };

  restoreClient = async (workspaceSlug: string, clientId: string) => {
    await this.changeAndRollBack(clientId, { archived_at: null }, () =>
      this.clientService.restoreClient(workspaceSlug, clientId)
    );
  };

  /** Links a project to a client (or unlinks it with null). Its work items follow the client. */
  setProjectClient = async (workspaceSlug: string, projectId: string, clientId: string | null) => {
    const before = this.projectClientMap[projectId];
    runInAction(() => {
      if (clientId) this.projectClientMap[projectId] = clientId;
      else delete this.projectClientMap[projectId];
    });
    try {
      await this.clientService.setProjectClient(workspaceSlug, projectId, clientId);
    } catch (error) {
      runInAction(() => {
        if (before) this.projectClientMap[projectId] = before;
        else delete this.projectClientMap[projectId];
      });
      throw error;
    }
  };

  reset = () => {
    this.clientMap = {};
    this.projectClientMap = {};
    this.fetchedWorkspaceSlug = null;
  };
}
