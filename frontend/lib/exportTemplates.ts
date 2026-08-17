import type { Template } from "./types";

function triggerDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function timestampedFilename(scopeLabel: string, ext: string): string {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return `giva-templates-${scopeLabel}-${stamp}.${ext}`;
}

export function exportTemplatesAsJson(templates: Template[], scopeLabel: string) {
  triggerDownload(
    JSON.stringify(templates, null, 2),
    timestampedFilename(scopeLabel, "json"),
    "application/json"
  );
}

const CSV_COLUMNS = [
  "id",
  "channel",
  "name",
  "category",
  "title",
  "header",
  "body",
  "footer",
  "buttons",
  "deep_link",
  "brand",
  "status",
  "created_at",
  "updated_at",
] as const;

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return "";
  const str = Array.isArray(value) ? value.join("; ") : String(value);
  if (/[",\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function exportTemplatesAsCsv(templates: Template[], scopeLabel: string) {
  const rows = templates.map((t) => {
    const record: Record<string, unknown> = {
      id: t.id,
      channel: t.channel,
      name: t.name,
      brand: t.brand,
      status: t.status,
      created_at: t.created_at,
      updated_at: t.updated_at,
      ...t.payload,
    };
    return CSV_COLUMNS.map((col) => csvEscape(record[col])).join(",");
  });
  const csv = [CSV_COLUMNS.join(","), ...rows].join("\n");
  triggerDownload(csv, timestampedFilename(scopeLabel, "csv"), "text/csv");
}
