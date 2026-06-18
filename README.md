# Tickr

Multi-guild Discord ticket bot (generalized from MinecadiaTickets).

## Features

- Per-guild configuration stored in MySQL
- `/setup` wizard for new servers
- Full ticket lifecycle: open, close, add, remove, rename, move, private, management
- Blacklist, ticket logs (Components V2), active tickets, oldest, ticket count
- In-Discord `/manage-tickets` editor
- Optional dashboard HTTP API and analytics

## Requirements

- Python 3.11+
- MySQL 8+
- Discord bot with `SERVER MEMBERS INTENT` and `MESSAGE CONTENT INTENT`

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with DISCORD_TOKEN and DB credentials
python scripts/migrate.py
python main.py
```

## Adding Tickr to a server

1. Invite the bot with Administrator (or Manage Channels + Manage Roles).
2. Run `/setup` in the server (Administrator required).
3. Run `/send-tickets` in the panel channel to post ticket menus.
4. Customize types with `/manage-tickets`.

## Importing Minecadia config

```bash
python scripts/import_minecadia_guild.py \
  --guild-id YOUR_GUILD_ID \
  --config /path/to/MinecadiaTickets/assets/config.json \
  --tickets /path/to/MinecadiaTickets/assets/tickets.json
```

## Dashboard HTTP API

When `TICKETS_BOT_API_SECRET` is set, listens on `127.0.0.1:8788`:

- `POST /close-ticket` — body: `{ guild_id?, channel_id, closed_by_id, reason }`
- `POST /ticket-command` — proxy ticket commands
- `GET /health`

Header: `X-Tickets-Key: <secret>`

## Development

Set `DISCORD_GUILD_ID` for faster command sync to your test guild alongside global sync.
