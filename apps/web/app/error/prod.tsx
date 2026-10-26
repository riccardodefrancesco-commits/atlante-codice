/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react"; // ATLANTE
import { useTheme } from "next-themes";
// plane imports
import { Button } from "@makeplane/propel/components/button";
// assets
import maintenanceModeDarkModeImage from "@/app/assets/instance/maintenance-mode-dark.svg?url";
import maintenanceModeLightModeImage from "@/app/assets/instance/maintenance-mode-light.svg?url";
// layouts
import DefaultLayout from "@/layouts/default-layout";
import { ATLANTE_SHOW_PLANE_LINKS } from "@/atlante/hidden-features"; // ATLANTE
import { newErrorCode } from "@/atlante/error-codes"; // ATLANTE
import { sendBrowserError } from "@/atlante/error-report"; // ATLANTE

// ATLANTE: no links to Plane's support, status page and social profile
const linkMap = !ATLANTE_SHOW_PLANE_LINKS
  ? []
  : [
      {
        key: "mail_to",
        label: "Contact Support",
        value: "mailto:support@plane.so",
      },
      {
        key: "status",
        label: "Status Page",
        value: "https://status.plane.so/",
      },
      {
        key: "twitter_handle",
        label: "@planepowers",
        value: "https://x.com/planepowers",
      },
    ];

// Production Error Component
interface ProdErrorComponentProps {
  onGoHome: () => void;
}

export function ProdErrorComponent({ onGoHome }: ProdErrorComponentProps) {
  // hooks
  const { resolvedTheme } = useTheme();

  // ATLANTE: the code of this error, shown here and sent to the log once
  const [code] = useState(newErrorCode);
  useEffect(() => sendBrowserError(code, "pagina rotta"), [code]);
  // derived values
  const maintenanceModeImage = resolvedTheme === "dark" ? maintenanceModeDarkModeImage : maintenanceModeLightModeImage;

  return (
    <DefaultLayout>
      <div className="relative container mx-auto flex h-full w-full max-w-xl flex-col items-center justify-center gap-2 gap-y-6 bg-surface-1 px-6 text-center">
        <div className="relative w-full">
          <img
            src={maintenanceModeImage}
            height="176"
            width="288"
            alt="ProjectSettingImg"
            className="h-full w-full object-fill object-center"
          />
        </div>
        <div className="relative mt-4 flex w-full flex-col gap-4">
          <div className="flex flex-col gap-2.5">
            {/* ATLANTE: in italiano */}
            <h1 className="text-left text-18 font-semibold text-primary">&#x1F6A7; Qualcosa non ha funzionato.</h1>
            <span className="text-left text-14 font-medium text-secondary">
              Ricarica la pagina. Se il problema resta, avvisa chi gestisce Atlante e digli cosa stavi facendo.
            </span>
            <span className="text-left text-14 font-medium text-primary">Codice: {code}</span>
          </div>

          <div className="mt-1 flex items-center justify-start gap-6">
            {linkMap.map((link) => (
              <div key={link.key}>
                <a
                  href={link.value}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-13 text-accent-primary hover:underline"
                >
                  {link.label}
                </a>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-start gap-6">
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              label="Torna alla Home"
              /* ATLANTE: in italiano */ onClick={onGoHome}
            />
          </div>
        </div>
      </div>
    </DefaultLayout>
  );
}
