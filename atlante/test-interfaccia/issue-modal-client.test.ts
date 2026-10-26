/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

vi.mock("mobx-react", () => ({ observer: (component) => component }));
vi.mock("@plane/blocks/toast", () => ({ setToast: () => {} }));
vi.mock("@plane/i18n", () => ({ useTranslation: () => ({ t: (key) => key }) }));
vi.mock("@/hooks/store/use-issue-detail", () => ({ useIssueDetail: () => ({}) }));
vi.mock("@/atlante/components/client-badge", () => ({ AtlanteClientBadge: () => null }));
vi.mock("@/atlante/components/client-select", () => ({ AtlanteClientSelect: () => null }));
vi.mock("@/atlante/hooks/use-atlante-client", () => ({ useAtlanteClient: () => ({}) }));
vi.mock("@/atlante/hooks/use-client-permissions", () => ({ useAtlanteClientPermissions: () => ({}) }));
vi.mock("@/atlante/hooks/use-issue-client", () => ({
  useAtlanteIssueClientInMemory: () => () => {},
  useAtlanteSetIssueClient: () => async () => {},
}));

import { clientSaveStep } from "@/atlante/components/issue-modal/client-context";

describe("saving the client chosen in the new work item window", () => {
  it("does nothing for drafts", () => {
    expect(clientSaveStep({ isDraft: true, chosen: "alfa", projectClientId: undefined })).toBe("nothing");
  });

  it("in a project with a client, only shows it: the server already gives it to the item", () => {
    expect(clientSaveStep({ isDraft: false, chosen: "beta", projectClientId: "alfa" })).toBe("screen-only");
    expect(clientSaveStep({ isDraft: false, chosen: undefined, projectClientId: "alfa" })).toBe("screen-only");
  });

  it("in a project without client, saves the choice, also 'no client', and nothing if untouched", () => {
    expect(clientSaveStep({ isDraft: false, chosen: "beta", projectClientId: undefined })).toBe("server");
    expect(clientSaveStep({ isDraft: false, chosen: null, projectClientId: undefined })).toBe("server");
    expect(clientSaveStep({ isDraft: false, chosen: undefined, projectClientId: undefined })).toBe("nothing");
  });
});
