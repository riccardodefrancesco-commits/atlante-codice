/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Select } from "@plane/blocks/select";
import type { SelectVariant } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import { useAtlanteClient, useAtlanteClientsLoader } from "@/atlante/hooks/use-atlante-client";

type TClientOption = { id: string; name: string; code: string; color: string | null };

type Props = {
  value: string | null | undefined;
  onChange: (clientId: string | null) => void;
  variant: SelectVariant;
  disabled?: boolean;
  className?: string;
  tabIndex?: number;
};

const NONE = "";

const dot = (color: string | null) => (
  <span
    className="h-2 w-2 flex-shrink-0 rounded-full border-[0.5px] border-strong"
    style={{ backgroundColor: color ?? "transparent" }}
  />
);

/** Choose the client of a work item: the active clients, by name, plus "No client". */
export const AtlanteClientSelect = observer(function AtlanteClientSelect(props: Props) {
  const { value, onChange, variant, disabled = false, className, tabIndex } = props;
  const { t } = useTranslation();
  useAtlanteClientsLoader();
  const { activeClients, getClientById } = useAtlanteClient();

  const none: TClientOption = { id: NONE, name: t("atlante.client.none"), code: "", color: null };
  const options: TClientOption[] = activeClients.map(({ id, name, code, color }) => ({ id, name, code, color }));
  const current = value ? getClientById(value) : undefined;
  const selected: TClientOption | null = current
    ? { id: current.id, name: current.name, code: current.code, color: current.color }
    : null;

  return (
    <Select<TClientOption>
      getValues={() => options}
      headerItems={[none]}
      value={selected}
      onChange={(id) => onChange(id ? id : null)}
      disabled={disabled}
      placeholder={t("atlante.client.select")}
      searchPlaceholder={t("atlante.client.search")}
      getOptionValue={(option) => option.id}
      getOptionLabel={(option) => option.name}
      getOptionSearchText={(option) => `${option.name} ${option.code}`}
      getOptionIcon={(option) => dot(option.color)}
    >
      <Select.Trigger<TClientOption>
        disabled={disabled}
        variant={variant}
        tabIndex={tabIndex}
        className={className}
        data-testid="atlante-client-select"
        prependIcon={(clients) => dot(clients[0]?.color ?? null)}
        label={(clients) => clients[0]?.name ?? t("atlante.client.select")}
      >
        {(clients) => (
          <span className="min-w-0 grow truncate text-left">{clients[0]?.name ?? t("atlante.client.select")}</span>
        )}
      </Select.Trigger>
    </Select>
  );
});
