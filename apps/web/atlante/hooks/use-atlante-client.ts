/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import type { IAtlanteClientStore } from "@/atlante/store/client.store";
import { StoreContext } from "@/lib/store-context";

export const useAtlanteClient = (): IAtlanteClientStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useAtlanteClient must be used within StoreProvider");
  return context.atlanteClient;
};

/** Loads the clients of the current workspace once (SWR shares the request).
 * Used by every component that shows a client, so the data is there on any page. */
export const useAtlanteClientsLoader = () => {
  const { workspaceSlug } = useParams();
  const { fetchClients } = useAtlanteClient();
  const slug = workspaceSlug?.toString();
  // The fetcher returns a value: with no data SWR would ask the server again at every mount
  // (every badge on screen).
  useSWR(slug ? `ATLANTE_CLIENTS_${slug}` : null, slug ? () => fetchClients(slug).then(() => slug) : null, {
    revalidateIfStale: false,
    revalidateOnFocus: false,
  });
};
