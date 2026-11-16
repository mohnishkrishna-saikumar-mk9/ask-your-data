-- IPL schema: matches + ball-by-ball deliveries, plus two helper views.
-- Re-runnable: drops and recreates everything (FR-4 idempotent loaders).
CREATE SCHEMA IF NOT EXISTS ipl;
DROP VIEW IF EXISTS ipl.batting_innings, ipl.bowling_innings;
DROP TABLE IF EXISTS ipl.deliveries, ipl.matches CASCADE;

CREATE TABLE ipl.matches (
    match_id        INTEGER PRIMARY KEY,
    season          SMALLINT NOT NULL,
    match_date      DATE NOT NULL,
    city            TEXT,
    venue           TEXT,
    match_type      TEXT,
    team1           TEXT NOT NULL,
    team2           TEXT NOT NULL,
    toss_winner     TEXT,
    toss_decision   TEXT,
    winner          TEXT,
    result          TEXT,
    result_margin   NUMERIC,
    target_runs     NUMERIC,
    target_overs    NUMERIC,
    super_over      BOOLEAN,
    method          TEXT,
    player_of_match TEXT
);

CREATE TABLE ipl.deliveries (
    id               BIGSERIAL PRIMARY KEY,
    match_id         INTEGER NOT NULL REFERENCES ipl.matches(match_id),
    inning           SMALLINT NOT NULL,
    over_no          SMALLINT NOT NULL CHECK (over_no BETWEEN 0 AND 19),
    ball             SMALLINT NOT NULL,
    phase            TEXT NOT NULL CHECK (phase IN ('powerplay', 'middle', 'death')),
    batting_team     TEXT NOT NULL,
    bowling_team     TEXT NOT NULL,
    batter           TEXT NOT NULL,
    bowler           TEXT NOT NULL,
    non_striker      TEXT,
    batter_runs      SMALLINT NOT NULL,
    extra_runs       SMALLINT NOT NULL,
    total_runs       SMALLINT NOT NULL,
    extras_type      TEXT,
    is_wicket        BOOLEAN NOT NULL,
    player_dismissed TEXT,
    dismissal_kind   TEXT,
    fielder          TEXT
);

-- Views: one row per batter per match / bowler per match. These make LLM questions far easier.
CREATE VIEW ipl.batting_innings AS
SELECT d.match_id,
       m.season,
       d.batter,
       d.batting_team                                                   AS team,
       SUM(d.batter_runs)                                               AS runs,
       COUNT(*) FILTER (WHERE d.extras_type IS DISTINCT FROM 'wides')   AS balls_faced,
       COUNT(*) FILTER (WHERE d.batter_runs = 4)                        AS fours,
       COUNT(*) FILTER (WHERE d.batter_runs = 6)                        AS sixes,
       COALESCE(BOOL_OR(d.player_dismissed = d.batter), FALSE)          AS is_out
FROM ipl.deliveries d
JOIN ipl.matches m ON m.match_id = d.match_id
WHERE d.inning <= 2
GROUP BY d.match_id, m.season, d.batter, d.batting_team;

CREATE VIEW ipl.bowling_innings AS
SELECT d.match_id,
       m.season,
       d.bowler,
       d.bowling_team AS team,
       COUNT(*) FILTER (WHERE d.extras_type IS NULL
                           OR d.extras_type NOT IN ('wides', 'noballs'))           AS balls_bowled,
       SUM(d.total_runs) - SUM(CASE WHEN d.extras_type IN ('byes', 'legbyes')
                                    THEN d.extra_runs ELSE 0 END)                  AS runs_conceded,
       COUNT(*) FILTER (WHERE d.is_wicket AND d.dismissal_kind NOT IN
                        ('run out', 'retired hurt', 'retired out', 'obstructing the field'))
                                                                                   AS wickets
FROM ipl.deliveries d
JOIN ipl.matches m ON m.match_id = d.match_id
WHERE d.inning <= 2
GROUP BY d.match_id, m.season, d.bowler, d.bowling_team;

CREATE INDEX idx_deliveries_match  ON ipl.deliveries (match_id);
CREATE INDEX idx_deliveries_batter ON ipl.deliveries (batter);
CREATE INDEX idx_deliveries_bowler ON ipl.deliveries (bowler);
CREATE INDEX idx_matches_season    ON ipl.matches (season);

-- Data dictionary. The LLM prompt is built from these comments, so keep them precise.
COMMENT ON TABLE ipl.matches IS 'One row per IPL match (2008 onwards). Team names are normalised to current franchise names.';
COMMENT ON COLUMN ipl.matches.match_id IS 'Unique match id (primary key)';
COMMENT ON COLUMN ipl.matches.season IS 'IPL season as a year, e.g. 2023 (taken from the match date)';
COMMENT ON COLUMN ipl.matches.match_date IS 'Date the match was played';
COMMENT ON COLUMN ipl.matches.city IS 'Host city (may be NULL in old data)';
COMMENT ON COLUMN ipl.matches.venue IS 'Stadium name, normalised so each ground has one spelling';
COMMENT ON COLUMN ipl.matches.match_type IS 'League, Qualifier 1, Eliminator, Qualifier 2, Final, etc. The season champion is the winner of the Final';
COMMENT ON COLUMN ipl.matches.team1 IS 'First listed team';
COMMENT ON COLUMN ipl.matches.team2 IS 'Second listed team';
COMMENT ON COLUMN ipl.matches.toss_winner IS 'Team that won the toss';
COMMENT ON COLUMN ipl.matches.toss_decision IS 'bat or field - what the toss winner chose';
COMMENT ON COLUMN ipl.matches.winner IS 'Winning team; NULL for no result';
COMMENT ON COLUMN ipl.matches.result IS 'runs (team batting first won), wickets (chasing team won), tie, or no result';
COMMENT ON COLUMN ipl.matches.result_margin IS 'Winning margin in runs or wickets depending on result';
COMMENT ON COLUMN ipl.matches.target_runs IS 'Target set for the chasing team';
COMMENT ON COLUMN ipl.matches.target_overs IS 'Overs available to the chasing team (reduced in rain-affected games)';
COMMENT ON COLUMN ipl.matches.super_over IS 'TRUE if the match was decided by a super over';
COMMENT ON COLUMN ipl.matches.method IS 'D/L if Duckworth-Lewis was applied, else NULL';
COMMENT ON COLUMN ipl.matches.player_of_match IS 'Player of the match award winner';

COMMENT ON TABLE ipl.deliveries IS 'One row per ball bowled. inning 1 and 2 are the normal innings; 3+ are super overs';
COMMENT ON COLUMN ipl.deliveries.id IS 'Surrogate primary key';
COMMENT ON COLUMN ipl.deliveries.match_id IS 'Foreign key to ipl.matches.match_id';
COMMENT ON COLUMN ipl.deliveries.inning IS '1 = first innings, 2 = chase, 3+ = super over';
COMMENT ON COLUMN ipl.deliveries.over_no IS 'Over number, 0-based (0 = first over, 19 = last)';
COMMENT ON COLUMN ipl.deliveries.ball IS 'Ball number within the over (extras can make it exceed 6)';
COMMENT ON COLUMN ipl.deliveries.phase IS 'powerplay (overs 0-5), middle (6-14) or death (15-19)';
COMMENT ON COLUMN ipl.deliveries.batting_team IS 'Team batting on this ball';
COMMENT ON COLUMN ipl.deliveries.bowling_team IS 'Team bowling on this ball';
COMMENT ON COLUMN ipl.deliveries.batter IS 'Batter on strike';
COMMENT ON COLUMN ipl.deliveries.bowler IS 'Bowler';
COMMENT ON COLUMN ipl.deliveries.non_striker IS 'Batter at the non-striker end';
COMMENT ON COLUMN ipl.deliveries.batter_runs IS 'Runs scored off the bat (4 = four, 6 = six)';
COMMENT ON COLUMN ipl.deliveries.extra_runs IS 'Extra runs on this ball';
COMMENT ON COLUMN ipl.deliveries.total_runs IS 'batter_runs + extra_runs';
COMMENT ON COLUMN ipl.deliveries.extras_type IS 'wides, noballs, byes, legbyes, penalty, or NULL for a normal ball';
COMMENT ON COLUMN ipl.deliveries.is_wicket IS 'TRUE if a wicket fell on this ball (includes run outs)';
COMMENT ON COLUMN ipl.deliveries.player_dismissed IS 'Batter who got out, if any';
COMMENT ON COLUMN ipl.deliveries.dismissal_kind IS 'caught, bowled, lbw, run out, stumped, etc.';
COMMENT ON COLUMN ipl.deliveries.fielder IS 'Fielder involved in the dismissal, if any';

COMMENT ON VIEW ipl.batting_innings IS 'One row per batter per match (super overs excluded). Prefer this for batting questions';
COMMENT ON COLUMN ipl.batting_innings.match_id IS 'Match id';
COMMENT ON COLUMN ipl.batting_innings.season IS 'Season year';
COMMENT ON COLUMN ipl.batting_innings.batter IS 'Batter name';
COMMENT ON COLUMN ipl.batting_innings.team IS 'Batter''s team';
COMMENT ON COLUMN ipl.batting_innings.runs IS 'Runs off the bat in this innings';
COMMENT ON COLUMN ipl.batting_innings.balls_faced IS 'Balls faced (wides excluded)';
COMMENT ON COLUMN ipl.batting_innings.fours IS 'Number of fours';
COMMENT ON COLUMN ipl.batting_innings.sixes IS 'Number of sixes';
COMMENT ON COLUMN ipl.batting_innings.is_out IS 'TRUE if the batter was dismissed';

COMMENT ON VIEW ipl.bowling_innings IS 'One row per bowler per match (super overs excluded). Prefer this for bowling questions';
COMMENT ON COLUMN ipl.bowling_innings.match_id IS 'Match id';
COMMENT ON COLUMN ipl.bowling_innings.season IS 'Season year';
COMMENT ON COLUMN ipl.bowling_innings.bowler IS 'Bowler name';
COMMENT ON COLUMN ipl.bowling_innings.team IS 'Bowler''s team';
COMMENT ON COLUMN ipl.bowling_innings.balls_bowled IS 'Legal balls bowled (wides and no-balls excluded)';
COMMENT ON COLUMN ipl.bowling_innings.runs_conceded IS 'Runs conceded (byes and leg-byes not charged to bowler)';
COMMENT ON COLUMN ipl.bowling_innings.wickets IS 'Wickets credited to the bowler (run outs etc. excluded)';
