/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import { Header } from "@plane/blocks/layout";
import { useTranslation } from "@plane/i18n";
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { AtlanteClientIcon } from "@/atlante/components/client-icon";
import { useAtlanteClient, useAtlanteClientsLoader } from "@/atlante/hooks/use-atlante-client";

export const AtlanteClientDetailHeader = observer(function AtlanteClientDetailHeader() {
  const { workspaceSlug, clientId } = useParams();
  const { t } = useTranslation();
  useAtlanteClientsLoader();
  const { getClientById } = useAtlanteClient();
  const client = getClientById(clientId?.toString());

  return (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink
                href={`/${workspaceSlug?.toString()}/clients/`}
                label={t("atlante.client.plural")}
                icon={<AtlanteClientIcon className="h-4 w-4 text-tertiary" />}
              />
            }
          />
          {client && <Breadcrumbs.Item component={<BreadcrumbLink label={client.name} />} />}
        </Breadcrumbs>
      </Header.LeftItem>
    </Header>
  );
});
