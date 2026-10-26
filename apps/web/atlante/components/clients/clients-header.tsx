/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@makeplane/propel/components/button";
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import { Header } from "@plane/blocks/layout";
import { useTranslation } from "@plane/i18n";
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { CountChip } from "@/components/common/count-chip";
import { AtlanteClientIcon } from "@/atlante/components/client-icon";
import { useAtlanteClient } from "@/atlante/hooks/use-atlante-client";
import { useAtlanteClientPermissions } from "@/atlante/hooks/use-client-permissions";
import { AtlanteClientFormModal } from "./client-form-modal";

export const AtlanteClientsHeader = observer(function AtlanteClientsHeader() {
  const { workspaceSlug } = useParams();
  const router = useRouter();
  const { t } = useTranslation();
  const { activeClients } = useAtlanteClient();
  const { canManage } = useAtlanteClientPermissions();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const slug = workspaceSlug?.toString() ?? "";

  return (
    <>
      <AtlanteClientFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        workspaceSlug={slug}
        onCreated={(client) => router.push(`/${slug}/clients/${client.id}`)}
      />
      <Header>
        <Header.LeftItem>
          <div className="flex items-center gap-2.5">
            <Breadcrumbs>
              <Breadcrumbs.Item
                component={
                  <BreadcrumbLink
                    label={t("atlante.client.plural")}
                    icon={<AtlanteClientIcon className="h-4 w-4 text-tertiary" />}
                  />
                }
              />
            </Breadcrumbs>
            {activeClients.length > 0 && <CountChip count={activeClients.length} />}
          </div>
        </Header.LeftItem>
        <Header.RightItem>
          {canManage && (
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              label={t("atlante.client.new")}
              onClick={() => setIsModalOpen(true)}
            />
          )}
        </Header.RightItem>
      </Header>
    </>
  );
});
