import type { Template } from "@/lib/types";

function TemplateCard({ template }: { template: Template }) {
  return (
    <div className="template-card">
      <div className="tc-channel">{template.channel}</div>
      <div className="tc-title">{template.name}</div>
      <pre>{JSON.stringify(template.payload, null, 2)}</pre>
    </div>
  );
}

export function TemplatesSidebar({ templates }: { templates: Template[] }) {
  return (
    <aside className="templates-pane">
      <h2>Saved templates</h2>
      {templates.length === 0 ? (
        <div className="empty-state">No templates saved yet.</div>
      ) : (
        [...templates].reverse().map((t) => <TemplateCard key={t.id} template={t} />)
      )}
    </aside>
  );
}
