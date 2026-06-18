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

CREATE TABLE IF NOT EXISTS tickets (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,
    type VARCHAR(128) NOT NULL,
    opened_at INT NOT NULL,
    number INT NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    closed_by_id BIGINT NULL,
    closed_at INT NULL,
    reason TEXT NULL,
    name VARCHAR(512) NULL,
    transcript VARCHAR(1024) NULL,
    privated VARCHAR(32) NULL,
    PRIMARY KEY (channel_id),
    INDEX idx_tickets_guild_active (guild_id, is_active),
    INDEX idx_tickets_guild_channel (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS blacklists (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason TEXT NULL,
    staff_id BIGINT NOT NULL,
    unblacklist_at INT NOT NULL,
    created_at INT NULL,
    PRIMARY KEY (guild_id, user_id),
    INDEX idx_blacklists_guild_user (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS staff_statistics (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    tickets_closed INT NOT NULL DEFAULT 0,
    messages_sent INT NOT NULL DEFAULT 0,
    warnings INT NOT NULL DEFAULT 0,
    mutes INT NOT NULL DEFAULT 0,
    temp_bans INT NOT NULL DEFAULT 0,
    bans INT NOT NULL DEFAULT 0,
    screenshares INT NOT NULL DEFAULT 0,
    manual_bans INT NOT NULL DEFAULT 0,
    blacklists INT NOT NULL DEFAULT 0,
    revives INT NOT NULL DEFAULT 0,
    appeals INT NOT NULL DEFAULT 0,
    threads_locked INT NOT NULL DEFAULT 0,
    strike_team_votes INT NOT NULL DEFAULT 0,
    characters_sent INT NOT NULL DEFAULT 0,
    punishment_requests INT NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- Upgrade path for Minecadia single-guild installs (no-op when column already exists)
ALTER TABLE tickets ADD COLUMN guild_id BIGINT NULL;
ALTER TABLE blacklists ADD COLUMN guild_id BIGINT NULL;
ALTER TABLE staff_statistics ADD COLUMN guild_id BIGINT NULL;

CREATE INDEX idx_tickets_guild_active ON tickets (guild_id, is_active);
CREATE INDEX idx_tickets_guild_channel ON tickets (guild_id, channel_id);
CREATE INDEX idx_blacklists_guild_user ON blacklists (guild_id, user_id);

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
    messages_sent INT NOT NULL DEFAULT 0,
    warnings INT NOT NULL DEFAULT 0,
    mutes INT NOT NULL DEFAULT 0,
    temp_bans INT NOT NULL DEFAULT 0,
    bans INT NOT NULL DEFAULT 0,
    screenshares INT NOT NULL DEFAULT 0,
    manual_bans INT NOT NULL DEFAULT 0,
    blacklists INT NOT NULL DEFAULT 0,
    revives INT NOT NULL DEFAULT 0,
    appeals INT NOT NULL DEFAULT 0,
    threads_locked INT NOT NULL DEFAULT 0,
    strike_team_votes INT NOT NULL DEFAULT 0,
    characters_sent INT NOT NULL DEFAULT 0,
    punishment_requests INT NOT NULL DEFAULT 0,
    updated_at INT NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_ID)
);
