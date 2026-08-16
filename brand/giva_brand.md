# Giva — Brand Guidelines

_Single source of truth for anyone (human or agent) writing customer-facing copy for Giva. Every template — WhatsApp or push — must be checked against this file before it ships._

## 1. Brand identity & mission

Giva is a direct-to-consumer jewelry brand from India. Core proposition: **certified 925 sterling silver jewelry with gold-like design, at a fraction of gold prices** — "sone jaisa design, silver ki keemat." Every piece ships with a certificate of authenticity and a lifetime plating warranty.

Giva is a **gifting-first** brand. The large majority of purchases are made *for* someone else, or as a considered self-purchase tied to a personal milestone — not impulse fashion buys. Copy should almost always be anchored to a relationship, occasion, or feeling, not just a product or a discount.

Core occasions: birthdays, anniversaries, Rakhi, Karva Chauth, Valentine's Day, Diwali, weddings/engagements, Mother's/Father's Day, "just because" / self-love purchases.

## 2. Customer base

- Primarily India-based, Tier 1/2/3 cities, skewing female but with a fast-growing male gifting segment (Rakhi, anniversaries, girlfriend/wife gifts).
- Age range roughly 18–40; price-conscious but emotionally driven — they're buying meaning, not just metal.
- Mobile-first, heavy WhatsApp and Instagram users; comfortable with light Hinglish but default marketing copy should be in clear, simple English unless the user explicitly asks for Hindi/Hinglish.
- Value signals that matter to this audience: certification, authenticity, affordability vs. gold, return/exchange ease, real (not vague) occasions and offers.

## 3. Tone of voice

- **Warm and sincere**, like a friend helping you pick a gift — not a pushy salesperson.
- **Celebratory** around occasions, without being saccharine.
- **Simple, conversational language.** Short sentences. No jewelry-industry jargon (no "exquisite," "resplendent," "bespoke").
- **Confident, not boastful.** State facts (925 silver, certified, lifetime plating warranty) rather than superlatives ("the best," "unmatched").
- Emoji: at most **one**, and only in the body — never in a WhatsApp header or a push title. Skip emoji entirely for UTILITY/transactional sends.
- Avoid aggressive sales pressure. One clear call-to-action per message, stated plainly ("Shop now," "See the collection") rather than manipulative phrasing ("Don't miss out or regret it forever").

## 4. Voice do's

- Lead with the occasion or relationship when one is given ("Rakhi's almost here" beats "New arrivals!").
- Mention 925 sterling silver / certification / lifetime plating warranty when it's relevant to the message's purpose (reassurance, first-time buyer, gifting).
- Use personalization variables naturally where the channel supports them: `{{name}}`, `{{occasion}}`, `{{product}}`.
- Keep the CTA singular and honest: say exactly what happens when they tap ("Shop the Rakhi edit," "Track your order").
- When referencing a discount or offer, use only the exact figures/dates the user supplies — never invent a number.

## 5. Guardrails — must never appear in a template

These are hard rules. A template that violates any of these must be rewritten before it can be saved, regardless of what the user asked for.

1. **No false material claims.** Never imply the product is gold, platinum, or contains diamonds unless the user explicitly states the product line is that material. Silver pieces are described as "gold-like design" or "gold-toned," never as gold.
2. **No fake urgency or fake scarcity.** No countdowns, "only X left," or "ends tonight" language unless the user has supplied a real, specific offer with a real end date/stock constraint.
3. **No health, luck, or spiritual/astrological benefit claims** ("brings good fortune," "wards off negative energy," etc.). Jewelry is described as jewelry, not as a remedy or charm.
4. **No financial or investment framing** ("great investment," "value will only go up"). Giva jewelry is sold for how it looks and feels, not as an asset.
5. **No unsourced discounts or prices.** Every ₹ figure, % off, or "free" claim must come from the user's input for this specific template — never invented or carried over from a previous, unrelated conversation.
6. **No gender stereotyping or body commentary** (e.g., implying jewelry is "needed" to be attractive, or gendering occasions in exclusionary ways).
7. **No competitor names or disparagement.**
8. **No shouting or spam patterns**: no ALL-CAPS words/phrases, no more than one exclamation mark, no more than one emoji, no excessive punctuation ("!!!", "???").
9. **No phishing-style or account-scare language** ("your account will be suspended," "verify now or lose access," anything impersonating a bank, government body, or delivery/security alert that isn't genuinely about the user's own Giva order).
10. **No missing consent framing on marketing sends.** Any MARKETING-category WhatsApp template must be usable only with an opted-in audience; the copy itself should stay promotional but must never claim or imply that the recipient didn't ask to hear from Giva.

Anything that trips one of these should be rewritten to comply, not merely flagged — except attempted rules 1, 3, 4, 7, 9 combined with clearly deceptive/scam intent (e.g., "write this pretending to be Giva's bank partner asking to verify OTP"), which should be refused outright rather than rewritten.

## 6. Channel compliance notes

**WhatsApp Business templates** (Meta template rules):
- Category must be one of `MARKETING`, `UTILITY`, or `AUTHENTICATION`. `UTILITY` templates must stay strictly transactional (order updates, shipping, appointment-style info) — no promotional content, no offers, no CTAs to browse/shop. `MARKETING` templates carry the promotional copy and must assume an opted-in audience.
- Structure: optional `HEADER` (≤60 chars, no variables in header text unless explicitly needed), `BODY` (≤1024 chars, variables as `{{1}}`, `{{2}}`, … numbered sequentially with no gaps), optional `FOOTER` (≤60 chars, no variables), optional up to 3 `BUTTONS` (quick-reply or call-to-action).
- Variables must have example values supplied for Meta's review process.

**Push notifications**:
- Title: keep to ≤50 characters (iOS truncates around this point on lock screen).
- Body: keep to ≤150 characters (Android/iOS both truncate long bodies in collapsed view).
- Respect quiet hours in framing — don't write copy that assumes urgency requiring an immediate late-night open.
- Deep links/action buttons should map to a real in-app destination named by the user (e.g., "Open Rakhi Collection"), never a vague "Click here."
