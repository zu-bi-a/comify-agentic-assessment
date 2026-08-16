from __future__ import annotations

import re
from pathlib import Path

from agents import RunContextWrapper, function_tool

from . import store
from .context import GivaContext

BRAND_MD_PATH = Path(__file__).resolve().parent.parent / "brand" / "giva_brand.md"

_SECTION_ALIASES = {
    "identity": "1. Brand identity & mission",
    "mission": "1. Brand identity & mission",
    "audience": "2. Customer base",
    "customer": "2. Customer base",
    "customer base": "2. Customer base",
    "tone": "3. Tone of voice",
    "voice": "3. Tone of voice",
    "dos": "4. Voice do's",
    "guardrails": "5. Guardrails",
    "compliance": "6. Channel compliance notes",
    "channel": "6. Channel compliance notes",
}

RED_FLAG_PHRASES = [
    "real gold", "genuine gold", "pure gold", "solid gold", "real diamond",
    "great investment", "value will", "good fortune", "negative energy",
    "brings luck", "wards off", "verify now", "account will be suspended",
    "verify your account", "only 2 left", "act now or", "don't miss out or",
]


def _read_brand_md() -> str:
    return BRAND_MD_PATH.read_text(encoding="utf-8")


def _extract_section(full_text: str, heading_snippet: str) -> str:
    lines = full_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and heading_snippet.lower() in line.lower():
            start = i
            break
    if start is None:
        return full_text
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip()


@function_tool
def get_brand_guidelines(section: str | None = None) -> str:
    """Read the Giva brand guidelines.

    Args:
        section: Optional keyword to scope the result to one section
            (e.g. "tone", "guardrails", "audience", "compliance"). Omit for the
            full brand document.
    """
    full_text = _read_brand_md()
    if not section:
        return full_text
    heading = _SECTION_ALIASES.get(section.strip().lower())
    if not heading:
        return full_text
    return _extract_section(full_text, heading)


@function_tool
def get_whatsapp_template_specs() -> str:
    """Return WhatsApp Business template structural rules (Meta template guidelines)."""
    return (
        "WhatsApp Business template rules:\n"
        "- Category: one of MARKETING, UTILITY, AUTHENTICATION.\n"
        "  UTILITY must be strictly transactional (no offers/CTAs to browse).\n"
        "  MARKETING carries promotional copy and assumes an opted-in audience.\n"
        "- HEADER: optional, <=60 chars, plain text.\n"
        "- BODY: required, <=1024 chars, variables written as {{1}}, {{2}}, ... "
        "numbered sequentially with no gaps.\n"
        "- FOOTER: optional, <=60 chars, no variables.\n"
        "- BUTTONS: optional, up to 3, quick-reply or call-to-action type.\n"
        "- Every {{n}} variable needs an example value for Meta's review."
    )


@function_tool
def get_push_notification_specs() -> str:
    """Return mobile push notification structural limits (iOS/Android)."""
    return (
        "Push notification rules:\n"
        "- Title: <=50 characters (iOS lock-screen truncation point).\n"
        "- Body: <=150 characters (Android/iOS collapse longer bodies).\n"
        "- Optional deep link / action button should name a real in-app destination.\n"
        "- Respect quiet hours in the framing; avoid copy implying urgent late-night action."
    )


@function_tool
def validate_template_structure(
    channel: str,
    body: str,
    title: str | None = None,
    header: str | None = None,
    footer: str | None = None,
    buttons: list[str] | None = None,
) -> str:
    """Deterministically validate a drafted template against channel limits and brand red-flag phrases.

    Args:
        channel: "whatsapp" or "push".
        body: Main message body (required for both channels).
        title: Push notification title (push only).
        header: WhatsApp header text (whatsapp only).
        footer: WhatsApp footer text (whatsapp only).
        buttons: List of button labels (whatsapp only, max 3).
    """
    issues: list[str] = []
    channel = channel.strip().lower()

    if channel == "whatsapp":
        if header and len(header) > 60:
            issues.append(f"Header is {len(header)} chars, exceeds 60-char limit.")
        if len(body) > 1024:
            issues.append(f"Body is {len(body)} chars, exceeds 1024-char limit.")
        if footer and len(footer) > 60:
            issues.append(f"Footer is {len(footer)} chars, exceeds 60-char limit.")
        if buttons and len(buttons) > 3:
            issues.append(f"{len(buttons)} buttons supplied, WhatsApp allows max 3.")
        var_numbers = [int(n) for n in re.findall(r"\{\{(\d+)\}\}", body)]
        if var_numbers:
            unique_sorted = sorted(set(var_numbers))
            expected = list(range(1, len(unique_sorted) + 1))
            if unique_sorted != expected:
                issues.append(
                    f"Template variables {unique_sorted} are not sequential "
                    f"starting at {{{{1}}}} with no gaps."
                )
    elif channel == "push":
        if title and len(title) > 50:
            issues.append(f"Title is {len(title)} chars, exceeds 50-char limit.")
        if len(body) > 150:
            issues.append(f"Body is {len(body)} chars, exceeds 150-char limit.")
    else:
        issues.append(f"Unknown channel '{channel}', expected 'whatsapp' or 'push'.")

    full_text = " ".join(filter(None, [title, header, body, footer, *(buttons or [])]))

    if re.search(r"\b[A-Z]{4,}\b", full_text):
        issues.append("Contains an ALL-CAPS word/phrase — avoid shouting.")
    if full_text.count("!") > 1:
        issues.append("More than one exclamation mark used.")
    if len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", full_text)) > 1:
        issues.append("More than one emoji used.")
    lowered = full_text.lower()
    for phrase in RED_FLAG_PHRASES:
        if phrase in lowered:
            issues.append(f'Contains red-flag phrase: "{phrase}" — check brand guardrails.')

    if not issues:
        return "VALID: no structural or red-flag issues found."
    return "ISSUES FOUND:\n- " + "\n- ".join(issues)


@function_tool
def save_whatsapp_template(
    ctx: RunContextWrapper[GivaContext],
    name: str,
    category: str,
    body: str,
    header: str | None = None,
    footer: str | None = None,
    buttons: list[str] | None = None,
) -> str:
    """Persist a finalized, user-approved WhatsApp template to the template store.

    Args:
        name: Short internal name for this template, e.g. "rakhi_2026_marketing".
        category: "MARKETING", "UTILITY", or "AUTHENTICATION".
        body: Main message body, with {{1}}, {{2}}, ... variables as needed.
        header: Optional header text.
        footer: Optional footer text.
        buttons: Optional list of button labels (max 3).
    """
    payload = {
        "category": category,
        "header": header,
        "body": body,
        "footer": footer,
        "buttons": buttons or [],
    }
    record = store.add_template("whatsapp", name, ctx.context.brand_name, payload)
    return f"Saved WhatsApp template '{name}' with id {record['id']}."


@function_tool
def save_push_template(
    ctx: RunContextWrapper[GivaContext],
    name: str,
    title: str,
    body: str,
    deep_link: str | None = None,
) -> str:
    """Persist a finalized, user-approved push notification template to the template store.

    Args:
        name: Short internal name for this template, e.g. "rakhi_2026_push".
        title: Notification title.
        body: Notification body.
        deep_link: Optional in-app destination for the notification's action.
    """
    payload = {"title": title, "body": body, "deep_link": deep_link}
    record = store.add_template("push", name, ctx.context.brand_name, payload)
    return f"Saved push template '{name}' with id {record['id']}."


@function_tool
def list_saved_templates(channel: str | None = None) -> str:
    """List previously saved templates, optionally filtered by channel ("whatsapp" or "push")."""
    templates = store.list_templates(channel)
    if not templates:
        return "No templates saved yet."
    lines = [
        f"- [{t['channel']}] {t['name']} (id={t['id']}, created={t['created_at']})"
        for t in templates
    ]
    return "\n".join(lines)
