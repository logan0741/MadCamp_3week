-- MemeForty PostgreSQL Database Initialization Script
-- This script runs automatically when the PostgreSQL container starts

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text similarity search

-- ===========================================
-- AI Task Results Table
-- ===========================================
CREATE TABLE IF NOT EXISTS ai_task_results (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) UNIQUE NOT NULL,
    
    -- Task metadata
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    
    -- Input/Output
    input_params TEXT,  -- JSON
    output_json_path VARCHAR(500),
    output_image_paths TEXT,  -- JSON array
    output_glb_path VARCHAR(500),
    output_obj_path VARCHAR(500),
    
    -- Performance metrics
    vram_peak_mb INTEGER,
    processing_time_sec REAL,
    gpu_device VARCHAR(20),
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for ai_task_results
CREATE INDEX IF NOT EXISTS ix_task_status_created ON ai_task_results(status, created_at);
CREATE INDEX IF NOT EXISTS ix_task_type_status ON ai_task_results(task_type, status);
CREATE INDEX IF NOT EXISTS ix_task_id ON ai_task_results(task_id);

-- ===========================================
-- Musinsa Products Table
-- ===========================================
CREATE TABLE IF NOT EXISTS musinsa_products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(50),
    subcategory VARCHAR(50),
    
    -- Pricing
    original_price INTEGER,
    sale_price INTEGER,
    discount_rate INTEGER,
    
    -- PCCS color information
    pccs_hue REAL,
    pccs_value REAL,
    pccs_chroma REAL,
    pccs_tone VARCHAR(10),
    primary_color_hex VARCHAR(7),
    
    -- Size information
    sizes_json TEXT,  -- JSON
    available_sizes VARCHAR(100),
    
    -- Generated assets
    front_image_path VARCHAR(500),
    back_image_path VARCHAR(500),
    glb_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    
    -- External URLs
    product_url VARCHAR(500),
    image_url VARCHAR(500),
    
    -- Vector embedding (for similarity search)
    embedding_vector TEXT,  -- JSON array of floats
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for musinsa_products
CREATE INDEX IF NOT EXISTS ix_product_category_brand ON musinsa_products(category, brand);
CREATE INDEX IF NOT EXISTS ix_product_pccs_tone ON musinsa_products(pccs_tone);
CREATE INDEX IF NOT EXISTS ix_product_id ON musinsa_products(product_id);
CREATE INDEX IF NOT EXISTS ix_product_is_active ON musinsa_products(is_active);

-- GIN index for text search on product name
CREATE INDEX IF NOT EXISTS ix_product_name_trgm ON musinsa_products USING GIN (name gin_trgm_ops);

-- ===========================================
-- User Profiles Table
-- ===========================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    
    -- Body measurements (cm)
    height REAL,
    weight REAL,
    shoulder_width REAL,
    chest REAL,
    waist REAL,
    hip REAL,
    arm_length REAL,
    leg_length REAL,
    
    -- Personal Color Analysis
    pca_season VARCHAR(20),
    pca_type VARCHAR(20),
    skin_tone_hex VARCHAR(7),
    
    -- PCCS preferences
    preferred_tones VARCHAR(100),
    preferred_hue_range VARCHAR(50),
    
    -- Generated avatar
    avatar_glb_path VARCHAR(500),
    avatar_thumbnail_path VARCHAR(500),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_user_id ON user_profiles(user_id);

-- ===========================================
-- Recommendation Logs Table
-- ===========================================
CREATE TABLE IF NOT EXISTS recommendation_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36),
    session_id VARCHAR(36),
    
    -- Query info
    query_type VARCHAR(50),
    query_text TEXT,
    
    -- Results
    recommendations_json TEXT,  -- JSON array
    
    -- Scoring
    text_similarity_score REAL,
    pccs_distance_score REAL,
    combined_score REAL,
    
    -- User interaction
    clicked_product_id VARCHAR(50),
    purchased_product_id VARCHAR(50),
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_rec_user_id ON recommendation_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_rec_session_id ON recommendation_logs(session_id);
CREATE INDEX IF NOT EXISTS ix_rec_created ON recommendation_logs(created_at);

-- ===========================================
-- Utility Functions
-- ===========================================

-- Function to update 'updated_at' timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
DROP TRIGGER IF EXISTS update_musinsa_products_updated_at ON musinsa_products;
CREATE TRIGGER update_musinsa_products_updated_at
    BEFORE UPDATE ON musinsa_products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- Sample Data (Optional - for testing)
-- ===========================================

-- Insert sample PCCS tone reference
CREATE TABLE IF NOT EXISTS pccs_tones (
    id SERIAL PRIMARY KEY,
    tone_code VARCHAR(10) UNIQUE NOT NULL,
    tone_name VARCHAR(50),
    tone_name_ko VARCHAR(50),
    value_range VARCHAR(20),
    chroma_range VARCHAR(20)
);

INSERT INTO pccs_tones (tone_code, tone_name, tone_name_ko, value_range, chroma_range)
VALUES
    ('v', 'vivid', '비비드', '4-6', '12-14'),
    ('b', 'bright', '브라이트', '7-8', '8-10'),
    ('s', 'strong', '스트롱', '4-6', '8-10'),
    ('dp', 'deep', '딥', '3-4', '6-8'),
    ('lt', 'light', '라이트', '7-8', '4-6'),
    ('sf', 'soft', '소프트', '5-6', '4-6'),
    ('d', 'dull', '덜', '4-5', '2-4'),
    ('dk', 'dark', '다크', '2-3', '4-6'),
    ('p', 'pale', '페일', '8-9', '2-3'),
    ('ltg', 'light grayish', '라이트 그레이시', '6-7', '1-2'),
    ('g', 'grayish', '그레이시', '4-5', '1-2'),
    ('dkg', 'dark grayish', '다크 그레이시', '2-3', '1-2')
ON CONFLICT (tone_code) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO memeforty;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO memeforty;

-- Confirm initialization
DO $$
BEGIN
    RAISE NOTICE 'MemeForty database initialized successfully!';
END $$;
