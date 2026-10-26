/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
import { Button } from "@makeplane/propel/components/button";
import { Dialog, DialogContent } from "@makeplane/propel/components/dialog";
import { Field } from "@makeplane/propel/components/field";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { InputColorPicker } from "@/components/core/theme/input-color-picker";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { useAtlanteClient } from "@/atlante/hooks/use-atlante-client";
import type { TAtlanteClient, TAtlanteClientFormData } from "@/atlante/types";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  workspaceSlug: string;
  /** The client to edit; none to create a new one. */
  client?: TAtlanteClient;
  onCreated?: (client: TAtlanteClient) => void;
};

const EMPTY: TAtlanteClientFormData = {
  name: "",
  code: "",
  color: "#3E63DD",
  internal_contact: null,
  email: "",
  website: "",
  internal_notes: "",
  included_revisions: 2,
};

const fromClient = (client?: TAtlanteClient): TAtlanteClientFormData =>
  client
    ? {
        name: client.name,
        code: client.code,
        color: client.color,
        internal_contact: client.internal_contact,
        email: client.email,
        website: client.website,
        internal_notes: client.internal_notes,
        included_revisions: client.included_revisions,
      }
    : EMPTY;

/** The server answers with a message per field: show them under the fields, the rest in a toast. */
type TServerErrors = Partial<Record<keyof TAtlanteClientFormData | "non_field_errors" | "error", string[] | string>>;

const FIELD_LABEL = "text-13 font-medium text-secondary";

export const AtlanteClientFormModal = observer(function AtlanteClientFormModal(props: Props) {
  const { isOpen, onClose, workspaceSlug, client, onCreated } = props;
  const { t } = useTranslation();
  const { createClient, updateClient } = useAtlanteClient();
  const {
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TAtlanteClientFormData>({ defaultValues: fromClient(client) });

  useEffect(() => {
    if (isOpen) reset(fromClient(client));
  }, [isOpen, client, reset]);

  const onSubmit = async (data: TAtlanteClientFormData) => {
    const payload = { ...data, code: data.code.trim().toUpperCase(), name: data.name.trim() };
    try {
      if (client) {
        await updateClient(workspaceSlug, client.id, payload);
        setToast({ type: "success", title: t("atlante.client.toast.updated"), message: payload.name });
      } else {
        const created = await createClient(workspaceSlug, payload);
        setToast({ type: "success", title: t("atlante.client.toast.created"), message: created.name });
        onCreated?.(created);
      }
      onClose();
    } catch (error) {
      const serverErrors = (error ?? {}) as TServerErrors;
      let shown = false;
      for (const field of Object.keys(EMPTY) as (keyof TAtlanteClientFormData)[]) {
        const message = serverErrors[field];
        if (message) {
          setError(field, { message: Array.isArray(message) ? message[0] : message });
          shown = true;
        }
      }
      if (!shown) {
        const general = serverErrors.non_field_errors ?? serverErrors.error;
        setToast({
          type: "error",
          title: t("atlante.client.toast.error"),
          message: (Array.isArray(general) ? general[0] : general) ?? "",
        });
      }
    }
  };

  return (
    <Dialog
      open={isOpen}
      disablePointerDismissal
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="md">
        <form onSubmit={handleSubmit(onSubmit)} data-atlante="client-form">
          <div className="space-y-4 p-5">
            <h3 className="text-18 font-medium text-secondary">
              {client ? t("atlante.client.form.edit_title") : t("atlante.client.form.create_title")}
            </h3>
            <div className="space-y-1">
              <label className={FIELD_LABEL} htmlFor="atlante-client-name">
                {t("atlante.client.form.name")}
              </label>
              <Controller
                name="name"
                control={control}
                rules={{ validate: (value) => value.trim().length > 0 || t("atlante.client.form.name_required") }}
                render={({ field: { value, onChange } }) => (
                  <Field name="name" invalid={Boolean(errors.name)}>
                    <InputGroup size="lg">
                      <Input
                        id="atlante-client-name"
                        size="lg"
                        name="name"
                        value={value}
                        onChange={onChange}
                        placeholder={t("atlante.client.form.name_placeholder")}
                        maxLength={255}
                      />
                    </InputGroup>
                  </Field>
                )}
              />
              <span className="text-11 text-danger-primary">{errors.name?.message}</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className={FIELD_LABEL} htmlFor="atlante-client-code">
                  {t("atlante.client.form.code")}
                </label>
                <Controller
                  name="code"
                  control={control}
                  rules={{
                    validate: (value) => {
                      const code = value.trim();
                      if (!code) return t("atlante.client.form.code_required");
                      return /^[A-Za-z0-9]{1,12}$/.test(code) || t("atlante.client.form.code_invalid");
                    },
                  }}
                  render={({ field: { value, onChange } }) => (
                    <Field name="code" invalid={Boolean(errors.code)}>
                      <InputGroup size="lg">
                        <Input
                          id="atlante-client-code"
                          size="lg"
                          name="code"
                          value={value}
                          onChange={(event) => onChange(event.target.value.toUpperCase())}
                          placeholder={t("atlante.client.form.code_placeholder")}
                          maxLength={12}
                        />
                      </InputGroup>
                    </Field>
                  )}
                />
                <span className="block text-11 text-tertiary">
                  {errors.code?.message ? (
                    <span className="text-danger-primary">{errors.code.message}</span>
                  ) : (
                    t("atlante.client.form.code_help")
                  )}
                </span>
              </div>
              <div className="space-y-1">
                <span className={FIELD_LABEL}>{t("atlante.client.form.color")}</span>
                <Controller
                  name="color"
                  control={control}
                  rules={{
                    validate: (value) => /^#[0-9A-Fa-f]{6}$/.test(value) || t("atlante.client.form.color_invalid"),
                  }}
                  render={({ field: { value, onChange } }) => (
                    <InputColorPicker
                      name="color"
                      value={value}
                      onChange={(color) => onChange(color.toUpperCase())}
                      hasError={Boolean(errors.color)}
                      placeholder="#3E63DD"
                    />
                  )}
                />
                <span className="text-11 text-danger-primary">{errors.color?.message}</span>
              </div>
            </div>
            <div className="space-y-1">
              <span className={FIELD_LABEL}>{t("atlante.client.form.contact")}</span>
              <Controller
                name="internal_contact"
                control={control}
                render={({ field: { value, onChange } }) => (
                  <MemberSelect
                    value={value}
                    onChange={(id) => onChange(id || null)}
                    variant="select-md"
                    clearable
                    placeholder={t("atlante.client.form.contact_placeholder")}
                  />
                )}
              />
              <span className="text-11 text-danger-primary">{errors.internal_contact?.message}</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {(["email", "website"] as const).map((field) => (
                <div key={field} className="space-y-1">
                  <label className={FIELD_LABEL} htmlFor={`atlante-client-${field}`}>
                    {t(`atlante.client.form.${field}`)}
                  </label>
                  <Controller
                    name={field}
                    control={control}
                    render={({ field: { value, onChange } }) => (
                      <Field name={field} invalid={Boolean(errors[field])}>
                        <InputGroup size="lg">
                          <Input
                            id={`atlante-client-${field}`}
                            size="lg"
                            name={field}
                            type={field === "email" ? "email" : "url"}
                            value={value}
                            onChange={onChange}
                            placeholder={field === "email" ? "info@esempio.it" : "https://"}
                          />
                        </InputGroup>
                      </Field>
                    )}
                  />
                  <span className="text-11 text-danger-primary">{errors[field]?.message}</span>
                </div>
              ))}
            </div>
            <div className="space-y-1">
              <label className={FIELD_LABEL} htmlFor="atlante-client-revisions">
                {t("atlante.client.form.included_revisions")}
              </label>
              <Controller
                name="included_revisions"
                control={control}
                render={({ field: { value, onChange } }) => (
                  <Field name="included_revisions" invalid={Boolean(errors.included_revisions)}>
                    <InputGroup size="lg">
                      <Input
                        id="atlante-client-revisions"
                        size="lg"
                        name="included_revisions"
                        type="number"
                        min={0}
                        max={20}
                        value={value}
                        onChange={(event) => onChange(Number(event.target.value))}
                      />
                    </InputGroup>
                  </Field>
                )}
              />
              <span className="text-11 text-tertiary">{t("atlante.client.form.included_revisions_help")}</span>
              <span className="text-11 text-danger-primary">{errors.included_revisions?.message}</span>
            </div>
            <div className="space-y-1">
              <label className={FIELD_LABEL} htmlFor="atlante-client-notes">
                {t("atlante.client.form.notes")}
              </label>
              <Controller
                name="internal_notes"
                control={control}
                render={({ field: { value, onChange } }) => (
                  <Field name="internal_notes">
                    <TextAreaGroup resize="none">
                      <TextArea
                        id="atlante-client-notes"
                        size="lg"
                        surface="field"
                        autoResize
                        maxRows={8}
                        name="internal_notes"
                        value={value}
                        onChange={onChange}
                      />
                    </TextAreaGroup>
                  </Field>
                )}
              />
              <span className="text-11 text-tertiary">{t("atlante.client.form.notes_help")}</span>
            </div>
          </div>
          <div className="flex items-center justify-end gap-2 border-t-[0.5px] border-subtle px-5 py-4">
            <Button variant="secondary" size="md" stretch="auto" onClick={onClose} label={t("common.cancel")} />
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              type="submit"
              loading={isSubmitting}
              label={
                client
                  ? t(isSubmitting ? "atlante.client.form.saving" : "atlante.client.form.save")
                  : t(isSubmitting ? "atlante.client.form.creating" : "atlante.client.form.create")
              }
            />
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
});
