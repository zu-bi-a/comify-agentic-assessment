"use client";

import { useMemo, useState } from "react";
import { exportTemplatesAsCsv, exportTemplatesAsJson } from "@/lib/exportTemplates";
import type { Template } from "@/lib/types";
import { TemplateCard } from "./TemplateCard";

type ChannelFilter = "all" | "whatsapp" | "push";

const FILTER_LABELS: Record<ChannelFilter, string> = {
  all: "All",
  whatsapp: "WhatsApp",
  push: "Push",
};

export function TemplatesSidebar({
  templates,
  onEdit,
}: {
  templates: Template[];
  onEdit: (template: Template) => void;
}) {
  const [filter, setFilter] = useState<ChannelFilter>("all");

  const filtered = useMemo(
    () => (filter === "all" ? templates : templates.filter((t) => t.channel === filter)),
    [templates, filter]
  );

  const exportDisabled = filtered.length === 0;

  return (
    <aside className="templates-pane">
      <div className="templates-pane-header">
        <h2>Saved templates</h2>
        {templates.length > 0 && <span className="templates-count">{filtered.length}</span>}
      </div>
      <div className="channel-filter" role="tablist" aria-label="Filter by channel">
        {(Object.keys(FILTER_LABELS) as ChannelFilter[]).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={filter === key}
            className={filter === key ? "active" : ""}
            onClick={() => setFilter(key)}
          >
            {FILTER_LABELS[key]}
          </button>
        ))}
      </div>
      <div className="export-actions">
        <span className="export-label">Export {FILTER_LABELS[filter].toLowerCase()}:</span>
        <button
          type="button"
          disabled={exportDisabled}
          onClick={() => exportTemplatesAsJson(filtered, filter)}
        >
          JSON
        </button>
        <button
          type="button"
          disabled={exportDisabled}
          onClick={() => exportTemplatesAsCsv(filtered, filter)}
        >
          CSV
        </button>
      </div>
      {filtered.length === 0 ? (
        <div className="empty-state">
          {templates.length === 0 ? "No templates saved yet." : "No templates match this filter."}
        </div>
      ) : (
        [...filtered].reverse().map((t) => <TemplateCard key={t.id} template={t} onEdit={onEdit} />)
      )}
    </aside>
  );
}
