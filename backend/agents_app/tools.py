from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from agents import RunContextWrapper, function_tool

from . import store
from .context import GivaContext
from .observability import observability_span

BRAND_MD_PATH = Path(__file__).resolve().parent.parent / "brand" / "giva_brand.md"
CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "brand" / "catalogue.json"

CATALOGUE_MATCH_CONFIDENCE_THRESHOLD = 0.6
TEMPLATE_SIMILARITY_THRESHOLD = 0.55

# Words too generic across this catalogue's descriptions to discriminate between
# collections (e.g. "pieces" and "jewelry" appear almost everywhere).
CATALOGUE_STOP_WORDS = {
    "pieces", "piece", "jewelry", "jewellery", "silver", "collection",
    "collections", "designs", "design", "wear", "gifting", "gifts", "gift",
    "catalogue", "catalog",
}

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


def _load_catalogue() -> list[dict]:
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def _catalogue_match_score(query: str, collection: dict) -> float:
    """Score how well a collection matches free-text query wording.

    Combines literal name similarity (catches "spring catalogue" ~= "Spring
    Bloom Collection") with description keyword overlap (catches
    semantically-related-but-lexically-different wording, e.g. "wedding
    pieces" ~= Bridal Shine's description, "diwali gifts" ~= Festive
    Gold-Tone's description, since those keywords live in the description
    rather than the name).
    """
    query_lower = query.lower().strip()
    name_lower = collection["name"].lower()
    description_lower = collection["description"].lower()
    query_words = [
        w
        for w in re.findall(r"[a-z]+", query_lower)
        if len(w) > 3 and w not in CATALOGUE_STOP_WORDS
    ]

    name_ratio = difflib.SequenceMatcher(None, query_lower, name_lower).ratio()

    name_bonus = 0.0
    if query_lower in name_lower:
        name_bonus = 0.3
    elif query_words and any(w in name_lower for w in query_words):
        name_bonus = 0.2

    desc_bonus = 0.0
    if query_words:
        desc_hits = sum(1 for w in query_words if w in description_lower)
        desc_bonus = 0.45 * (desc_hits / len(query_words))

    return min(name_ratio + max(name_bonus, desc_bonus), 1.0)


def _text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _keyword_match_score(query: str, text: str) -> float:
    """Fraction of the query's meaningful words found in text -- suited to
    topic search ("diwali offer") against a template's name/tags/body, unlike
    _text_similarity which compares two whole drafts to each other."""
    query_words = [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2]
    if not query_words:
        return 0.0
    text_lower = text.lower()
    return sum(1 for w in query_words if w in text_lower) / len(query_words)


def _template_search_text(record: dict) -> str:
    payload = record.get("payload") or {}
    parts = [
        record.get("name", ""),
        " ".join(record.get("tags") or []),
        str(payload.get("body", "")),
        str(payload.get("title", "")),
    ]
    return " ".join(p for p in parts if p)


def _auto_tags(
    ctx: RunContextWrapper[GivaContext],
    explicit_tags: list[str] | None,
    category: str | None = None,
) -> list[str] | None:
    """Merge agent-supplied tags with signals the app already tracks
    automatically (confirmed catalogue collection, category), so tagging
    doesn't rely entirely on the agent remembering to pass tags -- the user
    never has to enter any of this themselves."""
    auto: list[str] = []
    if ctx.context.confirmed_collection:
        auto.append(ctx.context.confirmed_collection)
    if category:
        auto.append(category)
    combined = {t.strip().lower() for t in (explicit_tags or []) + auto if t and t.strip()}
    return sorted(combined) or None


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
def list_catalogue_collections() -> str:
    """List all real Giva product collections available to reference in a template."""
    collections = _load_catalogue()
    lines = [f"- {c['name']}: {c['description']}" for c in collections]
    return "\n".join(lines)


@function_tool
def find_catalogue_collection(ctx: RunContextWrapper[GivaContext], query: str) -> str:
    """Find the Giva product collection(s) that best match a user's own wording
    (e.g. "spring catalogue", "rakhi stuff", "wedding pieces"). Always call this
    when the user references a collection/catalogue by name, even if their wording
    isn't exact -- then confirm the match with the user (e.g. via
    offer_quick_replies with the candidate name(s)) before using it in a draft.
    Never invent a collection name that isn't in the catalogue.

    Args:
        query: The user's own wording for the collection they mean.
    """
    collections = _load_catalogue()
    scored = sorted(
        ((_catalogue_match_score(query, c), c) for c in collections),
        key=lambda pair: pair[0],
        reverse=True,
    )
    best_score, best = scored[0]
    if best_score >= CATALOGUE_MATCH_CONFIDENCE_THRESHOLD:
        # Auto-captured for tagging (find_similar_templates / save_*) so
        # tagging doesn't depend on the agent remembering to repeat it.
        ctx.context.confirmed_collection = best["name"]
        return (
            f"Best match ({best_score:.2f} confidence): {best['name']} -- "
            f"{best['description']}. Confirm this with the user before using it."
        )
    top = scored[:3]
    lines = [f"- {c['name']}: {c['description']} (confidence {s:.2f})" for s, c in top]
    return (
        "No confident single match. Ask the user to pick from the closest "
        "candidates:\n" + "\n".join(lines)
    )


@function_tool
async def find_similar_templates(
    ctx: RunContextWrapper[GivaContext],
    channel: str,
    draft_body: str,
    category: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Check whether a saved template already closely matches the one you're
    about to create. Call this once you've written an initial draft body --
    same step as validate_template_structure -- and BEFORE showing the draft
    to the user.

    Args:
        channel: "whatsapp" or "push".
        draft_body: The main body text of your current draft.
        category: WhatsApp category if known (MARKETING/UTILITY/AUTHENTICATION).
            Omit for push.
        tags: Short freeform keywords for this template's occasion/collection/
            topic that you're confident about from the conversation so far
            (e.g. ["rakhi", "marketing"]). Omit if unsure -- this only narrows
            the search, it doesn't have to be exact. (Only used to narrow this
            search, not stored -- doesn't need to match what you'll pass at
            save time.)
    """
    candidates = await store.find_candidate_templates(
        ctx.context.brand_name, channel.strip().lower(), category, tags
    )
    if not candidates:
        with observability_span(
            "duplicate_check", data={"candidate_count": 0, "matched": False}
        ):
            return "No similar saved templates found."

    scored = sorted(
        (
            (_text_similarity(draft_body, c["payload"].get("body", "")), c)
            for c in candidates
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    best_score, best = scored[0]
    matched = best_score >= TEMPLATE_SIMILARITY_THRESHOLD
    with observability_span(
        "duplicate_check",
        data={
            "candidate_count": len(candidates),
            "best_score": round(best_score, 3),
            "threshold": TEMPLATE_SIMILARITY_THRESHOLD,
            "matched": matched,
            "matched_template_id": best["id"] if matched else None,
        },
    ):
        if not matched:
            return "No closely similar saved template found."
        return (
            f"A similar template already exists ({best_score:.2f} similarity): "
            f"'{best['name']}' (id={best['id']}, saved {best['created_at']}). Do "
            "NOT just present your draft as normal -- call offer_quick_replies "
            "with options like [\"Create a variation\", \"View existing\", "
            "\"Continue anyway\", \"Cancel\"] and ask the user how they'd like to "
            "proceed, mentioning the existing template's name, before showing or "
            "saving your draft."
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
async def save_whatsapp_template(
    ctx: RunContextWrapper[GivaContext],
    name: str,
    category: str,
    body: str,
    header: str | None = None,
    footer: str | None = None,
    buttons: list[str] | None = None,
    tags: list[str] | None = None,
) -> str:
    """Persist a finalized, user-approved WhatsApp template to the template store.

    Args:
        name: Short internal name for this template, e.g. "rakhi_2026_marketing".
        category: "MARKETING", "UTILITY", or "AUTHENTICATION".
        body: Main message body, with {{1}}, {{2}}, ... variables as needed.
        header: Optional header text.
        footer: Optional footer text.
        buttons: Optional list of button labels (max 3).
        tags: Optional extra occasion/topic keywords, e.g. ["rakhi"]. The
            category and any confirmed catalogue collection are tagged
            automatically -- this is only for anything extra you know.
    """
    payload = {
        "category": category,
        "header": header,
        "body": body,
        "footer": footer,
        "buttons": buttons or [],
    }
    record = await store.add_template(
        "whatsapp",
        name,
        ctx.context.brand_name,
        payload,
        category=category,
        tags=_auto_tags(ctx, tags, category),
    )
    return f"Saved WhatsApp template '{name}' with id {record['id']}."


@function_tool
async def save_push_template(
    ctx: RunContextWrapper[GivaContext],
    name: str,
    title: str,
    body: str,
    deep_link: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Persist a finalized, user-approved push notification template to the template store.

    Args:
        name: Short internal name for this template, e.g. "rakhi_2026_push".
        title: Notification title.
        body: Notification body.
        deep_link: Optional in-app destination for the notification's action.
        tags: Optional extra occasion/topic keywords, e.g. ["rakhi"]. Any
            confirmed catalogue collection is tagged automatically -- this is
            only for anything extra you know.
    """
    payload = {"title": title, "body": body, "deep_link": deep_link}
    record = await store.add_template(
        "push", name, ctx.context.brand_name, payload, tags=_auto_tags(ctx, tags)
    )
    return f"Saved push template '{name}' with id {record['id']}."


@function_tool
async def load_template_for_editing(ctx: RunContextWrapper[GivaContext], template_id: str) -> str:
    """Load a previously saved template so it can be edited. Call this as your
    first action when the user wants to edit a specific saved template, before
    anything else. Remembers the id so that once the user approves a revised
    draft, you update this same template instead of saving a new one.

    Args:
        template_id: The id of the saved template to edit.
    """
    record = await store.get_template(template_id)
    if record is None:
        return f"No saved template found with id {template_id}. It may have been removed."
    ctx.context.editing_template_id = template_id
    payload = record["payload"]
    fields = "\n".join(f"- {k}: {v}" for k, v in payload.items())
    return (
        f"Loaded '{record['name']}' ({record['channel']}) for editing:\n{fields}\n\n"
        "If the user already described the change they want -- anywhere "
        "earlier in this conversation, including the message that prompted "
        "this edit -- apply it directly to the content above and present the "
        "revised draft; do not ask them to repeat it. Only ask how they'd "
        "like to modify it if they haven't said yet."
    )


@function_tool
async def update_whatsapp_template(
    ctx: RunContextWrapper[GivaContext],
    template_id: str,
    name: str,
    category: str,
    body: str,
    header: str | None = None,
    footer: str | None = None,
    buttons: list[str] | None = None,
    tags: list[str] | None = None,
) -> str:
    """Save a revised WhatsApp template over an existing saved entry (in place,
    not as a new template). Only call this after the user has approved the
    revised draft during an edit flow started with load_template_for_editing.

    Args:
        template_id: The id of the template being edited (from load_template_for_editing).
        name: Internal name for this template.
        category: "MARKETING", "UTILITY", or "AUTHENTICATION".
        body: Main message body, with {{1}}, {{2}}, ... variables as needed.
        header: Optional header text.
        footer: Optional footer text.
        buttons: Optional list of button labels (max 3).
        tags: Optional extra occasion/topic keywords, e.g. ["rakhi"]. The
            category and any confirmed catalogue collection are tagged
            automatically -- this is only for anything extra you know.
    """
    payload = {
        "category": category,
        "header": header,
        "body": body,
        "footer": footer,
        "buttons": buttons or [],
    }
    record = await store.update_template(
        template_id, name, payload, category=category, tags=_auto_tags(ctx, tags, category)
    )
    if record is None:
        return f"No saved template found with id {template_id} -- could not update."
    ctx.context.editing_template_id = None
    return f"Updated WhatsApp template '{name}' (id {template_id})."


@function_tool
async def update_push_template(
    ctx: RunContextWrapper[GivaContext],
    template_id: str,
    name: str,
    title: str,
    body: str,
    deep_link: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Save a revised push notification template over an existing saved entry (in
    place, not as a new template). Only call this after the user has approved the
    revised draft during an edit flow started with load_template_for_editing.

    Args:
        template_id: The id of the template being edited (from load_template_for_editing).
        name: Internal name for this template.
        title: Notification title.
        body: Notification body.
        deep_link: Optional in-app destination for the notification's action.
        tags: Optional extra occasion/topic keywords, e.g. ["rakhi"]. Any
            confirmed catalogue collection is tagged automatically -- this is
            only for anything extra you know.
    """
    payload = {"title": title, "body": body, "deep_link": deep_link}
    record = await store.update_template(
        template_id, name, payload, tags=_auto_tags(ctx, tags)
    )
    if record is None:
        return f"No saved template found with id {template_id} -- could not update."
    ctx.context.editing_template_id = None
    return f"Updated push template '{name}' (id {template_id})."


@function_tool
def offer_quick_replies(ctx: RunContextWrapper[GivaContext], options: list[str]) -> str:
    """Attach clickable quick-reply buttons to your current message, for when you're
    asking the user to choose between a small set of good, discrete answers (e.g.
    "WhatsApp or push?", a template category, common occasion presets, or
    approve-vs-revise on a draft).

    Call this BEFORE writing your reply text, then write the one message asking
    the question as the very next thing you do. Do not write your question first
    and call this afterward, and do not send another message after calling this --
    the tool call, then one message, is the whole turn.

    Don't call this for open-ended or subjective questions where the user needs to
    describe something in their own words (e.g. the exact message copy, custom offer
    details, who the audience is) -- just ask normally and let them type.

    Args:
        options: 2-5 short button labels, e.g. ["WhatsApp template", "Push notification"].
    """
    ctx.context.pending_quick_replies = list(options)[:5]
    return "Quick replies attached to this turn."


@function_tool
async def list_saved_templates(channel: str | None = None) -> str:
    """List previously saved templates, optionally filtered by channel ("whatsapp" or "push")."""
    templates = await store.list_templates(channel)
    if not templates:
        return "No templates saved yet."
    lines = [
        f"- [{t['channel']}] {t['name']} (id={t['id']}, created={t['created_at']})"
        for t in templates
    ]
    return "\n".join(lines)


@function_tool
async def search_saved_templates(
    ctx: RunContextWrapper[GivaContext], query: str, channel: str | None = None
) -> str:
    """Check whether a saved template already exists for a topic/occasion the
    user describes in their own words (e.g. "diwali offer", "welcome
    message"). Use this -- not list_saved_templates -- whenever the user asks
    something like "do I have a template for X?".

    Args:
        query: The user's own wording for what they're looking for.
        channel: Optional "whatsapp" or "push" to narrow the search.
    """
    records = await store.list_templates_by_brand(
        ctx.context.brand_name, channel.strip().lower() if channel else None
    )
    if not records:
        return "No saved templates yet."
    scored = sorted(
        ((_keyword_match_score(query, _template_search_text(r)), r) for r in records),
        key=lambda pair: pair[0],
        reverse=True,
    )
    matches = [(s, r) for s, r in scored if s > 0][:5]
    if not matches:
        return f"No saved templates found matching '{query}'."
    lines = [
        f"- [{r['channel']}] {r['name']} (id={r['id']}, created={r['created_at']})"
        for _, r in matches
    ]
    return "Possible matches:\n" + "\n".join(lines)
