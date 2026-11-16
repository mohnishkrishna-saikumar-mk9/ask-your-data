-- Netflix schema: one row per title + four bridge tables built from comma-separated lists.
-- Re-runnable: drops and recreates everything.
CREATE SCHEMA IF NOT EXISTS netflix;
DROP TABLE IF EXISTS netflix.title_directors, netflix.title_cast, netflix.title_countries,
                     netflix.title_genres, netflix.titles CASCADE;

CREATE TABLE netflix.titles (
    show_id          TEXT PRIMARY KEY,
    type             TEXT NOT NULL CHECK (type IN ('Movie', 'TV Show')),
    title            TEXT NOT NULL,
    date_added       DATE,
    release_year     SMALLINT NOT NULL,
    rating           TEXT,
    duration_minutes SMALLINT,
    seasons          SMALLINT,
    description      TEXT
);

-- Bridge tables: a title can have many directors / actors / countries / genres and vice versa.
CREATE TABLE netflix.title_directors (
    show_id  TEXT NOT NULL REFERENCES netflix.titles(show_id),
    director TEXT NOT NULL,
    PRIMARY KEY (show_id, director)
);
CREATE TABLE netflix.title_cast (
    show_id TEXT NOT NULL REFERENCES netflix.titles(show_id),
    actor   TEXT NOT NULL,
    PRIMARY KEY (show_id, actor)
);
CREATE TABLE netflix.title_countries (
    show_id TEXT NOT NULL REFERENCES netflix.titles(show_id),
    country TEXT NOT NULL,
    PRIMARY KEY (show_id, country)
);
CREATE TABLE netflix.title_genres (
    show_id TEXT NOT NULL REFERENCES netflix.titles(show_id),
    genre   TEXT NOT NULL,
    PRIMARY KEY (show_id, genre)
);

CREATE INDEX idx_titles_type       ON netflix.titles (type);
CREATE INDEX idx_titles_date_added ON netflix.titles (date_added);
CREATE INDEX idx_directors_name    ON netflix.title_directors (director);
CREATE INDEX idx_cast_actor        ON netflix.title_cast (actor);
CREATE INDEX idx_countries_country ON netflix.title_countries (country);
CREATE INDEX idx_genres_genre      ON netflix.title_genres (genre);

COMMENT ON TABLE netflix.titles IS 'One row per movie or TV show on Netflix (catalogue up to 2021)';
COMMENT ON COLUMN netflix.titles.show_id IS 'Netflix show id, e.g. s1 (primary key)';
COMMENT ON COLUMN netflix.titles.type IS 'Movie or TV Show';
COMMENT ON COLUMN netflix.titles.title IS 'Title name';
COMMENT ON COLUMN netflix.titles.date_added IS 'Date the title was added to Netflix; "added in year X" = EXTRACT(YEAR FROM date_added)';
COMMENT ON COLUMN netflix.titles.release_year IS 'Year the title was originally released';
COMMENT ON COLUMN netflix.titles.rating IS 'Age rating, e.g. TV-MA, TV-14, PG-13, R';
COMMENT ON COLUMN netflix.titles.duration_minutes IS 'Running time in minutes (movies only; NULL for TV shows)';
COMMENT ON COLUMN netflix.titles.seasons IS 'Number of seasons (TV shows only; NULL for movies)';
COMMENT ON COLUMN netflix.titles.description IS 'Short plot summary';

COMMENT ON TABLE netflix.title_directors IS 'Bridge table: which director(s) directed each title';
COMMENT ON COLUMN netflix.title_directors.show_id IS 'Foreign key to netflix.titles.show_id';
COMMENT ON COLUMN netflix.title_directors.director IS 'Director name';
COMMENT ON TABLE netflix.title_cast IS 'Bridge table: actors appearing in each title';
COMMENT ON COLUMN netflix.title_cast.show_id IS 'Foreign key to netflix.titles.show_id';
COMMENT ON COLUMN netflix.title_cast.actor IS 'Actor name';
COMMENT ON TABLE netflix.title_countries IS 'Bridge table: production countries of each title. Indian title = has country ''India''';
COMMENT ON COLUMN netflix.title_countries.show_id IS 'Foreign key to netflix.titles.show_id';
COMMENT ON COLUMN netflix.title_countries.country IS 'Country name, e.g. India, United States';
COMMENT ON TABLE netflix.title_genres IS 'Bridge table: genres / categories of each title (from listed_in)';
COMMENT ON COLUMN netflix.title_genres.show_id IS 'Foreign key to netflix.titles.show_id';
COMMENT ON COLUMN netflix.title_genres.genre IS 'Genre, e.g. Dramas, International Movies, Comedies';
