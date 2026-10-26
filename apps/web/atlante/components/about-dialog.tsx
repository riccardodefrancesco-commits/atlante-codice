/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Button } from "@makeplane/propel/components/button";
import { Dialog, DialogContent } from "@makeplane/propel/components/dialog";
import { PlaneLogo } from "@plane/blocks/icons";
import { useTranslation } from "@plane/i18n";
import packageJson from "package.json";
import { ATLANTE_SOURCE_URL } from "@/atlante/hidden-features";
import { atlanteVersionLabel } from "@/atlante/version";

const PLANE_SOURCE_URL = "https://github.com/makeplane/plane";
const LICENSE_URL = "https://www.gnu.org/licenses/agpl-3.0.html";

type Props = { isOpen: boolean; onClose: () => void };

const link = (href: string, label: string) => (
  <a className="text-accent-primary underline" href={href} target="_blank" rel="noopener noreferrer">
    {label}
  </a>
);

/** "About Atlante": what it is, that it is based on Plane, its license and where the source code is. */
export function AtlanteAboutDialog({ isOpen, onClose }: Props) {
  const { t } = useTranslation();
  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="sm">
        <div className="space-y-4 p-5 text-13 text-secondary" data-atlante="about">
          <div className="flex items-center gap-3 text-accent-primary">
            <PlaneLogo className="h-5 w-auto shrink-0" />
            <div>
              <h3 className="text-18 font-semibold text-primary">{t("atlante.about.title")}</h3>
              <p className="text-12 text-tertiary">{t("atlante.about.version", { version: atlanteVersionLabel() })}</p>
              <p className="text-12 text-tertiary">
                {t("atlante.about.plane_version", { version: packageJson.version })}
              </p>
            </div>
          </div>
          <p>{t("atlante.about.what")}</p>
          <p>{t("atlante.about.based_on")}</p>
          <ul className="space-y-1">
            <li>{link(ATLANTE_SOURCE_URL, t("atlante.about.source_atlante"))}</li>
            <li>{link(PLANE_SOURCE_URL, t("atlante.about.source_plane"))}</li>
            <li>{link(LICENSE_URL, t("atlante.about.license"))}</li>
          </ul>
          <p className="text-12 text-tertiary">{t("atlante.about.source_access")}</p>
        </div>
        <div className="flex justify-end border-t-[0.5px] border-subtle px-5 py-3">
          <Button variant="secondary" size="md" stretch="auto" label={t("close")} onClick={onClose} />
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** At the bottom of the side menu, in place of Plane's "Community" badge (which opened the paid plans). */
export function AtlanteAboutButton() {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <AtlanteAboutDialog isOpen={isOpen} onClose={() => setIsOpen(false)} />
      <Button variant="tertiary" size="md" stretch="auto" label="Atlante" onClick={() => setIsOpen(true)} />
    </>
  );
}
