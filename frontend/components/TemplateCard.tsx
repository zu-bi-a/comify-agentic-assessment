"use client";

import { useState } from "react";
import type { Template } from "@/lib/types";
import { TemplatePreview } from "./TemplatePreview";

const CHANNEL_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  push: "Push",
};

export function TemplateCard({
  template,
  onEdit,
}: {
  template: Template;
  onEdit: (template: Template) => void;
}) {
  const [mode, setMode] = useState<"preview" | "template">("preview");

  return (
    <div className="template-card">
      <div className="template-card-top">
        <div className={`tc-channel tc-channel-${template.channel}`}>
          {CHANNEL_LABELS[template.channel] ?? template.channel}
        </div>
        <button type="button" className="edit-button" onClick={() => onEdit(template)}>
          Edit
        </button>
      </div>
      <div className="tc-title">{template.name}</div>
      <div className="mode-toggle" role="tablist" aria-label="View mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "preview"}
          className={mode === "preview" ? "active" : ""}
          onClick={() => setMode("preview")}
        >
          Preview
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "template"}
          className={mode === "template" ? "active" : ""}
          onClick={() => setMode("template")}
        >
          Template
        </button>
      </div>
      {mode === "preview" ? (
        <TemplatePreview template={template} />
      ) : (
        <pre>{JSON.stringify(template.payload, null, 2)}</pre>
      )}
    </div>
  );
}
