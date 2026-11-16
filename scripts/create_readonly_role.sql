-- Creates the SELECT-only role the app connects as (defence in depth, SPEC 9.3).
-- Run via:  python -m scripts.create_readonly_role   (reads READONLY_PASSWORD from .env)
-- The password is passed in as the session setting ayd.pw, so it never lives in this file.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ayd_reader') THEN
        CREATE ROLE ayd_reader LOGIN;
    END IF;
    EXECUTE format('ALTER ROLE ayd_reader WITH LOGIN PASSWORD %L', current_setting('ayd.pw'));
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO ayd_reader', current_database());
END
$$;

-- Safety settings applied to every session of this role.
ALTER ROLE ayd_reader SET default_transaction_read_only = on;
ALTER ROLE ayd_reader SET statement_timeout = '10s';

-- Read access to the 8 dataset schemas only (nothing in public). Keep in sync with DATASETS.
REVOKE ALL ON SCHEMA public FROM ayd_reader;
GRANT USAGE ON SCHEMA placements, netflix, startups, air_quality, ecommerce, ipl, olist, chinook
    TO ayd_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA placements, netflix, startups, air_quality, ecommerce, ipl, olist,
    chinook TO ayd_reader;

-- Loaders drop and recreate tables; default privileges keep the grants for new tables.
ALTER DEFAULT PRIVILEGES IN SCHEMA placements, netflix, startups, air_quality, ecommerce, ipl, olist,
    chinook GRANT SELECT ON TABLES TO ayd_reader;
