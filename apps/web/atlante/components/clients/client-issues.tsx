/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { Loader } from "@plane/blocks/skeleton";
import { useTranslation } from "@plane/i18n";
import { cn, renderFormattedDate } from "@plane/utils";
import type { TAtlanteClient, TAtlanteClientIssue, TAtlanteStateGroup } from "@/atlante/types";
import { useAtlanteClientIssues } from "./use-client-issues";

type Props = { workspaceSlug: string; client: TAtlanteClient };

const GROUPS: TAtlanteStateGroup[] = ["backlog", "unstarted", "started", "completed", "cancelled"];

/** All the work items of a client, from all its projects, by phase. Each opens Plane's work item page. */
export const AtlanteClientIssues = observer(function AtlanteClientIssues({ workspaceSlug, client }: Props) {
  const { t } = useTranslation();
  const { data, isLoading } = useAtlanteClientIssues(workspaceSlug, client.id);

  if (isLoading)
    return (
      <Loader className="space-y-3 py-4">
        <Loader.Item height="36px" />
        <Loader.Item height="36px" />
        <Loader.Item height="36px" />
      </Loader>
    );

  if (!data || data.results.length === 0)
    return <p className="py-10 text-center text-13 text-tertiary">{t("atlante.client.issues.empty")}</p>;

  const byGroup = new Map<TAtlanteStateGroup, TAtlanteClientIssue[]>();
  for (const issue of data.results) {
    const group = issue.state_group ?? "backlog";
    byGroup.set(group, [...(byGroup.get(group) ?? []), issue]);
  }

  return (
    <div className="space-y-5 py-4" data-atlante="client-issues">
      {data.truncated && (
        <p className="text-12 text-tertiary">
          {t("atlante.client.issues.truncated", { shown: data.results.length, total: data.total })}
        </p>
      )}
      {GROUPS.filter((group) => byGroup.has(group)).map((group) => (
        <section key={group}>
          <h4 className="mb-1 text-13 font-semibold text-secondary">
            {t(`atlante.client.issues.groups.${group}`)}
            <span className="font-normal ml-2 text-tertiary">{data.counts[group]}</span>
          </h4>
          <ul className="divide-y divide-subtle rounded-md border border-subtle">
            {(byGroup.get(group) ?? []).map((issue) => {
              const key = `${issue.project_identifier}-${issue.sequence_id}`;
              return (
                <li key={issue.id}>
                  <Link
                    href={`/${workspaceSlug}/browse/${key}/`}
                    className="flex items-center gap-3 px-4 py-2 text-13 hover:bg-layer-transparent-hover"
                  >
                    <span className="w-20 flex-shrink-0 text-12 text-tertiary">{key}</span>
                    <span className="min-w-0 flex-1 truncate text-primary">{issue.name}</span>
                    <span className="hidden w-40 truncate text-12 text-tertiary md:block">{issue.project_name}</span>
                    <span className="flex w-32 items-center gap-1.5 truncate text-12 text-secondary">
                      <span
                        className="h-2 w-2 flex-shrink-0 rounded-full"
                        style={{ backgroundColor: issue.state_color ?? "#A3A3A3" }}
                      />
                      {issue.state_name}
                    </span>
                    <span
                      className={cn("w-24 flex-shrink-0 text-right text-12", {
                        "font-medium text-danger-primary": issue.overdue,
                        "text-tertiary": !issue.overdue,
                      })}
                    >
                      {issue.target_date ? renderFormattedDate(issue.target_date) : ""}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
});
