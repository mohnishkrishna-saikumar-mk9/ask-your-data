-- Olist Brazilian marketplace (2016-2018): 8 tables - the multi-join stress test.
-- Re-runnable: drops and recreates everything.
CREATE SCHEMA IF NOT EXISTS olist;
DROP TABLE IF EXISTS olist.order_items, olist.payments, olist.reviews, olist.orders,
                     olist.customers, olist.products, olist.sellers, olist.zip_locations CASCADE;

CREATE TABLE olist.customers (
    customer_id        TEXT PRIMARY KEY,
    customer_unique_id TEXT NOT NULL,
    zip_code_prefix    TEXT NOT NULL,
    city               TEXT NOT NULL,
    state              CHAR(2) NOT NULL
);

CREATE TABLE olist.sellers (
    seller_id       TEXT PRIMARY KEY,
    zip_code_prefix TEXT NOT NULL,
    city            TEXT NOT NULL,
    state           CHAR(2) NOT NULL
);

CREATE TABLE olist.products (
    product_id          TEXT PRIMARY KEY,
    category            TEXT,
    category_english    TEXT,
    name_length         SMALLINT,
    description_length  SMALLINT,
    photos_qty          SMALLINT,
    weight_g            INTEGER,
    length_cm           SMALLINT,
    height_cm           SMALLINT,
    width_cm            SMALLINT
);

CREATE TABLE olist.orders (
    order_id                      TEXT PRIMARY KEY,
    customer_id                   TEXT NOT NULL REFERENCES olist.customers(customer_id),
    order_status                  TEXT NOT NULL,
    order_purchase_timestamp      TIMESTAMP NOT NULL,
    order_approved_at             TIMESTAMP,
    order_delivered_carrier_date  TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP NOT NULL
);

CREATE TABLE olist.order_items (
    order_id            TEXT NOT NULL REFERENCES olist.orders(order_id),
    order_item_id       SMALLINT NOT NULL,
    product_id          TEXT NOT NULL REFERENCES olist.products(product_id),
    seller_id           TEXT NOT NULL REFERENCES olist.sellers(seller_id),
    shipping_limit_date TIMESTAMP NOT NULL,
    price               NUMERIC(10, 2) NOT NULL,
    freight_value       NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE olist.payments (
    order_id             TEXT NOT NULL REFERENCES olist.orders(order_id),
    payment_sequential   SMALLINT NOT NULL,
    payment_type         TEXT NOT NULL,
    payment_installments SMALLINT NOT NULL,
    payment_value        NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE olist.reviews (
    id                      BIGSERIAL PRIMARY KEY,
    review_id               TEXT NOT NULL,
    order_id                TEXT NOT NULL REFERENCES olist.orders(order_id),
    review_score            SMALLINT NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP NOT NULL,
    review_answer_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE olist.zip_locations (
    zip_code_prefix TEXT PRIMARY KEY,
    lat             DOUBLE PRECISION NOT NULL,
    lng             DOUBLE PRECISION NOT NULL,
    city            TEXT NOT NULL,
    state           CHAR(2) NOT NULL
);

CREATE INDEX idx_olist_orders_customer  ON olist.orders (customer_id);
CREATE INDEX idx_olist_orders_purchase  ON olist.orders (order_purchase_timestamp);
CREATE INDEX idx_olist_customers_unique ON olist.customers (customer_unique_id);
CREATE INDEX idx_olist_items_product    ON olist.order_items (product_id);
CREATE INDEX idx_olist_items_seller     ON olist.order_items (seller_id);
CREATE INDEX idx_olist_payments_order   ON olist.payments (order_id);
CREATE INDEX idx_olist_reviews_order    ON olist.reviews (order_id);

COMMENT ON TABLE olist.customers IS 'One row per customer_id. A person gets a NEW customer_id for every order; use customer_unique_id to count real customers or repeat buyers';
COMMENT ON COLUMN olist.customers.customer_id IS 'Per-order customer key (primary key); joins to olist.orders.customer_id';
COMMENT ON COLUMN olist.customers.customer_unique_id IS 'The real person. Repeat customer = customer_unique_id with more than one order';
COMMENT ON COLUMN olist.customers.zip_code_prefix IS 'First 5 digits of the Brazilian postcode (text, keeps leading zeros); joins to olist.zip_locations';
COMMENT ON COLUMN olist.customers.city IS 'Customer city, lower case without accents, e.g. sao paulo';
COMMENT ON COLUMN olist.customers.state IS 'Brazilian state code, e.g. SP, RJ, MG';

COMMENT ON TABLE olist.sellers IS 'Marketplace sellers';
COMMENT ON COLUMN olist.sellers.seller_id IS 'Seller key (primary key)';
COMMENT ON COLUMN olist.sellers.zip_code_prefix IS 'Seller postcode prefix (text)';
COMMENT ON COLUMN olist.sellers.city IS 'Seller city, lower case';
COMMENT ON COLUMN olist.sellers.state IS 'Seller state code, e.g. SP';

COMMENT ON TABLE olist.products IS 'Product catalogue (no product names, only category and dimensions)';
COMMENT ON COLUMN olist.products.product_id IS 'Product key (primary key)';
COMMENT ON COLUMN olist.products.category IS 'Category name in Portuguese, e.g. cama_mesa_banho';
COMMENT ON COLUMN olist.products.category_english IS 'Category name in English, e.g. bed_bath_table, health_beauty. Prefer this for questions in English';
COMMENT ON COLUMN olist.products.name_length IS 'Number of characters in the product name';
COMMENT ON COLUMN olist.products.description_length IS 'Number of characters in the product description';
COMMENT ON COLUMN olist.products.photos_qty IS 'Number of product photos';
COMMENT ON COLUMN olist.products.weight_g IS 'Weight in grams';
COMMENT ON COLUMN olist.products.length_cm IS 'Length in cm';
COMMENT ON COLUMN olist.products.height_cm IS 'Height in cm';
COMMENT ON COLUMN olist.products.width_cm IS 'Width in cm';

COMMENT ON TABLE olist.orders IS 'One row per order (Sep 2016 - Oct 2018). Delivered order = order_status = ''delivered''';
COMMENT ON COLUMN olist.orders.order_id IS 'Order key (primary key)';
COMMENT ON COLUMN olist.orders.customer_id IS 'Foreign key to olist.customers.customer_id (per-order customer key)';
COMMENT ON COLUMN olist.orders.order_status IS 'delivered, shipped, canceled, unavailable, invoiced, processing, created, approved';
COMMENT ON COLUMN olist.orders.order_purchase_timestamp IS 'When the order was placed; month = date_trunc(''month'', order_purchase_timestamp)';
COMMENT ON COLUMN olist.orders.order_approved_at IS 'When payment was approved';
COMMENT ON COLUMN olist.orders.order_delivered_carrier_date IS 'When the seller handed the order to the carrier';
COMMENT ON COLUMN olist.orders.order_delivered_customer_date IS 'When the customer received it. Delivery days = this minus order_purchase_timestamp';
COMMENT ON COLUMN olist.orders.order_estimated_delivery_date IS 'Promised delivery date. Late delivery = order_delivered_customer_date > this';

COMMENT ON TABLE olist.order_items IS 'One row per item in an order. GMV = SUM(price); revenue incl. freight = price + freight_value. Currency BRL';
COMMENT ON COLUMN olist.order_items.order_id IS 'Foreign key to olist.orders.order_id';
COMMENT ON COLUMN olist.order_items.order_item_id IS 'Item number within the order (1, 2, 3 ...)';
COMMENT ON COLUMN olist.order_items.product_id IS 'Foreign key to olist.products.product_id';
COMMENT ON COLUMN olist.order_items.seller_id IS 'Foreign key to olist.sellers.seller_id';
COMMENT ON COLUMN olist.order_items.shipping_limit_date IS 'Deadline for the seller to hand the item to the carrier';
COMMENT ON COLUMN olist.order_items.price IS 'Item price in BRL';
COMMENT ON COLUMN olist.order_items.freight_value IS 'Freight (shipping) cost for this item in BRL';

COMMENT ON TABLE olist.payments IS 'Payments for each order; one order can be paid in several parts';
COMMENT ON COLUMN olist.payments.order_id IS 'Foreign key to olist.orders.order_id';
COMMENT ON COLUMN olist.payments.payment_sequential IS 'Payment number within the order';
COMMENT ON COLUMN olist.payments.payment_type IS 'credit_card, boleto (bank slip), voucher, debit_card, not_defined';
COMMENT ON COLUMN olist.payments.payment_installments IS 'Number of instalments chosen';
COMMENT ON COLUMN olist.payments.payment_value IS 'Amount paid in BRL';

COMMENT ON TABLE olist.reviews IS 'Customer reviews of orders (review_id is not unique in the source, so id is a surrogate key)';
COMMENT ON COLUMN olist.reviews.id IS 'Surrogate primary key';
COMMENT ON COLUMN olist.reviews.review_id IS 'Review id from the source (can repeat)';
COMMENT ON COLUMN olist.reviews.order_id IS 'Foreign key to olist.orders.order_id';
COMMENT ON COLUMN olist.reviews.review_score IS 'Score from 1 (worst) to 5 (best)';
COMMENT ON COLUMN olist.reviews.review_comment_title IS 'Review title in Portuguese (often NULL)';
COMMENT ON COLUMN olist.reviews.review_comment_message IS 'Review text in Portuguese (often NULL)';
COMMENT ON COLUMN olist.reviews.review_creation_date IS 'When the review survey was sent';
COMMENT ON COLUMN olist.reviews.review_answer_timestamp IS 'When the customer answered';

COMMENT ON TABLE olist.zip_locations IS 'One row per postcode prefix: average latitude/longitude and most common city/state (built from 1M geolocation rows)';
COMMENT ON COLUMN olist.zip_locations.zip_code_prefix IS 'Postcode prefix (primary key); joins to customers/sellers zip_code_prefix';
COMMENT ON COLUMN olist.zip_locations.lat IS 'Average latitude';
COMMENT ON COLUMN olist.zip_locations.lng IS 'Average longitude';
COMMENT ON COLUMN olist.zip_locations.city IS 'Most common city name for this prefix';
COMMENT ON COLUMN olist.zip_locations.state IS 'Most common state code for this prefix';
