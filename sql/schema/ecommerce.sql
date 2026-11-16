-- E-commerce schema: Amazon India seller sales (2022), split into products / orders / order_items.
-- Re-runnable: drops and recreates everything.
CREATE SCHEMA IF NOT EXISTS ecommerce;
DROP TABLE IF EXISTS ecommerce.order_items, ecommerce.orders, ecommerce.products CASCADE;

CREATE TABLE ecommerce.products (
    sku      TEXT PRIMARY KEY,
    style    TEXT,
    category TEXT,
    size     TEXT,
    asin     TEXT
);

CREATE TABLE ecommerce.orders (
    order_id           TEXT PRIMARY KEY,
    order_date         DATE NOT NULL,
    status             TEXT NOT NULL,
    fulfilment         TEXT,
    sales_channel      TEXT,
    ship_service_level TEXT,
    ship_city          TEXT,
    ship_state         TEXT,
    ship_postal_code   TEXT,
    is_b2b             BOOLEAN NOT NULL,
    has_promotion      BOOLEAN NOT NULL
);

CREATE TABLE ecommerce.order_items (
    id             BIGSERIAL PRIMARY KEY,
    order_id       TEXT NOT NULL REFERENCES ecommerce.orders(order_id),
    sku            TEXT NOT NULL REFERENCES ecommerce.products(sku),
    qty            INTEGER NOT NULL,
    amount         NUMERIC(12, 2),
    currency       TEXT,
    courier_status TEXT,
    amount_missing BOOLEAN NOT NULL
);

CREATE INDEX idx_orders_date       ON ecommerce.orders (order_date);
CREATE INDEX idx_orders_state      ON ecommerce.orders (ship_state);
CREATE INDEX idx_order_items_order ON ecommerce.order_items (order_id);
CREATE INDEX idx_order_items_sku   ON ecommerce.order_items (sku);

COMMENT ON TABLE ecommerce.products IS 'One row per SKU (stock keeping unit) sold by the seller';
COMMENT ON COLUMN ecommerce.products.sku IS 'SKU code (primary key)';
COMMENT ON COLUMN ecommerce.products.style IS 'Style / design code; several SKUs (sizes) share one style';
COMMENT ON COLUMN ecommerce.products.category IS 'Product category, e.g. Set, kurta, Western Dress, Top';
COMMENT ON COLUMN ecommerce.products.size IS 'Garment size, e.g. S, M, L, XL, XXL, Free';
COMMENT ON COLUMN ecommerce.products.asin IS 'Amazon Standard Identification Number';

COMMENT ON TABLE ecommerce.orders IS 'One row per customer order (Amazon India, 2022)';
COMMENT ON COLUMN ecommerce.orders.order_id IS 'Amazon order id (primary key)';
COMMENT ON COLUMN ecommerce.orders.order_date IS 'Date the order was placed. Month = date_trunc(''month'', order_date)';
COMMENT ON COLUMN ecommerce.orders.status IS 'Order status, e.g. Shipped, Shipped - Delivered to Buyer, Cancelled, Shipped - Returned to Seller. Cancelled orders have status starting with Cancelled';
COMMENT ON COLUMN ecommerce.orders.fulfilment IS 'Amazon (fulfilled by Amazon) or Merchant (seller ships)';
COMMENT ON COLUMN ecommerce.orders.sales_channel IS 'Amazon.in or Non-Amazon';
COMMENT ON COLUMN ecommerce.orders.ship_service_level IS 'Expedited or Standard shipping';
COMMENT ON COLUMN ecommerce.orders.ship_city IS 'Delivery city, Title Case';
COMMENT ON COLUMN ecommerce.orders.ship_state IS 'Delivery state, Title Case with spelling variants merged (e.g. Delhi, Puducherry)';
COMMENT ON COLUMN ecommerce.orders.ship_postal_code IS 'Delivery PIN code (text)';
COMMENT ON COLUMN ecommerce.orders.is_b2b IS 'TRUE for business (B2B) orders, FALSE for consumer (B2C)';
COMMENT ON COLUMN ecommerce.orders.has_promotion IS 'TRUE if any promotion was applied to the order';

COMMENT ON TABLE ecommerce.order_items IS 'One row per SKU line in an order. Revenue comes from amount here';
COMMENT ON COLUMN ecommerce.order_items.id IS 'Surrogate primary key';
COMMENT ON COLUMN ecommerce.order_items.order_id IS 'Foreign key to ecommerce.orders.order_id';
COMMENT ON COLUMN ecommerce.order_items.sku IS 'Foreign key to ecommerce.products.sku';
COMMENT ON COLUMN ecommerce.order_items.qty IS 'Quantity ordered (0 for many cancelled lines)';
COMMENT ON COLUMN ecommerce.order_items.amount IS 'Line amount in INR; NULL for many cancelled orders';
COMMENT ON COLUMN ecommerce.order_items.currency IS 'Currency code, INR';
COMMENT ON COLUMN ecommerce.order_items.courier_status IS 'Courier status: Shipped, Unshipped, Cancelled, or NULL';
COMMENT ON COLUMN ecommerce.order_items.amount_missing IS 'TRUE if amount was blank in the raw data (usually cancelled)';
