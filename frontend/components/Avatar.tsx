import type { MessageRole } from "@/lib/types";

export function Avatar({ role }: { role: MessageRole }) {
  if (role === "system") return null;
  return (
    <div className={`avatar avatar-${role}`} aria-hidden="true">
      {role === "user" ? "Y" : "G"}
    </div>
  );
}
