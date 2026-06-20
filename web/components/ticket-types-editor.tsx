"use client";

import { useCallback, useEffect, useState } from "react";
import { tickrFetchClient } from "@/lib/api-client";

type TicketType = {
  Status: string;
  Emoji: string;
  Description: string;
  Category: number | null;
  PrivateMode: string | null;
  Message: string;
  Questions: { Label: string; Placeholder: string; Length: string }[];
};

type Props = { guildId: string };

export function TicketTypesEditor({ guildId }: Props) {
  const [data, setData] = useState<Record<string, unknown>>({});
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("");
  const [newCategory, setNewCategory] = useState("");
  const [newType, setNewType] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await tickrFetchClient(`/guilds/${guildId}/ticket-types`);
      setData(resp.data || {});
      setCategories(resp.categories || []);
      if (!selectedCategory && resp.categories?.length) {
        setSelectedCategory(resp.categories[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [guildId, selectedCategory]);

  useEffect(() => {
    load();
  }, [load]);

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
    await load();
  }

  async function addType() {
    if (!selectedCategory || !newType.trim()) return;
    await tickrFetchClient(`/guilds/${guildId}/ticket-types/categories/${encodeURIComponent(selectedCategory)}/types`, {
      method: "POST",
      body: JSON.stringify({ name: newType.trim() }),
    });
    setNewType("");
    await load();
  }

  async function updateTypeField(field: string, value: unknown) {
    if (!selectedCategory || !selectedType || !currentType) return;
    const updated = { ...currentType, [field]: value };
    await tickrFetchClient(
      `/guilds/${guildId}/ticket-types/categories/${encodeURIComponent(selectedCategory)}/types/${encodeURIComponent(selectedType)}`,
      { method: "PUT", body: JSON.stringify({ data: updated }) },
    );
    await load();
  }

  async function toggleGlobal() {
    const status = data.TOGGLE_STATUS === "Disabled" ? "Enabled" : "Disabled";
    await tickrFetchClient(`/guilds/${guildId}/ticket-types/toggle-global`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await load();
  }

  if (loading) return <p className="text-[var(--text-muted)]">Loading ticket types...</p>;

  return (
    <div className="space-y-6">
      {error && <div className="text-red-300">{error}</div>}
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
            {typesInCategory.map((t) => (
              <li key={t}>
                <button
                  type="button"
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm ${
                    selectedType === t ? "bg-[var(--accent)]" : "hover:bg-[var(--bg-tertiary)]"
                  }`}
                  onClick={() => setSelectedType(t)}
                >
                  {t}
                </button>
              </li>
            ))}
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

        <div className="glass-card p-4 lg:col-span-1">
          <h3 className="mb-3 font-semibold">Type details</h3>
          {!currentType ? (
            <p className="text-sm text-[var(--text-muted)]">Select a ticket type.</p>
          ) : (
            <div className="space-y-3">
              <label className="block text-sm">
                Emoji
                <input
                  className="input-field mt-1"
                  value={currentType.Emoji}
                  onChange={(e) => updateTypeField("Emoji", e.target.value)}
                />
              </label>
              <label className="block text-sm">
                Description
                <input
                  className="input-field mt-1"
                  value={currentType.Description}
                  onChange={(e) => updateTypeField("Description", e.target.value)}
                />
              </label>
              <label className="block text-sm">
                Status
                <select
                  className="select-field mt-1"
                  value={currentType.Status}
                  onChange={(e) => updateTypeField("Status", e.target.value)}
                >
                  <option value="Enabled">Enabled</option>
                  <option value="Disabled">Disabled</option>
                </select>
              </label>
              <label className="block text-sm">
                Opening message
                <textarea
                  className="input-field mt-1 min-h-[80px]"
                  value={currentType.Message}
                  onChange={(e) => updateTypeField("Message", e.target.value)}
                />
              </label>
              <div>
                <p className="mb-2 text-sm font-medium">Questions</p>
                <ul className="space-y-1 text-sm text-[var(--text-secondary)]">
                  {currentType.Questions?.map((q) => (
                    <li key={q.Label}>
                      {q.Label} ({q.Length})
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
