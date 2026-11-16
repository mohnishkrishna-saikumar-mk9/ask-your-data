-- Indian startup funding schema: one row per funding round + a bridge table of investors.
-- Re-runnable: drops and recreates everything.
CREATE SCHEMA IF NOT EXISTS startups;
DROP TABLE IF EXISTS startups.round_investors, startups.funding_rounds CASCADE;

CREATE TABLE startups.funding_rounds (
    round_id          INTEGER PRIMARY KEY,
    funding_date      DATE,
    startup_name      TEXT NOT NULL,
    industry_vertical TEXT,
    sub_vertical      TEXT,
    city              TEXT,
    investment_type   TEXT,
    amount_usd        NUMERIC(16, 2),
    remarks           TEXT
);

CREATE TABLE startups.round_investors (
    round_id      INTEGER NOT NULL REFERENCES startups.funding_rounds(round_id),
    investor_name TEXT NOT NULL,
    PRIMARY KEY (round_id, investor_name)
);

CREATE INDEX idx_rounds_date     ON startups.funding_rounds (funding_date);
CREATE INDEX idx_rounds_startup  ON startups.funding_rounds (startup_name);
CREATE INDEX idx_investors_name  ON startups.round_investors (investor_name);

COMMENT ON TABLE startups.funding_rounds IS 'One row per funding round raised by an Indian startup (2015-2020)';
COMMENT ON COLUMN startups.funding_rounds.round_id IS 'Round id (the Sr No of the raw file, primary key)';
COMMENT ON COLUMN startups.funding_rounds.funding_date IS 'Date of the round; year = EXTRACT(YEAR FROM funding_date). NULL if the raw date was unreadable';
COMMENT ON COLUMN startups.funding_rounds.startup_name IS 'Startup name, with common variants merged (e.g. Ola, OYO, Paytm, Flipkart)';
COMMENT ON COLUMN startups.funding_rounds.industry_vertical IS 'Industry, e.g. Consumer Internet, Technology, eCommerce, FinTech';
COMMENT ON COLUMN startups.funding_rounds.sub_vertical IS 'More specific business description';
COMMENT ON COLUMN startups.funding_rounds.city IS 'Head-office city, normalised (Bengaluru, Delhi, Gurugram, Mumbai ...)';
COMMENT ON COLUMN startups.funding_rounds.investment_type IS 'Round type: Seed / Angel, Private Equity, Series A, Series B, Debt Funding, ...';
COMMENT ON COLUMN startups.funding_rounds.amount_usd IS 'Amount raised in US dollars; NULL when undisclosed. Total funding = SUM(amount_usd)';
COMMENT ON COLUMN startups.funding_rounds.remarks IS 'Free-text remarks from the source, often empty';

COMMENT ON TABLE startups.round_investors IS 'Bridge table: one row per investor taking part in a round. Investor activity = COUNT(DISTINCT round_id)';
COMMENT ON COLUMN startups.round_investors.round_id IS 'Foreign key to startups.funding_rounds.round_id';
COMMENT ON COLUMN startups.round_investors.investor_name IS 'Investor name (individual or firm)';
