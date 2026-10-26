/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { useAtlanteClient } from "@/atlante/hooks/use-atlante-client";
import type { TAtlanteClient } from "@/atlante/types";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  workspaceSlug: string;
  client: TAtlanteClient;
};

/** Archiving asks first: it is not a delete, but the client stops being offered as a choice. */
export function AtlanteClientArchiveDialog(props: Props) {
  const { isOpen, onClose, workspaceSlug, client } = props;
  const { t } = useTranslation();
  const { archiveClient } = useAtlanteClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await archiveClient(workspaceSlug, client.id);
      setToast({ type: "success", title: t("atlante.client.toast.archived"), message: client.name });
      onClose();
    } catch {
      setToast({ type: "error", title: t("atlante.client.toast.error"), message: client.name });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ConfirmDialog
      isOpen={isOpen}
      handleClose={onClose}
      handleSubmit={handleSubmit}
      isSubmitting={isSubmitting}
      variant="warning"
      title={t("atlante.client.archive_confirm.title", { name: client.name })}
      content={t("atlante.client.archive_confirm.description")}
      primaryButtonText={{
        default: t("atlante.client.archive_confirm.confirm"),
        loading: t("atlante.client.archive_confirm.confirming"),
      }}
      secondaryButtonText={t("common.cancel")}
    />
  );
}
