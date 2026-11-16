-- Chinook music store - data dictionary + extra index.
-- The tables themselves come from data/raw/chinook/Chinook_PostgreSql.sql (v1.4.5, MIT licence),
-- run by scripts/load_chinook.py inside schema `chinook`. That script has no comments, so we add them.

CREATE INDEX IF NOT EXISTS invoice_invoice_date_idx ON chinook.invoice (invoice_date);

COMMENT ON TABLE chinook.artist IS 'Recording artists and bands';
COMMENT ON COLUMN chinook.artist.artist_id IS 'Artist key (primary key)';
COMMENT ON COLUMN chinook.artist.name IS 'Artist or band name';

COMMENT ON TABLE chinook.album IS 'Albums; each album belongs to one artist';
COMMENT ON COLUMN chinook.album.album_id IS 'Album key (primary key)';
COMMENT ON COLUMN chinook.album.title IS 'Album title';
COMMENT ON COLUMN chinook.album.artist_id IS 'Foreign key to chinook.artist.artist_id';

COMMENT ON TABLE chinook.genre IS 'Music genres, e.g. Rock, Jazz, Metal';
COMMENT ON COLUMN chinook.genre.genre_id IS 'Genre key (primary key)';
COMMENT ON COLUMN chinook.genre.name IS 'Genre name';

COMMENT ON TABLE chinook.media_type IS 'File formats, e.g. MPEG audio file, AAC audio file';
COMMENT ON COLUMN chinook.media_type.media_type_id IS 'Media type key (primary key)';
COMMENT ON COLUMN chinook.media_type.name IS 'Media type name';

COMMENT ON TABLE chinook.track IS 'Songs / videos for sale. Track length in minutes = milliseconds / 60000.0';
COMMENT ON COLUMN chinook.track.track_id IS 'Track key (primary key)';
COMMENT ON COLUMN chinook.track.name IS 'Track name';
COMMENT ON COLUMN chinook.track.album_id IS 'Foreign key to chinook.album.album_id';
COMMENT ON COLUMN chinook.track.media_type_id IS 'Foreign key to chinook.media_type.media_type_id';
COMMENT ON COLUMN chinook.track.genre_id IS 'Foreign key to chinook.genre.genre_id';
COMMENT ON COLUMN chinook.track.composer IS 'Composer(s), may be NULL';
COMMENT ON COLUMN chinook.track.milliseconds IS 'Track length in milliseconds';
COMMENT ON COLUMN chinook.track.bytes IS 'File size in bytes';
COMMENT ON COLUMN chinook.track.unit_price IS 'List price in USD (0.99 or 1.99)';

COMMENT ON TABLE chinook.playlist IS 'Playlists';
COMMENT ON COLUMN chinook.playlist.playlist_id IS 'Playlist key (primary key)';
COMMENT ON COLUMN chinook.playlist.name IS 'Playlist name';

COMMENT ON TABLE chinook.playlist_track IS 'Bridge table: which tracks are on which playlist';
COMMENT ON COLUMN chinook.playlist_track.playlist_id IS 'Foreign key to chinook.playlist.playlist_id';
COMMENT ON COLUMN chinook.playlist_track.track_id IS 'Foreign key to chinook.track.track_id';

COMMENT ON TABLE chinook.employee IS 'Store employees. reports_to points to the manager (self-join / recursive CTE for the hierarchy)';
COMMENT ON COLUMN chinook.employee.employee_id IS 'Employee key (primary key)';
COMMENT ON COLUMN chinook.employee.last_name IS 'Last name';
COMMENT ON COLUMN chinook.employee.first_name IS 'First name';
COMMENT ON COLUMN chinook.employee.title IS 'Job title, e.g. Sales Support Agent, General Manager';
COMMENT ON COLUMN chinook.employee.reports_to IS 'employee_id of this person''s manager; NULL for the top manager';
COMMENT ON COLUMN chinook.employee.birth_date IS 'Date of birth';
COMMENT ON COLUMN chinook.employee.hire_date IS 'Date hired';
COMMENT ON COLUMN chinook.employee.address IS 'Street address';
COMMENT ON COLUMN chinook.employee.city IS 'City';
COMMENT ON COLUMN chinook.employee.state IS 'State / province';
COMMENT ON COLUMN chinook.employee.country IS 'Country';
COMMENT ON COLUMN chinook.employee.postal_code IS 'Postal code';
COMMENT ON COLUMN chinook.employee.phone IS 'Phone number';
COMMENT ON COLUMN chinook.employee.fax IS 'Fax number';
COMMENT ON COLUMN chinook.employee.email IS 'Email address';

COMMENT ON TABLE chinook.customer IS 'Customers. Each customer has one sales support rep (support_rep_id -> employee)';
COMMENT ON COLUMN chinook.customer.customer_id IS 'Customer key (primary key)';
COMMENT ON COLUMN chinook.customer.first_name IS 'First name';
COMMENT ON COLUMN chinook.customer.last_name IS 'Last name';
COMMENT ON COLUMN chinook.customer.company IS 'Company name, often NULL';
COMMENT ON COLUMN chinook.customer.address IS 'Street address';
COMMENT ON COLUMN chinook.customer.city IS 'City';
COMMENT ON COLUMN chinook.customer.state IS 'State / province, often NULL';
COMMENT ON COLUMN chinook.customer.country IS 'Country, e.g. USA, Canada, Brazil';
COMMENT ON COLUMN chinook.customer.postal_code IS 'Postal code';
COMMENT ON COLUMN chinook.customer.phone IS 'Phone number';
COMMENT ON COLUMN chinook.customer.fax IS 'Fax number';
COMMENT ON COLUMN chinook.customer.email IS 'Email address';
COMMENT ON COLUMN chinook.customer.support_rep_id IS 'Foreign key to chinook.employee.employee_id (the sales rep)';

COMMENT ON TABLE chinook.invoice IS 'One row per purchase (2021-2025). Revenue = SUM(total) per invoice, or SUM(invoice_line.unit_price * quantity)';
COMMENT ON COLUMN chinook.invoice.invoice_id IS 'Invoice key (primary key)';
COMMENT ON COLUMN chinook.invoice.customer_id IS 'Foreign key to chinook.customer.customer_id';
COMMENT ON COLUMN chinook.invoice.invoice_date IS 'Purchase date; month = date_trunc(''month'', invoice_date)';
COMMENT ON COLUMN chinook.invoice.billing_address IS 'Billing street address';
COMMENT ON COLUMN chinook.invoice.billing_city IS 'Billing city';
COMMENT ON COLUMN chinook.invoice.billing_state IS 'Billing state / province';
COMMENT ON COLUMN chinook.invoice.billing_country IS 'Billing country';
COMMENT ON COLUMN chinook.invoice.billing_postal_code IS 'Billing postal code';
COMMENT ON COLUMN chinook.invoice.total IS 'Invoice total in USD';

COMMENT ON TABLE chinook.invoice_line IS 'One row per track bought on an invoice';
COMMENT ON COLUMN chinook.invoice_line.invoice_line_id IS 'Invoice line key (primary key)';
COMMENT ON COLUMN chinook.invoice_line.invoice_id IS 'Foreign key to chinook.invoice.invoice_id';
COMMENT ON COLUMN chinook.invoice_line.track_id IS 'Foreign key to chinook.track.track_id';
COMMENT ON COLUMN chinook.invoice_line.unit_price IS 'Price paid per unit in USD';
COMMENT ON COLUMN chinook.invoice_line.quantity IS 'Units bought (always 1 in this data)';
