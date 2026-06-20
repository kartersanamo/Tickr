"use client";

import { useCallback, useEffect, useState } from "react";
import { tickrFetchClient } from "@/lib/api-client";

type ConfigField = {
  key: string;
  path: string;
  label: string;
  description: string;
  fieldType: string;
  required: boolean;
  category: string;
};

type DiscordMeta = {
  roles: { id: string; name: string }[];
  textChannels: { id: string; name: string }[];
  categories: { id: string; name: string }[];
  voiceChannels: { id: string; name: string }[];
};

type Props = {
  guildId: string;
  categories: Record<string, string>;
  fields: ConfigField[];
  initialValues: Record<string, unknown>;
  missingRequired: string[];
};

export function ConfigEditor({
  guildId,
  categories,
  fields,
  initialValues,
  missingRequired,
}: Props) {
  const [activeCategory, setActiveCategory] = useState(Object.keys(categories)[0] || "core");
  const [values, setValues] = useState<Record<string, unknown>>(initialValues);
  const [meta, setMeta] = useState<DiscordMeta | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    tickrFetchClient(`/guilds/${guildId}/discord/meta`)
      .then(setMeta)
      .catch(() => setMeta(null));
  }, [guildId]);

  const categoryFields = fields.filter((f) => f.category === activeCategory);

  const saveField = useCallback(
    async (key: string, value: unknown) => {
      setSaving(true);
      setError("");
      setMessage("");
      try {
        await tickrFetchClient(`/guilds/${guildId}/config`, {
          method: "PATCH",
          body: JSON.stringify({ updates: { [key]: value } }),
        });
        setValues((prev) => ({ ...prev, [key]: value }));
        setMessage(`Saved ${key}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Save failed");
      } finally {
        setSaving(false);
      }
    },
    [guildId],
  );

  function renderField(field: ConfigField) {
    const value = values[field.key];
    const common = (
      <p className="mb-3 text-sm text-[var(--text-muted)]">{field.description}</p>
    );

    if (field.fieldType === "toggle") {
      return (
        <div key={field.key} className="glass-card mb-4 p-5">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-semibold">
              {field.label}
              {field.required && <span className="text-[var(--accent)]"> *</span>}
            </h3>
            <button
              type="button"
              className="btn-primary text-sm"
              disabled={saving}
              onClick={() => saveField(field.key, !value)}
            >
              {value ? "Disable" : "Enable"}
            </button>
          </div>
          {common}
        </div>
      );
    }

    if (field.fieldType === "role") {
      return (
        <div key={field.key} className="glass-card mb-4 p-5">
          <h3 className="mb-1 font-semibold">
            {field.label}
            {field.required && <span className="text-[var(--accent)]"> *</span>}
          </h3>
          {common}
          <select
            className="select-field"
            value={String(value || "")}
            onChange={(e) => saveField(field.key, e.target.value ? e.target.value : null)}
          >
            <option value="">Not set</option>
            {meta?.roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
      );
    }

    if (field.fieldType === "role_list" || field.fieldType === "category_list") {
      const selected = Array.isArray(value) ? (value as string[]) : [];
      const options =
        field.fieldType === "role_list" ? meta?.roles || [] : meta?.categories || [];
      return (
        <div key={field.key} className="glass-card mb-4 p-5">
          <h3 className="mb-1 font-semibold">{field.label}</h3>
          {common}
          <select
            multiple
            className="select-field min-h-[120px]"
            value={selected.map(String)}
            onChange={(e) => {
              const next = Array.from(e.target.selectedOptions).map((o) => o.value);
              saveField(field.key, next);
            }}
          >
            {options.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs text-[var(--text-muted)]">Hold Ctrl/Cmd to select multiple.</p>
        </div>
      );
    }

    if (["channel_text", "channel_category", "channel_voice"].includes(field.fieldType)) {
      const options =
        field.fieldType === "channel_voice"
          ? meta?.voiceChannels || []
          : field.fieldType === "channel_category"
            ? meta?.categories || []
            : meta?.textChannels || [];
      return (
        <div key={field.key} className="glass-card mb-4 p-5">
          <h3 className="mb-1 font-semibold">
            {field.label}
            {field.required && <span className="text-[var(--accent)]"> *</span>}
          </h3>
          {common}
          <select
            className="select-field"
            value={String(value || "")}
            onChange={(e) => saveField(field.key, e.target.value ? e.target.value : null)}
          >
            <option value="">Not set</option>
            {options.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      );
    }

    if (field.fieldType === "json") {
      return (
        <div key={field.key} className="glass-card mb-4 p-5">
          <h3 className="mb-1 font-semibold">{field.label}</h3>
          {common}
          <textarea
            className="input-field min-h-[120px] font-mono text-sm"
            defaultValue={JSON.stringify(value ?? {}, null, 2)}
            onBlur={(e) => {
              try {
                saveField(field.key, JSON.parse(e.target.value || "{}"));
              } catch {
                setError("Invalid JSON");
              }
            }}
          />
        </div>
      );
    }

    if (field.fieldType === "dashboard_secret") {
      return (
        <div key={field.key} className="glass-card mb-4 p-5">
          <h3 className="mb-1 font-semibold">{field.label}</h3>
          {common}
          <input
            type="password"
            className="input-field"
            placeholder={value === "********" ? "Leave blank to keep current" : "Enter secret"}
            onBlur={(e) => {
              if (e.target.value) saveField(field.key, e.target.value);
            }}
          />
        </div>
      );
    }

    return (
      <div key={field.key} className="glass-card mb-4 p-5">
        <h3 className="mb-1 font-semibold">
          {field.label}
          {field.required && <span className="text-[var(--accent)]"> *</span>}
        </h3>
        {common}
        <input
          className="input-field"
          defaultValue={String(value ?? "")}
          onBlur={(e) => saveField(field.key, e.target.value || null)}
        />
      </div>
    );
  }

  return (
    <div>
      {missingRequired.length > 0 && (
        <div className="mb-6 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-amber-100">
          Missing required: {missingRequired.join(", ")}
        </div>
      )}
      {message && <div className="mb-4 text-sm text-green-300">{message}</div>}
      {error && <div className="mb-4 text-sm text-red-300">{error}</div>}
      <div className="mb-6 flex flex-wrap gap-2">
        {Object.entries(categories).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`rounded-lg px-4 py-2 text-sm ${
              activeCategory === key
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
            }`}
            onClick={() => setActiveCategory(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {categoryFields.map(renderField)}
    </div>
  );
}
