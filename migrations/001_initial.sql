-- Tickr multi-guild schema

CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    configured TINYINT(1) NOT NULL DEFAULT 0,
    config JSON NOT NULL,
    ticket_types JSON NOT NULL,
    tickets_global_enabled TINYINT(1) NOT NULL DEFAULT 1,
    created_at INT NOT NULL,
    updated_at INT NOT NULL
);

CREATE TABLE IF NOT EXISTS guild_dashboard (
    guild_id BIGINT PRIMARY KEY,
    notify_url VARCHAR(512) NULL,
    api_secret VARCHAR(128) NULL
);

-- Add guild_id to existing tables (nullable first for migration compatibility)
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS guild_id BIGINT NULL;
ALTER TABLE blacklists ADD COLUMN IF NOT EXISTS guild_id BIGINT NULL;
ALTER TABLE staff_statistics ADD COLUMN IF NOT EXISTS guild_id BIGINT NULL;

CREATE INDEX IF NOT EXISTS idx_tickets_guild_active ON tickets (guild_id, is_active);
CREATE INDEX IF NOT EXISTS idx_tickets_guild_channel ON tickets (guild_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_blacklists_guild_user ON blacklists (guild_id, user_id);

-- Analytics tables (create if missing, add guild_id)
CREATE TABLE IF NOT EXISTS analytics_ticket_messages_daily (
    guild_id BIGINT NOT NULL,
    day DATE NOT NULL,
    channel_id BIGINT NOT NULL,
    staff_messages INT NOT NULL DEFAULT 0,
    owner_messages INT NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, day, channel_id)
);

CREATE TABLE IF NOT EXISTS analytics_command_daily (
    guild_id BIGINT NOT NULL,
    day DATE NOT NULL,
    command_name VARCHAR(128) NOT NULL,
    bot_id BIGINT NOT NULL,
    invocations INT NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, day, command_name, bot_id)
);

CREATE TABLE IF NOT EXISTS total_statistics (
    guild_id BIGINT NOT NULL,
    user_ID BIGINT NOT NULL,
    tickets_closed INT NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_ID)
);
