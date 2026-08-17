import type { Template } from "@/lib/types";

function fillPlaceholders(text?: string | null): string {
  if (!text) return "";
  return text.replace(/\{\{(\d+)\}\}/g, (_match, n: string) =>
    n === "1" ? "Priya" : `[Detail ${n}]`
  );
}

function WhatsAppPreview({ payload }: { payload: Record<string, unknown> }) {
  const header = payload.header as string | null | undefined;
  const body = payload.body as string | undefined;
  const footer = payload.footer as string | null | undefined;
  const buttons = (payload.buttons as string[] | undefined) ?? [];

  return (
    <div className="preview-card preview-whatsapp">
      <div className="preview-bubble">
        {header && <div className="preview-header">{fillPlaceholders(header)}</div>}
        <div className="preview-body">{fillPlaceholders(body)}</div>
        {footer && <div className="preview-footer">{fillPlaceholders(footer)}</div>}
      </div>
      {buttons.length > 0 && (
        <div className="preview-buttons">
          {buttons.map((label) => (
            <div key={label} className="preview-button">
              {label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PushPreview({ payload }: { payload: Record<string, unknown> }) {
  const title = payload.title as string | undefined;
  const body = payload.body as string | undefined;

  return (
    <div className="preview-card preview-push">
      <div className="preview-push-meta">
        <span className="preview-push-icon" aria-hidden="true">
          G
        </span>
        <span className="preview-push-app">Giva</span>
        <span className="preview-push-time">now</span>
      </div>
      <div className="preview-push-title">{fillPlaceholders(title)}</div>
      <div className="preview-push-body">{fillPlaceholders(body)}</div>
    </div>
  );
}

export function TemplatePreview({ template }: { template: Template }) {
  return template.channel === "whatsapp" ? (
    <WhatsAppPreview payload={template.payload} />
  ) : (
    <PushPreview payload={template.payload} />
  );
}
