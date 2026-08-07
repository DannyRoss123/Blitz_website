-- Optional extra-credit schema (per the assignment FAQ: "CSV is required;
-- Postgres is optional extra credit"). Mirrors the CSV's grain and columns
-- 1:1 -- see src/models.py for the authoritative column list.
--
-- pit_IP is stored as TEXT, not NUMERIC: Baseball-Reference displays innings
-- pitched as thirds (63.1 = 63 and 1/3 innings, 63.2 = 63 and 2/3), which is
-- not a real decimal value -- storing it numerically would silently imply
-- the wrong arithmetic meaning.

CREATE TABLE IF NOT EXISTS all_stars (
    player_id                       TEXT NOT NULL,
    team_id                         TEXT NOT NULL,
    season_id                       INTEGER NOT NULL,
    stat_type                       TEXT NOT NULL CHECK (stat_type IN ('batting', 'pitching')),

    is_all_star                     BOOLEAN NOT NULL DEFAULT TRUE,
    all_star_selections_2024_2026   INTEGER,

    full_name                       TEXT,
    birth_date                      DATE,
    birth_place                     TEXT,
    bats                            TEXT,
    throws                          TEXT,
    height_inches                   INTEGER,
    height_raw                      TEXT,
    weight_lbs                      INTEGER,
    debut_date                      DATE,
    primary_position                TEXT,

    team_name                       TEXT,
    team_wins                       INTEGER,
    team_losses                     INTEGER,
    team_record                     TEXT,

    bat_g                           INTEGER,
    bat_pa                          INTEGER,
    bat_ab                          INTEGER,
    bat_r                           INTEGER,
    bat_h                           INTEGER,
    bat_2b                          INTEGER,
    bat_3b                          INTEGER,
    bat_hr                          INTEGER,
    bat_rbi                         INTEGER,
    bat_sb                          INTEGER,
    bat_cs                          INTEGER,
    bat_bb                          INTEGER,
    bat_so                          INTEGER,
    bat_ba                          NUMERIC(4,3),
    bat_obp                         NUMERIC(4,3),
    bat_slg                         NUMERIC(4,3),
    bat_ops                         NUMERIC(4,3),
    bat_ops_plus                    INTEGER,
    bat_tb                          INTEGER,
    bat_gdp                         INTEGER,
    bat_hbp                         INTEGER,
    bat_sh                          INTEGER,
    bat_sf                          INTEGER,
    bat_ibb                         INTEGER,

    pit_w                           INTEGER,
    pit_l                           INTEGER,
    pit_wl_pct                      NUMERIC(4,3),
    pit_era                         NUMERIC(5,2),
    pit_g                           INTEGER,
    pit_gs                          INTEGER,
    pit_gf                          INTEGER,
    pit_cg                          INTEGER,
    pit_sho                         INTEGER,
    pit_sv                          INTEGER,
    pit_ip                          TEXT,
    pit_h                           INTEGER,
    pit_r                           INTEGER,
    pit_er                          INTEGER,
    pit_hr                          INTEGER,
    pit_bb                          INTEGER,
    pit_ibb                         INTEGER,
    pit_so                          INTEGER,
    pit_hbp                         INTEGER,
    pit_bk                          INTEGER,
    pit_wp                          INTEGER,
    pit_bf                          INTEGER,
    pit_era_plus                    INTEGER,
    pit_whip                        NUMERIC(5,3),
    pit_h9                          NUMERIC(4,1),
    pit_hr9                         NUMERIC(4,1),
    pit_bb9                         NUMERIC(4,1),
    pit_so9                         NUMERIC(4,1),

    is_show_top100                  BOOLEAN NOT NULL DEFAULT FALSE,
    show_overall_rating             INTEGER,
    show_rank                       INTEGER,
    show_potential_grade            TEXT,

    scraped_at                      TIMESTAMPTZ,
    source_team_url                 TEXT,
    source_player_url               TEXT,

    PRIMARY KEY (player_id, season_id, stat_type, team_id)
);

CREATE INDEX IF NOT EXISTS idx_all_stars_player ON all_stars (player_id);
CREATE INDEX IF NOT EXISTS idx_all_stars_season ON all_stars (season_id);
CREATE INDEX IF NOT EXISTS idx_all_stars_show_top100 ON all_stars (is_show_top100) WHERE is_show_top100;
