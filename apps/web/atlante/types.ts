/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TAtlanteClient = {
  id: string;
  name: string;
  code: string;
  color: string;
  internal_contact: string | null;
  email: string;
  website: string;
  internal_notes: string;
  /** Revision rounds included in the contract: the others are paid. */
  included_revisions: number;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  project_count?: number;
  open_issues?: number;
  overdue_issues?: number;
};

/** What the client window sends: the fields a person can change. */
export type TAtlanteClientFormData = Pick<
  TAtlanteClient,
  "name" | "code" | "color" | "internal_contact" | "email" | "website" | "internal_notes" | "included_revisions"
>;

export type TAtlanteProjectClient = {
  project_id: string;
  client_id: string;
};

/** A project of a client, with its progress. */
export type TAtlanteClientProject = {
  id: string;
  name: string;
  identifier: string;
  archived_at: string | null;
  total_issues: number;
  completed_issues: number;
  open_issues: number;
  overdue_issues: number;
};

export type TAtlanteStateGroup = "backlog" | "unstarted" | "started" | "completed" | "cancelled";

/** A work item of a client, as the client card shows it. */
export type TAtlanteClientIssue = {
  id: string;
  name: string;
  sequence_id: number;
  project_id: string;
  project_identifier: string;
  project_name: string;
  state_name: string | null;
  state_group: TAtlanteStateGroup | null;
  state_color: string | null;
  priority: string;
  target_date: string | null;
  overdue: boolean;
  assignee_ids: string[];
};

export type TAtlanteClientIssues = {
  total: number;
  overdue: number;
  truncated: boolean;
  counts: Record<TAtlanteStateGroup, number>;
  results: TAtlanteClientIssue[];
};

/** The client of a work item: its own, or its project's ("project"); editable only in projects without a client. */
export type TAtlanteIssueClient = {
  issue_id: string;
  client_id: string | null;
  source: "issue" | "project" | null;
  editable: boolean;
};

/** A phase of the project's template, linked to one of its states (assaggio B). */
export type TAtlantePhaseRule = {
  state_id: string;
  phase: string;
  phase_name: string;
  executor: string | null;
  executor_name: string;
  deadline: string;
};

/** Template, roles and phase rules of a project. */
export type TAtlanteProjectTemplate = {
  project_id: string;
  template: string | null;
  templates: { key: string; name: string }[];
  /** Phases added to the template after it was applied: applying it again adds them. */
  missing_phases: string[];
  roles: { key: string; name: string; member_ids: string[] }[];
  phases: TAtlantePhaseRule[];
};

/** The choices made on one task: responsible person, roles, dates, and its current phase. */
export type TAtlanteTaskChoices = {
  issue_id: string;
  template: string | null;
  responsabile: { member_id: string | null; source: "task" | "project" | null };
  roles: { key: string; name: string; member_ids: string[]; project_member_ids: string[] }[];
  dates: { key: string; name: string; day: string | null }[];
  /** In a phase that gives the work, without executor (design system, table 14). */
  to_assign: boolean;
  /** The kind of work (video, copertina, post...), and the ones to choose from. */
  work_type: string | null;
  work_types: { key: string; name: string }[];
  phase: {
    key: string;
    name: string;
    executor_name: string;
    deadline: string;
    entered_at: string | null;
    rule: string;
  } | null;
};

/** null goes back to the project's choice, or removes the date. */
export type TAtlanteTaskChoicesUpdate = Record<string, string | string[] | null>;

/** A task in the Home lists "Da assegnare" and "Senza responsabile". */
export type TAtlanteHomeTask = {
  id: string;
  name: string;
  sequence_id: number;
  project_id: string;
  project_identifier: string;
  state_name: string | null;
  state_color: string | null;
  target_date: string | null;
};

export type TAtlanteHomeTasks = {
  to_assign: TAtlanteHomeTask[];
  approvals: TAtlanteHomeApproval[];
  /** Only for workspace admins, otherwise null. */
  without_responsible: TAtlanteHomeTask[] | null;
};

/** The client's approval of a task (assaggio F; design system, table 15). */
export type TAtlanteApproval = {
  /** Until the portal: "da_inviare" until the team presses "Inviato al cliente". */
  status: "da_inviare" | "attesa" | "approvata" | "approvata_auto" | "modifiche";
  consent: boolean;
  phase_name: string;
  sent_on: string | null;
  sent_by: string | null;
  reminder_on: string | null;
  /** The client's last day, included (the day of sending does not count). */
  due_on: string | null;
  days_left: number | null;
  reminder_day: boolean;
  /** From the sixteenth day: the silent consent, to be confirmed by a person. */
  to_confirm: boolean;
  late: boolean;
  approved_from: string | null;
  approve_to: string | null;
  round: number;
  included: number;
  used: number;
  counts_round: boolean;
  note: string;
  decided_at: string | null;
  decided_by: string | null;
  next_state_name: string | null;
  client_name: string | null;
  visible: boolean;
};

/** A client's approval waiting, in the Home of the responsible person. */
export type TAtlanteHomeApproval = TAtlanteHomeTask & {
  ready: boolean;
  days_left: number | null;
  reminder_day: boolean;
  to_confirm: boolean;
  consent: boolean;
  client_code: string | null;
  client_color: string | null;
};
