-- Musinsa Price Tracker PostgreSQL Database Initialization Script
-- This script runs automatically when the PostgreSQL container starts

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text similarity search

-- ===========================================
-- Users Table
-- ===========================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);

-- ===========================================
-- Products Table (Musinsa Product Information)
-- ===========================================
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    musinsa_id VARCHAR(20) UNIQUE NOT NULL,
    url TEXT NOT NULL,
    title VARCHAR(255),
    brand VARCHAR(100),
    thumbnail_url TEXT,
    image_urls TEXT,  -- JSON array of image URLs for carousel
    original_price INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- AI Analysis Fields
    is_garment_modeled BOOLEAN DEFAULT FALSE,
    
    -- Color Analysis
    pccs_hue VARCHAR(20),
    pccs_value VARCHAR(20),
    pccs_chroma VARCHAR(20),
    pccs_tone VARCHAR(20),
    primary_color_hex VARCHAR(20),
    color_temperature VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS ix_products_musinsa_id ON products(musinsa_id);
CREATE INDEX IF NOT EXISTS ix_products_brand ON products(brand);

-- GIN index for text search on product title
CREATE INDEX IF NOT EXISTS ix_product_title_trgm ON products USING GIN (title gin_trgm_ops);

-- ===========================================
-- User Interests Table (User-Product M:N)
-- ===========================================
CREATE TABLE IF NOT EXISTS user_interests (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, product_id)
);

CREATE INDEX IF NOT EXISTS ix_user_interests_user_id ON user_interests(user_id);
CREATE INDEX IF NOT EXISTS ix_user_interests_product_id ON user_interests(product_id);

-- ===========================================
-- Price Logs Table (Price History for Charts)
-- ===========================================
CREATE TABLE IF NOT EXISTS price_logs (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price INTEGER NOT NULL,
    discount_rate INTEGER,
    captured_at DATE DEFAULT CURRENT_DATE,
    UNIQUE (product_id, captured_at)
);

CREATE INDEX IF NOT EXISTS ix_price_logs_product_id ON price_logs(product_id);
CREATE INDEX IF NOT EXISTS ix_price_logs_captured_at ON price_logs(captured_at);

-- ===========================================
-- Utility Functions
-- ===========================================

-- Function to update 'updated_at' timestamp automatically (for future use)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ===========================================
-- Grant Permissions
-- ===========================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO memeforty;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO memeforty;

-- Confirm initialization
DO $$
BEGIN
    RAISE NOTICE 'Musinsa Price Tracker database initialized successfully!';
END $$;
