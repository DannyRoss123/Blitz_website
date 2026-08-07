"""Shared CSV schema for the All-Star aggregator.

Batting and pitching share several stat names on Baseball Reference (e.g. both
tables have a "G" column), so batting columns are prefixed ``bat_`` and
pitching columns ``pit_`` to keep one wide row format. Every row has all
columns; the ones for the other stat_type are left blank.
"""

ID_COLUMNS = ["player_id", "team_id", "season_id", "stat_type"]

SUMMARY_COLUMNS = ["is_all_star", "all_star_selections_2024_2026"]

METADATA_COLUMNS = [
    "full_name",
    "birth_date",
    "birth_place",
    "bats",
    "throws",
    "height_inches",
    "height_raw",
    "weight_lbs",
    "debut_date",
    "primary_position",
]

TEAM_COLUMNS = ["team_name", "team_wins", "team_losses", "team_record"]

BATTING_COLUMNS = [
    "bat_G", "bat_PA", "bat_AB", "bat_R", "bat_H", "bat_2B", "bat_3B",
    "bat_HR", "bat_RBI", "bat_SB", "bat_CS", "bat_BB", "bat_SO", "bat_BA",
    "bat_OBP", "bat_SLG", "bat_OPS", "bat_OPS_plus", "bat_TB", "bat_GDP",
    "bat_HBP", "bat_SH", "bat_SF", "bat_IBB",
]

# Maps BR's Standard Batting table `data-stat` attribute -> our column name
# (confirmed against a live team page; see WRITEUP.md).
BATTING_HEADER_MAP = {
    "b_games": "bat_G", "b_pa": "bat_PA", "b_ab": "bat_AB", "b_r": "bat_R",
    "b_h": "bat_H", "b_doubles": "bat_2B", "b_triples": "bat_3B",
    "b_hr": "bat_HR", "b_rbi": "bat_RBI", "b_sb": "bat_SB", "b_cs": "bat_CS",
    "b_bb": "bat_BB", "b_so": "bat_SO", "b_batting_avg": "bat_BA",
    "b_onbase_perc": "bat_OBP", "b_slugging_perc": "bat_SLG",
    "b_onbase_plus_slugging": "bat_OPS",
    "b_onbase_plus_slugging_plus": "bat_OPS_plus", "b_tb": "bat_TB",
    "b_gidp": "bat_GDP", "b_hbp": "bat_HBP", "b_sh": "bat_SH",
    "b_sf": "bat_SF", "b_ibb": "bat_IBB",
}

PITCHING_COLUMNS = [
    "pit_W", "pit_L", "pit_WL_pct", "pit_ERA", "pit_G", "pit_GS", "pit_GF",
    "pit_CG", "pit_SHO", "pit_SV", "pit_IP", "pit_H", "pit_R", "pit_ER",
    "pit_HR", "pit_BB", "pit_IBB", "pit_SO", "pit_HBP", "pit_BK", "pit_WP",
    "pit_BF", "pit_ERA_plus", "pit_WHIP", "pit_H9", "pit_HR9", "pit_BB9",
    "pit_SO9",
]

# Maps BR's Standard Pitching table `data-stat` attribute -> our column name
# (confirmed against a live team page; see WRITEUP.md).
PITCHING_HEADER_MAP = {
    "p_w": "pit_W", "p_l": "pit_L", "p_win_loss_perc": "pit_WL_pct",
    "p_earned_run_avg": "pit_ERA", "p_g": "pit_G", "p_gs": "pit_GS",
    "p_gf": "pit_GF", "p_cg": "pit_CG", "p_sho": "pit_SHO", "p_sv": "pit_SV",
    "p_ip": "pit_IP", "p_h": "pit_H", "p_r": "pit_R", "p_er": "pit_ER",
    "p_hr": "pit_HR", "p_bb": "pit_BB", "p_ibb": "pit_IBB", "p_so": "pit_SO",
    "p_hbp": "pit_HBP", "p_bk": "pit_BK", "p_wp": "pit_WP", "p_bfp": "pit_BF",
    "p_earned_run_avg_plus": "pit_ERA_plus", "p_whip": "pit_WHIP",
    "p_hits_per_nine": "pit_H9", "p_hr_per_nine": "pit_HR9",
    "p_bb_per_nine": "pit_BB9", "p_so_per_nine": "pit_SO9",
}

SHOW_COLUMNS = [
    "is_show_top100", "show_overall_rating", "show_rank",
    "show_potential_grade",
]

PROVENANCE_COLUMNS = ["scraped_at", "source_team_url", "source_player_url"]

ALL_COLUMNS = (
    ID_COLUMNS
    + SUMMARY_COLUMNS
    + METADATA_COLUMNS
    + TEAM_COLUMNS
    + BATTING_COLUMNS
    + PITCHING_COLUMNS
    + SHOW_COLUMNS
    + PROVENANCE_COLUMNS
)


def empty_row():
    return {col: None for col in ALL_COLUMNS}
