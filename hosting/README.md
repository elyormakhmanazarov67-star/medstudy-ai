# MedStudy AI — preparing our own cloud server (10–35 students)

Status: **prepared for testing, not deployed**. This folder prepares a provider-neutral Linux VPS. It does NOT create a cloud account, move the Railway database, alter Android, or switch the current Telegram bot.

## Initial capacity

- Expected active audience: 10–20 students; possible maximum 35.
- Workload: lessons, quizzes, approved Telegram Mini App users, lightweight SVG diagrams. No local large language model.
- Starting VM target: 1 vCPU, 1 GB RAM and 10+ GB persistent disk. Prefer 2 GB RAM if available. This is an estimate, not a concurrency/load-test guarantee.
- Start one FastAPI instance with SQLite and monitor memory, CPU, disk, response times and SQLite lock errors. Do not start multiple API replicas against the same file.

## Preflight on a separately created Linux cloud VM

Requirements: Ubuntu/Debian, Docker Engine and Docker Compose plugin, a DNS hostname pointing at the VM, ports TCP 80 and 443 open, a narrowly restricted SSH access rule, and backups stored off the VM.

From the cloned repository root:

    cd hosting
    cp .env.example .env
    # On the VM only: fill SITE_DOMAIN and WEB_APP_URL with YOUR domain.
    # Use TEST credentials for any preview. Never commit hosting/.env.
    docker compose config --quiet
    docker compose up -d --build
    docker compose ps
    curl --fail https://YOUR_PREVIEW_DOMAIN/api/health

Caddy obtains and renews free HTTPS certificates after DNS/ports work. The API listens only on its internal container network; Caddy is the public ingress. SQLite resides in the persistent Docker volume called medstudy_data.

The Compose file forces AUTO_SET_WEBHOOK=0, DEV_PREVIEW=0 and AI_ENABLED=0. It must NOT reassign the existing Telegram production webhook as part of a preview. A copied BOT_TOKEN alone does not authorize changing the webhook; use a separate test Telegram bot whenever possible.

## Backup before any Railway expiry

From the hosting directory of an already-running VPS deployment:

    bash backup.sh

This runs SQLite's online-backup API inside the application container, exports a consistent snapshot to hosting/backups on the Linux host, and checks PRAGMA integrity_check. The backup filename includes its UTC timestamp. It is readable only to its owner by default.

Backups on the same VM are NOT disaster recovery. Move an encrypted copy to separate storage and practice restoring it on an isolated server. Do not upload SQLite files or credentials to a GitHub repository or a chat.

## Migration plan (not yet performed)

1. Inventory existing Railway services and storage. The Mini App and the Android/mobile staging service have separate databases and account flows; these are NOT interchangeable. Android remains unchanged.
2. Take consistent database backups from each relevant Railway persistent volume. Use SQLite backup API, not a blind copy of a file while active writes or WAL journaling might be present.
3. Record only aggregate counts: consents, access approvals, attempted quizzes and lesson counts. Do not log IDs, tokens or private account data in CI.
4. Restore the Mini App database into a disposable staging VPS. Confirm table schemas, integrity_check, and aggregate counts. Never overwrite any live database before verification.
5. Test HTTPS, Telegram signed initData, access approvals, lesson reading, original diagrams, quizzes and permissions using a test bot. Compare behavior and response latency with Railway.
6. Schedule a final cutover after approval: briefly stop writes on the old service, make a fresh consistent backup, restore to the new persistent volume, switch webhook setup from OFF to ON ONLY in the newly verified host config, restart it, and verify Telegram Bot API points to the new HTTPS webhook. Update BotFather's Mini App URL/menu when required.
7. If something fails, switch webhook/menu back, but account for any writes that may have occurred on the new server first. Never silently replace a newer DB with an older backup.
8. Keep the Railway service unchanged and available during preflight and for the planned rollback window.

## Hosting choice and the limits of zero cost

An actual, always-running VPS needs a cloud provider account. A free tier is not a guaranteed free server for life.

- Oracle Cloud Always Free offers eligible VMs and storage, subject to signup, inventory availability and idle resource reclamation. Account verification may be a blocker.
- Google Cloud has a limited free e2-micro VM in select US regions, with a small monthly egress allowance. A valid billing account is required and usage beyond the allowance can cost money.
- Cloudflare Workers Free plus D1 can potentially serve 35 students within free quotas, but is NOT a Docker VPS. The current disk-based Python SQLite Store and deployment workflow would need adaptation for D1 and serverless limits; we must test it before making any claims about compatibility.
- Render Free sleeps when idle and loses local SQLite changes on redeploy, so do not move this app's stateful database to an unmodified Render Free web service.

**Next action requiring the owner's explicit action:** obtain a suitable cloud account/VM (or choose a Cloudflare D1 rewrite). Do not switch the Telegram webhook until the chosen replacement has passed the migration checklist.
