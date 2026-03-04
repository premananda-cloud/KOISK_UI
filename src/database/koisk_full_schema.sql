-- =============================================================================
-- koisk_full_schema.sql
-- Full schema — run once on a fresh database.
-- PostgreSQL 14+  |  Safe to re-run (IF NOT EXISTS everywhere)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Shared trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- users
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id               SERIAL PRIMARY KEY,
    username         VARCHAR(50)  UNIQUE NOT NULL,
    email            VARCHAR(255) UNIQUE,
    full_name        VARCHAR(255) NOT NULL,
    hashed_password  VARCHAR(255) NOT NULL,
    phone_number     VARCHAR(20),
    address          TEXT,
    city             VARCHAR(100),
    state            VARCHAR(100),
    postal_code      VARCHAR(10),
    is_active        BOOLEAN     DEFAULT TRUE,
    is_verified      BOOLEAN     DEFAULT FALSE,
    email_verified   BOOLEAN     DEFAULT FALSE,
    created_at       TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    last_login       TIMESTAMP,
    google_id        VARCHAR(255) UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_users_username   ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email      ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_users_updated_at') THEN
    CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

-- =============================================================================
-- admins  (department officers, super-admins, merchants)
-- =============================================================================
CREATE TABLE IF NOT EXISTS admins (
    id               SERIAL PRIMARY KEY,
    username         VARCHAR(50)  UNIQUE NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    full_name        VARCHAR(255) NOT NULL,
    hashed_password  VARCHAR(255) NOT NULL,
    -- role: super_admin | department_admin | merchant
    role             VARCHAR(50)  NOT NULL DEFAULT 'department_admin',
    -- NULL = super-admin scope; otherwise 'electricity'|'water'|'municipal'
    department       VARCHAR(50),
    -- merchant payment gateway config  {"gateway":"portone","merchant_id":"..."}
    merchant_config  JSONB        DEFAULT '{}',
    is_active        BOOLEAN     DEFAULT TRUE,
    created_at       TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    last_login       TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_admin_role       ON admins(role);
CREATE INDEX IF NOT EXISTS idx_admin_department ON admins(department);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_admins_updated_at') THEN
    CREATE TRIGGER trg_admins_updated_at BEFORE UPDATE ON admins
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

-- =============================================================================
-- payments  (must exist before service_requests FK)
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id                  VARCHAR(200) PRIMARY KEY,
    user_id             VARCHAR(200) NOT NULL,
    bill_id             VARCHAR(100) NOT NULL,
    department          VARCHAR(50)  NOT NULL,   -- electricity|water|municipal
    amount              DECIMAL(10,2) NOT NULL,
    currency            VARCHAR(3)   DEFAULT 'INR',
    gateway             VARCHAR(50)  NOT NULL,   -- portone|razorpay|mock
    gateway_payment_id  VARCHAR(200),
    gateway_order_id    VARCHAR(200),
    gateway_status      VARCHAR(50),
    payment_method      VARCHAR(50),             -- upi|card|netbanking
    consumer_number     VARCHAR(100),
    billing_period      VARCHAR(20),             -- YYYY-MM or YYYY
    reference_no        VARCHAR(100) UNIQUE,
    status              VARCHAR(50)  NOT NULL DEFAULT 'pending',
    error_message       TEXT,
    created_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    paid_at             TIMESTAMP,
    metadata            JSONB       DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_pay_user_id    ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_pay_status     ON payments(status);
CREATE INDEX IF NOT EXISTS idx_pay_dept       ON payments(department);
CREATE INDEX IF NOT EXISTS idx_pay_gw_order   ON payments(gateway_order_id);
CREATE INDEX IF NOT EXISTS idx_pay_created_at ON payments(created_at DESC);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_payments_updated_at') THEN
    CREATE TRIGGER trg_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

-- =============================================================================
-- service_requests  — unified audit log for all departments
-- =============================================================================
CREATE TABLE IF NOT EXISTS service_requests (
    id                  SERIAL PRIMARY KEY,
    service_request_id  VARCHAR(50)  UNIQUE NOT NULL,
    user_id             INTEGER REFERENCES users(id) ON DELETE SET NULL,
    department          VARCHAR(50)  NOT NULL,
    service_type        VARCHAR(80)  NOT NULL,
    status              VARCHAR(30)  NOT NULL DEFAULT 'SUBMITTED',
    payload             JSONB        DEFAULT '{}',
    handled_by_admin    INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    error_code          VARCHAR(50),
    error_message       TEXT,
    payment_id          VARCHAR(200) REFERENCES payments(id) ON DELETE SET NULL,
    created_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sr_department   ON service_requests(department);
CREATE INDEX IF NOT EXISTS idx_sr_service_type ON service_requests(service_type);
CREATE INDEX IF NOT EXISTS idx_sr_status       ON service_requests(status);
CREATE INDEX IF NOT EXISTS idx_sr_user_id      ON service_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_sr_created_at   ON service_requests(created_at DESC);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_sr_updated_at') THEN
    CREATE TRIGGER trg_sr_updated_at BEFORE UPDATE ON service_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

-- =============================================================================
-- electricity_meters
-- =============================================================================
CREATE TABLE IF NOT EXISTS electricity_meters (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    meter_number       VARCHAR(50) UNIQUE NOT NULL,
    meter_type         VARCHAR(50),
    status             VARCHAR(20) DEFAULT 'ACTIVE',
    load_requirement   FLOAT,
    monthly_bill       FLOAT DEFAULT 0.0,
    outstanding_amount FLOAT DEFAULT 0.0,
    last_reading       FLOAT,
    last_reading_date  TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_elec_user_id      ON electricity_meters(user_id);
CREATE INDEX IF NOT EXISTS idx_elec_meter_number ON electricity_meters(meter_number);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_elec_updated_at') THEN
    CREATE TRIGGER trg_elec_updated_at BEFORE UPDATE ON electricity_meters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

-- =============================================================================
-- water_consumers
-- =============================================================================
CREATE TABLE IF NOT EXISTS water_consumers (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consumer_number    VARCHAR(50) UNIQUE NOT NULL,
    property_type      VARCHAR(50),
    status             VARCHAR(20) DEFAULT 'ACTIVE',
    monthly_bill       FLOAT DEFAULT 0.0,
    outstanding_amount FLOAT DEFAULT 0.0,
    last_reading       FLOAT,
    last_reading_date  TIMESTAMP,
    usage_limit        FLOAT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_water_user_id         ON water_consumers(user_id);
CREATE INDEX IF NOT EXISTS idx_water_consumer_number ON water_consumers(consumer_number);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_water_updated_at') THEN
    CREATE TRIGGER trg_water_updated_at BEFORE UPDATE ON water_consumers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

-- =============================================================================
-- municipal_consumers  (NEW department)
-- =============================================================================
CREATE TABLE IF NOT EXISTS municipal_consumers (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consumer_number    VARCHAR(50)  UNIQUE NOT NULL,
    -- Property tax
    property_id        VARCHAR(50),
    property_type      VARCHAR(50),   -- Residential|Commercial|Industrial
    ward_number        VARCHAR(20),
    zone               VARCHAR(50),
    -- Trade license
    trade_license_no   VARCHAR(50),
    business_name      VARCHAR(200),
    -- Billing
    annual_tax         FLOAT DEFAULT 0.0,
    outstanding_amount FLOAT DEFAULT 0.0,
    last_paid_date     TIMESTAMP,
    status             VARCHAR(20) DEFAULT 'ACTIVE',
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_muni_user_id         ON municipal_consumers(user_id);
CREATE INDEX IF NOT EXISTS idx_muni_consumer_number ON municipal_consumers(consumer_number);
CREATE INDEX IF NOT EXISTS idx_muni_property_id     ON municipal_consumers(property_id);
CREATE INDEX IF NOT EXISTS idx_muni_ward            ON municipal_consumers(ward_number);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_muni_updated_at') THEN
    CREATE TRIGGER trg_muni_updated_at BEFORE UPDATE ON municipal_consumers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

-- =============================================================================
-- payment_profiles
-- =============================================================================
CREATE TABLE IF NOT EXISTS payment_profiles (
    id                   VARCHAR(200) PRIMARY KEY,
    user_id              INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    portone_customer_id  VARCHAR(200) UNIQUE,
    razorpay_customer_id VARCHAR(200),
    name                 VARCHAR(200) NOT NULL,
    contact              VARCHAR(20)  NOT NULL,
    email                VARCHAR(200),
    default_method       VARCHAR(50),
    preferred_gateway    VARCHAR(50) DEFAULT 'portone',
    is_default           BOOLEAN DEFAULT TRUE,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pp_portone_id ON payment_profiles(portone_customer_id);

-- =============================================================================
-- refunds
-- =============================================================================
CREATE TABLE IF NOT EXISTS refunds (
    id                VARCHAR(200) PRIMARY KEY,
    payment_id        VARCHAR(200) NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    amount            DECIMAL(10,2) NOT NULL,
    reason            TEXT,
    gateway_refund_id VARCHAR(200),
    status            VARCHAR(50) DEFAULT 'pending',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_refunds_payment_id ON refunds(payment_id);

-- =============================================================================
-- Seed data — demo records for testing without a real gateway
-- =============================================================================

-- Default super admin  (password: Admin@1234 — bcrypt hash)
INSERT INTO admins (username, email, full_name, hashed_password, role, department)
VALUES (
    'superadmin',
    'admin@koisk.local',
    'KOISK Super Admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaJqhNzFIBqSP1OQmK.hVPKSy',
    'super_admin',
    NULL
)
ON CONFLICT (username) DO NOTHING;

-- Department admins
INSERT INTO admins (username, email, full_name, hashed_password, role, department)
VALUES
  ('elec_admin',  'elec@koisk.local',  'Electricity Officer', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaJqhNzFIBqSP1OQmK.hVPKSy', 'department_admin', 'electricity'),
  ('water_admin', 'water@koisk.local', 'Water Officer',       '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaJqhNzFIBqSP1OQmK.hVPKSy', 'department_admin', 'water'),
  ('muni_admin',  'muni@koisk.local',  'Municipal Officer',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaJqhNzFIBqSP1OQmK.hVPKSy', 'department_admin', 'municipal')
ON CONFLICT (username) DO NOTHING;

-- Demo user
INSERT INTO users (username, email, full_name, hashed_password, is_active, email_verified, phone_number)
VALUES ('demo_ramesh', 'ramesh@koisk.local', 'Ramesh Kumar',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaJqhNzFIBqSP1OQmK.hVPKSy',
        TRUE, TRUE, '+919876543210')
ON CONFLICT (username) DO NOTHING;

-- Demo consumer records
INSERT INTO electricity_meters (user_id, meter_number, meter_type, status, monthly_bill, outstanding_amount)
SELECT id, 'ELEC-MH-00234', 'Single Phase', 'ACTIVE', 1420.00, 1420.00
FROM users WHERE username='demo_ramesh'
ON CONFLICT (meter_number) DO NOTHING;

INSERT INTO water_consumers (user_id, consumer_number, property_type, status, monthly_bill, outstanding_amount)
SELECT id, 'WAT-MH-00891', 'Residential', 'ACTIVE', 310.00, 310.00
FROM users WHERE username='demo_ramesh'
ON CONFLICT (consumer_number) DO NOTHING;

INSERT INTO municipal_consumers (user_id, consumer_number, property_id, property_type, ward_number, zone, annual_tax, outstanding_amount)
SELECT id, 'MUNI-MH-00456', 'PROP-001234', 'Residential', 'W-14', 'North', 8500.00, 8500.00
FROM users WHERE username='demo_ramesh'
ON CONFLICT (consumer_number) DO NOTHING;

-- Permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO koisk_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO koisk_user;

SELECT 'Schema initialised successfully ✅' AS status;
