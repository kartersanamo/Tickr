# Tickr Web Dashboard Deployment

Host **tickr.kartersanamo.com** on the home server using Docker and Cloudflare tunnel (same pattern as jm.kartersanamo.com and kimsdiner.kartersanamo.com).

## Prerequisites

- Tickr bot running with MySQL configured
- Bot `.env` includes `TICKETS_BOT_API_SECRET` (enables localhost control API on port 8788)
- Discord application with OAuth2 and bot scopes

## 1. Discord Developer Portal

1. Open [Discord Developer Portal](https://discord.com/developers/applications) → your Tickr application.
2. **OAuth2 → Redirects** — add:
   ```
   https://tickr.kartersanamo.com/api/auth/callback/discord
   ```
   For local dev also add: `http://localhost:3000/api/auth/callback/discord`
3. **OAuth2 → URL Generator** — scopes: `identify`, `guilds`. Copy Client ID and Client Secret.
4. **Bot → Invite URL** — permissions: Manage Channels, Manage Roles, View Channels, Send Messages, Embed Links, Read Message History, Use Slash Commands. Copy invite link.

## 2. Environment file

```bash
cp .env.dashboard.example .env.dashboard
# Edit .env.dashboard — set AUTH_SECRET, DASHBOARD_INTERNAL_SECRET, Discord IDs, DB creds, bot token, TICKETS_BOT_API_SECRET
openssl rand -base64 32   # use for AUTH_SECRET and DASHBOARD_INTERNAL_SECRET
```

Ensure `TICKETS_BOT_API_SECRET` matches the bot's `.env`.

## 3. Build and run

```bash
chmod +x web/deploy.sh
./web/deploy.sh
```

Services:
- **tickr-web** — port **8005** (public via Cloudflare)
- **tickr-api** — port **8790** (internal; web container proxies authenticated requests)

## 4. Cloudflare tunnel

Add to `/etc/cloudflared/config.yml` ingress:

```yaml
  - hostname: tickr.kartersanamo.com
    service: http://localhost:8005
```

Provision DNS (once):

```bash
cloudflared tunnel route dns homeserver tickr.kartersanamo.com
sudo systemctl restart cloudflared
```

## 5. Verify

- `https://tickr.kartersanamo.com` — landing page
- Sign in with Discord → guild picker
- Open a server → config, ticket types, live tickets

Health checks:
- `curl http://localhost:8790/health`
- Bot API: `curl -H "X-Tickets-Key: $SECRET" http://127.0.0.1:8788/health`

## Local development

Terminal 1 — API (from repo root, with venv + .env):

```bash
source .venv/bin/activate
export $(grep -v '^#' .env.dashboard | xargs)
uvicorn api.main:app --reload --port 8790
```

Terminal 2 — Web:

```bash
cd web
npm install
cp ../.env.dashboard .env.local
npm run dev
```

Open http://localhost:3000

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No servers in picker | Bot must be in guild; user needs Administrator or Manage Server (or configured admin role) |
| Live ticket actions fail | Confirm `TICKETS_BOT_API_SECRET` and bot is running; API container must reach `host.docker.internal:8788` |
| OAuth redirect error | Redirect URI must exactly match Discord portal entry |
| Config changes not in Discord | Wait up to 60s for bot config cache, or restart bot |
