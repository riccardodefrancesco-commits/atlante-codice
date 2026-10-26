/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TFilterProperty } from "@plane/types";
import { COLLECTION_OPERATOR, EQUALITY_OPERATOR } from "@plane/types";
import type { IFilterIconConfig, TCreateFilterConfig, TCreateFilterConfigParams } from "@plane/utils";
import { createFilterConfig, createOperatorConfigEntry, getMultiSelectConfig } from "@plane/utils";
import type { TAtlanteClient } from "@/atlante/types";

export type TCreateClientFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<TAtlanteClient> & {
    clients: TAtlanteClient[];
  };

const getClientMultiSelectConfig = (params: TCreateClientFilterParams) =>
  getMultiSelectConfig<TAtlanteClient, string, TAtlanteClient>(
    {
      items: params.clients,
      getId: (client) => client.id,
      getLabel: (client) => client.name,
      getValue: (client) => client.id,
      getIconData: (client) => client,
    },
    {
      singleValueOperator: EQUALITY_OPERATOR.EXACT,
      ...params,
    },
    {
      ...params,
    }
  );

/** "Client" in the rich filter builder: the server filters on the effective client. */
export const getAtlanteClientFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateClientFilterParams> =>
  (params: TCreateClientFilterParams) =>
    createFilterConfig<P>({
      id: key,
      label: "Cliente",
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getClientMultiSelectConfig(updatedParams)
        ),
      ]),
    });
