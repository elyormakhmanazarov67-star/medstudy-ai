# MedStudy AI v1.0.2 — Public Free launch

- Production Free access requires Railway environment variable `PUBLIC_FREE_ENABLED=1`.
- With the flag off, previous `ALLOWED_USER_IDS` allowlist still restricts access. Do not remove the allowlist to enable Free.
- Each Mini App API request still requires valid, non-expired Telegram `initData` and per-user privacy consent.
- Telegram `/start` offers Mini App to any private-chat user when Free is open. `/myid` is still available but no longer required for Free.
- `ADMIN_USER_IDS` can explicitly designate admins; absent this variable, the existing `ALLOWED_USER_IDS` applies as the admin list. Free users are never promoted to admins.
- OpenAI is **not** a Free feature; the real AI endpoint and OpenAI opt-in remain admin-only until a separately tested Pro billing/entitlement system launches.
- Free lesson helper: max 12 requests per Telegram user per UTC minute. Quiz submissions: max 20 per minute per user. Quotas are stored as tiny SQLite counters in a new non-destructive table.
- No PDF/document upload or download, no recurring paid charge, no user billing or subscription.
- Old SQLite volume and users remain untouched; `CREATE TABLE IF NOT EXISTS` adds only a rate-limit table.
- Existing educational content includes drafts; not a medical or university-certified clinical instruction.
- To revert public enrollment safely, set `PUBLIC_FREE_ENABLED=0`, leaving the owner allowlist intact.

## Acceptance checks
1. Signed Telegram `initData` for an unlisted user: `/api/me` 200, `/api/catalog` 403 before consent and 200 after consent.
2. Anonymous or expired / tampered `initData`: 401.
3. Public users cannot call `/api/tutor/ask` or activate OpenAI consent, even if an API key is present.
4. Scores and account deletion remain scoped to the authenticated Telegram ID.
5. `/start` offers the Mini App in production; database persists across deployment.
