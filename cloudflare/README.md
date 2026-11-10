# MedStudy AI — free Cloudflare Workers + D1 migration pilot

**Status: the Cloudflare Preview has been deployed. The new Telegram command gateway is implemented and offline-tested on this feature branch, but stays DISABLED by default. Not ready to replace Railway.**

Our goal is zero recurring platform charges for a small school cohort of
10–20 students (up to 35 maximum), without keeping a home computer running.

## Architecture

- Cloudflare Workers Free: future Python/FastAPI alternative for Telegram
  webhook and Mini App API (the proof of concept uses JavaScript).
- Cloudflare static assets: existing Telegram Mini App HTML/CSS/JavaScript and
  31 Preklinik SVG illustrations.
- Cloudflare D1 Free: permanent SQLite-compatible serverless database with
  Telegram approvals, consents and quiz history.
- Existing **Qdrant Cloud Free**: optional semantic-search vector index only;
  cannot run Telegram bots or replace the application backend.
- No paid LLM in this pilot. The simple lesson helper can be ported later
  without making API calls to paid inference services.

Current Free platform thresholds (verify before production rollout):
Cloudflare Workers Free offers 100,000 Worker requests per UTC day,
10 ms CPU time per request and 128 MB RAM. Static asset requests are free
and don't use Worker invocation quota. Cloudflare D1 Free offers 5 GB total
storage, 5 million rows read per day and 100,000 rows written per day.
This seems sufficient for 35 students' study materials and tests, but
our current API is not yet optimized or load-tested on Cloudflare itself.
When the limits are exceeded, requests can fail; $0 service is not a
100% uptime or free-forever guarantee.

References (official documentation):
https://developers.cloudflare.com/workers/platform/limits/
https://developers.cloudflare.com/workers/platform/pricing/
https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/

## What this pilot can already test

Run without any Cloudflare account or real Telegram key:

    node cloudflare/scripts/build-assets.mjs
    node --test cloudflare/test/*.test.mjs

- Health check: GET /api/health, returns migration_ready=false.
- Verify signed Telegram initData with HMAC-SHA256.
- Student access and approval read checks using mock/local D1.
- POST /api/consent for an approved account.
- GET /api/me, GET /api/catalog, GET /api/lessons/{id}.
- POST /api/attempts with graded full/retry/supplementary quizzes, D1 writes
  inside an atomic batch and a per-student rate limit.
- GET /api/progress, GET /api/history and GET /api/review/{lesson_id} with
  per-user authorization and no access to other students' scores.
- The original 6 subjects and 81 lesson descriptions are packaged locally.
- Static site and Preklinik illustration files are copied to deployable assets.

Not implemented, do not switch over yet:

- Activating and verifying the isolated test-bot webhook on Cloudflare with a separate Telegram bot.
- Real-cloud end-to-end signed student quiz tests and recovery from failure.
- Study planning, full AI Ustoz helper and optional Qdrant integration.
- Restoring private student SQLite data into D1 with consistency checks.
- Real-cloud testing and handling Cloudflare Free limits.

Remaining unimplemented API routes return an explicit 501. Telegram webhook returns 503 unless TELEGRAM_WEBHOOK_ENABLED=1, and requires correct secrets and the D1 replay-protection migration before use. Do not turn it on for the existing Railway bot.

## How to prepare an actual Cloudflare Free preview — when ready

1. Create a Cloudflare account using the official
   https://dash.cloudflare.com dashboard. Choose only the Free plan.
   Use the included workers.dev subdomain; a paid custom domain is not
   required. Do not supply payment details unless you understand charges.
2. Deploying this pilot requires Node.js and Wrangler 4 on a trusted
   development computer (or GitHub CI once connected). No Mac required.
3. Create D1 database named medstudy-ai-free. Put its ID into the
   cloudflare/wrangler.jsonc database_id field.
4. Apply cloudflare/migrations/0001_schema.sql to the **new D1 database**.
   This prepares only empty tables; NEVER upload student records via GitHub.
5. Set BOT_TOKEN only as a Cloudflare Worker encrypted secret. Do not put
   it in wrangler.jsonc, GitHub code, screenshots or chat. Better use a
   **different test Telegram bot**, because the production bot's webhook
   must stay on Railway until migration is complete.
6. Build assets, test locally and review permissions before deploying
   a preview URL on workers.dev.
7. Do not put a production bot token on an unfinished preview. Do not set
   a Telegram webhook until the webhook handler is implemented and tested.

### Manual commands (for an already provisioned Free Cloudflare account)

    cd cloudflare
    npm install
    npm run test
    npx wrangler d1 create medstudy-ai-free --config wrangler.jsonc
    # Copy ONLY the resulting D1 database ID into wrangler.jsonc.
    npx wrangler d1 migrations apply medstudy-ai-free --remote --config wrangler.jsonc
    npm run dev

No command above modifies Railway. The new D1 instance must be backed up
or exported separately; D1 is not the existing Railway SQLite file.

## Before replacing Railway

The production Telegram Mini App may be served by a different Railway
service from the backend used during Android development. We will
inventory all active services before any cutover. The Android application
remains unchanged, as requested.

The cutover will be allowed only after parity checks for all endpoints,
all Telegram bot commands, user approvals and the migration of quiz data.
Back up the old database securely, verify imported row counts, run signed
test-bot sessions and retain a rollback plan. Never overwrite newer
student progress with an older backup.

Keep Railway operating until the new application is fully compatible.


## New test-bot gateway (code only, OFF by default)

The preview feature branch now has a Telegram command gateway that handles
/start, /myid, /status, /privacy, and the admin commands /requests,
/approve ID, /reject ID, /revoke ID. It also handles inline approval buttons.
The webhook validates Telegram's secret header and rejects updates without it.
Replay protection uses the new D1 table telegram_updates; full Telegram
messages and student names are not stored.

We intentionally have NOT enabled the gateway or changed the Railway webhook.

1. Before deployment, keep this isolated preview on its own Worker name and
   ensure GitHub Actions tests pass.
2. Apply only the NEW second migration on the already-created D1 database:
   npx.cmd wrangler d1 migrations apply medstudy-ai-free --remote
3. Create a SEPARATE Telegram test bot. Do not use the Railway production bot.
   Do not send Bot API tokens, secret headers or personal IDs in chat/screenshots.
4. On the Cloudflare Worker, set BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET as
   encrypted Worker secrets for the test bot only. The webhook secret must be
   a random 16–256-character string made of letters, numbers, _ or -.
   ADMIN_USER_IDS must be set to the intended test administrator ID.
5. WEB_APP_URL should match the preview Worker origin. Only after reviewing
   configuration, opt in to TELEGRAM_WEBHOOK_ENABLED=1 on the test Worker.
   There is no automatic setWebhook, so registering
   https://medstudy-ai-free-preview.elyormakhmanazarov67.workers.dev/telegram/webhook
   as a Telegram webhook is a separate deliberate action for the TEST bot
   and must include the matching secret_token.
6. Verify student approval/revocation and the signed Mini App on the separate
   test bot before any possible production cutover.

No production bot token, student database or webhook is moved by this code
change. For more information see the official Telegram Bot API setWebhook
documentation: https://core.telegram.org/bots/api#setwebhook
