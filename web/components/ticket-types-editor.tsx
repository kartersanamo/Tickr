"use client";

import { useCallback, useEffect, useState } from "react";
import { tickrFetchClient } from "@/lib/api-client";
import { isValidTicketEmoji, TICKET_EMOJI_ERROR } from "@/lib/ticket-emoji";

type Question = { Label: string; Placeholder: string; Length: string };

type TicketType = {
  Status: string;
  Emoji: string;
  Description: string;
  Category: number | null;
  PrivateMode: string | null;
  Message: string;
  Questions: Question[];
};

type Props = { guildId: string };

function typePath(guildId: string, category: string, typeName: string, suffix = "") {
  const base = `/guilds/${guildId}/ticket-types/categories/${encodeURIComponent(category)}/types/${encodeURIComponent(typeName)}`;
  return suffix ? `${base}${suffix}` : base;
}

export function TicketTypesEditor({ guildId }: Props) {
  const [data, setData] = useState<Record<string, unknown>>({});
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("");
  const [newCategory, setNewCategory] = useState("");
  const [newType, setNewType] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [newQuestion, setNewQuestion] = useState({ label: "", placeholder: "", length: "Long" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await tickrFetchClient(`/guilds/${guildId}/ticket-types`);
      setData(resp.data || {});
      const cats: string[] = resp.categories || [];
      setCategories(cats);
      setSelectedCategory((prev) => (prev && cats.includes(prev) ? prev : cats[0] || ""));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 4000);
    return () => clearTimeout(timer);
  }, [message]);

  const typesInCategory =
    selectedCategory && data[selectedCategory] && typeof data[selectedCategory] === "object"
      ? Object.keys(data[selectedCategory] as Record<string, TicketType>)
      : [];

  const currentType =
    selectedCategory && selectedType
      ? ((data[selectedCategory] as Record<string, TicketType>)?.[selectedType] ?? null)
      : null;

  async function addCategory() {
    if (!newCategory.trim()) return;
    await tickrFetchClient(`/guilds/${guildId}/ticket-types/categories`, {
      method: "POST",
      body: JSON.stringify({ name: newCategory.trim() }),
    });
    setNewCategory("");
    setMessage("Category added.");
    await load();
  }

  async function addType() {
    if (!selectedCategory || !newType.trim()) return;
    await tickrFetchClient(
      `/guilds/${guildId}/ticket-types/categories/${encodeURIComponent(selectedCategory)}/types`,
      { method: "POST", body: JSON.stringify({ name: newType.trim() }) },
    );
    setNewType("");
    setMessage("Ticket type added.");
    await load();
  }

  async function updateTypeField(field: string, value: unknown) {
    if (!selectedCategory || !selectedType || !currentType) return;
    const { Emoji: _emoji, ...rest } = currentType;
    const updated = { ...rest, [field]: value };
    await tickrFetchClient(typePath(guildId, selectedCategory, selectedType), {
      method: "PUT",
      body: JSON.stringify({ data: updated }),
    });
    setMessage("Saved.");
    await load();
  }

  async function updateEmoji(typeName: string, emoji: string) {
    if (!selectedCategory) return;
    if (!isValidTicketEmoji(emoji)) {
      setError(TICKET_EMOJI_ERROR);
      throw new Error(TICKET_EMOJI_ERROR);
    }
    await tickrFetchClient(typePath(guildId, selectedCategory, typeName, "/emoji"), {
      method: "PATCH",
      body: JSON.stringify({ emoji }),
    });
    setError("");
    setMessage("Emoji saved.");
    await load();
  }

  async function addQuestion() {
    if (!selectedCategory || !selectedType || !newQuestion.label.trim()) return;
    await tickrFetchClient(typePath(guildId, selectedCategory, selectedType, "/questions"), {
      method: "POST",
      body: JSON.stringify({
        label: newQuestion.label.trim(),
        placeholder: newQuestion.placeholder.trim(),
        length: newQuestion.length,
      }),
    });
    setNewQuestion({ label: "", placeholder: "", length: "Long" });
    setMessage("Question added.");
    await load();
  }

  async function updateQuestion(originalLabel: string, patch: Partial<Question> & { newLabel?: string }) {
    if (!selectedCategory || !selectedType) return;
    await tickrFetchClient(
      typePath(guildId, selectedCategory, selectedType, `/questions/${encodeURIComponent(originalLabel)}`),
      {
        method: "PATCH",
        body: JSON.stringify({
          label: patch.Label,
          newLabel: patch.newLabel,
          placeholder: patch.Placeholder,
          length: patch.Length,
        }),
      },
    );
    setMessage("Question saved.");
    await load();
  }

  async function deleteQuestion(label: string) {
    if (!selectedCategory || !selectedType) return;
    if (!window.confirm(`Delete question "${label}"?`)) return;
    await tickrFetchClient(
      typePath(guildId, selectedCategory, selectedType, `/questions/${encodeURIComponent(label)}`),
      { method: "DELETE" },
    );
    setMessage("Question deleted.");
    await load();
  }

  async function deleteType() {
    if (!selectedCategory || !selectedType) return;
    if (
      !window.confirm(
        `Delete ticket type "${selectedType}" from "${selectedCategory}"? This cannot be undone.`,
      )
    ) {
      return;
    }
    await tickrFetchClient(typePath(guildId, selectedCategory, selectedType), {
      method: "DELETE",
    });
    setSelectedType("");
    setMessage("Ticket type deleted.");
    await load();
  }

  async function toggleGlobal() {
    const status = data.TOGGLE_STATUS === "Disabled" ? "Enabled" : "Disabled";
    await tickrFetchClient(`/guilds/${guildId}/ticket-types/toggle-global`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    setMessage(`Tickets ${status.toLowerCase()} globally.`);
    await load();
  }

  if (loading) return <p className="text-[var(--text-muted)]">Loading ticket types...</p>;

  return (
    <div className="space-y-6">
      {error && <div className="text-red-300">{error}</div>}
      {message && <div className="text-green-300">{message}</div>}

      <div className="glass-card flex flex-wrap items-center justify-between gap-4 p-4">
        <div>
          <p className="text-sm text-[var(--text-muted)]">Global toggle</p>
          <p className="font-semibold">{String(data.TOGGLE_STATUS || "Enabled")}</p>
        </div>
        <button type="button" className="btn-primary" onClick={toggleGlobal}>
          Toggle all tickets
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="glass-card p-4">
          <h3 className="mb-3 font-semibold">Panel categories</h3>
          <ul className="space-y-2">
            {categories.map((cat) => (
              <li key={cat}>
                <button
                  type="button"
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm ${
                    selectedCategory === cat ? "bg-[var(--accent)]" : "hover:bg-[var(--bg-tertiary)]"
                  }`}
                  onClick={() => {
                    setSelectedCategory(cat);
                    setSelectedType("");
                  }}
                >
                  {cat}
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex gap-2">
            <input
              className="input-field"
              placeholder="New category"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
            />
            <button type="button" className="btn-secondary" onClick={addCategory}>
              Add
            </button>
          </div>
        </div>

        <div className="glass-card p-4">
          <h3 className="mb-3 font-semibold">Ticket types</h3>
          <ul className="space-y-2">
            {typesInCategory.map((t) => {
              const info = (data[selectedCategory] as Record<string, TicketType>)?.[t];
              return (
                <li key={t}>
                  <button
                    type="button"
                    className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${
                      selectedType === t ? "bg-[var(--accent)]" : "hover:bg-[var(--bg-tertiary)]"
                    }`}
                    onClick={() => setSelectedType(t)}
                  >
                    <span className="text-lg leading-none">{info?.Emoji || "🎫"}</span>
                    <span>{t}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          {selectedCategory && (
            <div className="mt-4 flex gap-2">
              <input
                className="input-field"
                placeholder="New type"
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
              />
              <button type="button" className="btn-secondary" onClick={addType}>
                Add
              </button>
            </div>
          )}
        </div>

        <div className="glass-card p-4">
          <h3 className="mb-3 font-semibold">Type details</h3>
          {!currentType ? (
            <p className="text-sm text-[var(--text-muted)]">Select a ticket type.</p>
          ) : (
            <div className="space-y-3">
              <label className="block text-sm">
                Description
                <input
                  className="input-field mt-1"
                  defaultValue={currentType.Description}
                  key={`desc-${selectedType}`}
                  onBlur={(e) => {
                    if (e.target.value !== currentType.Description) {
                      void updateTypeField("Description", e.target.value);
                    }
                  }}
                />
              </label>
              <label className="block text-sm">
                Status
                <select
                  className="select-field mt-1"
                  value={currentType.Status}
                  onChange={(e) => void updateTypeField("Status", e.target.value)}
                >
                  <option value="Enabled">Enabled</option>
                  <option value="Disabled">Disabled</option>
                </select>
              </label>
              <label className="block text-sm">
                Opening message
                <textarea
                  className="input-field mt-1 min-h-[80px]"
                  defaultValue={currentType.Message}
                  key={`msg-${selectedType}`}
                  onBlur={(e) => {
                    if (e.target.value !== currentType.Message) {
                      void updateTypeField("Message", e.target.value);
                    }
                  }}
                />
              </label>
              <button
                type="button"
                className="btn-secondary text-sm text-red-300"
                onClick={() => void deleteType()}
              >
                Delete ticket type
              </button>
            </div>
          )}
        </div>
      </div>

      {selectedCategory && typesInCategory.length > 0 && (
        <div className="glass-card p-5">
          <h3 className="mb-1 font-semibold">Emojis</h3>
          <p className="mb-4 text-sm text-[var(--text-muted)]">
            Change panel emojis here. Other ticket settings are edited in Type details and Questions.
          </p>
          <div className="space-y-3">
            {typesInCategory.map((typeName) => {
              const info = (data[selectedCategory] as Record<string, TicketType>)?.[typeName];
              return (
                <EmojiRow
                  key={typeName}
                  typeName={typeName}
                  emoji={info?.Emoji || "🎫"}
                  onSave={(emoji) => updateEmoji(typeName, emoji)}
                />
              );
            })}
          </div>
        </div>
      )}

      {selectedCategory && selectedType && currentType && (
        <div className="glass-card p-5">
          <h3 className="mb-1 font-semibold">Questions</h3>
          <p className="mb-4 text-sm text-[var(--text-muted)]">
            Up to 5 questions per type (Discord modal limit). Labels max 45 characters.
          </p>

          <div className="space-y-4">
            {currentType.Questions?.map((q) => (
              <QuestionEditor
                key={q.Label}
                question={q}
                onSave={(patch) => updateQuestion(q.Label, patch)}
                onDelete={() => deleteQuestion(q.Label)}
              />
            ))}
          </div>

          {(currentType.Questions?.length ?? 0) < 5 && (
            <div className="mt-6 rounded-lg border border-[var(--border)] p-4">
              <p className="mb-3 text-sm font-medium">Add question</p>
              <div className="grid gap-3 md:grid-cols-3">
                <input
                  className="input-field"
                  placeholder="Label"
                  maxLength={45}
                  value={newQuestion.label}
                  onChange={(e) => setNewQuestion((s) => ({ ...s, label: e.target.value }))}
                />
                <input
                  className="input-field"
                  placeholder="Placeholder (optional)"
                  maxLength={100}
                  value={newQuestion.placeholder}
                  onChange={(e) => setNewQuestion((s) => ({ ...s, placeholder: e.target.value }))}
                />
                <select
                  className="select-field"
                  value={newQuestion.length}
                  onChange={(e) => setNewQuestion((s) => ({ ...s, length: e.target.value }))}
                >
                  <option value="Long">Long answer</option>
                  <option value="Short">Short answer</option>
                </select>
              </div>
              <button type="button" className="btn-primary mt-3" onClick={() => void addQuestion()}>
                Add question
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmojiRow({
  typeName,
  emoji,
  onSave,
}: {
  typeName: string;
  emoji: string;
  onSave: (emoji: string) => Promise<void>;
}) {
  const [value, setValue] = useState(emoji);
  const [fieldError, setFieldError] = useState("");

  useEffect(() => {
    setValue(emoji);
    setFieldError("");
  }, [emoji]);

  return (
    <div className="rounded-lg bg-[var(--bg-tertiary)] px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="min-w-[8rem] font-medium">{typeName}</span>
        <input
          className="input-field max-w-[8rem] text-center text-xl"
          value={value}
          maxLength={32}
          onChange={(e) => {
            setValue(e.target.value);
            setFieldError("");
          }}
          onBlur={() => {
            const trimmed = value.trim();
            if (!trimmed || trimmed === emoji) {
              setValue(emoji);
              return;
            }
            if (!isValidTicketEmoji(trimmed)) {
              setFieldError(TICKET_EMOJI_ERROR);
              setValue(emoji);
              return;
            }
            void onSave(trimmed).catch(() => setValue(emoji));
          }}
          aria-label={`Emoji for ${typeName}`}
          aria-invalid={Boolean(fieldError)}
        />
        <span className="text-2xl leading-none">{isValidTicketEmoji(value) ? value : emoji}</span>
      </div>
      {fieldError && <p className="mt-2 text-sm text-red-300">{fieldError}</p>}
    </div>
  );
}

function QuestionEditor({
  question,
  onSave,
  onDelete,
}: {
  question: Question;
  onSave: (patch: Partial<Question> & { newLabel?: string }) => Promise<void>;
  onDelete: () => void;
}) {
  const [label, setLabel] = useState(question.Label);
  const [placeholder, setPlaceholder] = useState(question.Placeholder);
  const [length, setLength] = useState(question.Length);

  useEffect(() => {
    setLabel(question.Label);
    setPlaceholder(question.Placeholder);
    setLength(question.Length);
  }, [question]);

  function saveIfChanged() {
    const patch: Partial<Question> & { newLabel?: string } = {};
    if (label.trim() !== question.Label) {
      patch.newLabel = label.trim();
    }
    if (placeholder !== question.Placeholder) {
      patch.Placeholder = placeholder;
    }
    if (length !== question.Length) {
      patch.Length = length;
    }
    if (Object.keys(patch).length > 0) {
      void onSave(patch);
    }
  }

  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <div className="grid gap-3 md:grid-cols-3">
        <label className="block text-sm">
          Label
          <input
            className="input-field mt-1"
            maxLength={45}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={saveIfChanged}
          />
        </label>
        <label className="block text-sm">
          Placeholder
          <input
            className="input-field mt-1"
            maxLength={100}
            value={placeholder}
            onChange={(e) => setPlaceholder(e.target.value)}
            onBlur={saveIfChanged}
          />
        </label>
        <label className="block text-sm">
          Length
          <select
            className="select-field mt-1"
            value={length}
            onChange={(e) => {
              setLength(e.target.value);
              void onSave({ Length: e.target.value });
            }}
          >
            <option value="Long">Long answer</option>
            <option value="Short">Short answer</option>
          </select>
        </label>
      </div>
      <button type="button" className="btn-secondary mt-3 text-sm text-red-300" onClick={onDelete}>
        Delete question
      </button>
    </div>
  );
}
