-- ========================================================
-- Smart Gym Membership & Fitness Management System
-- Update Script: Migrate Membership Plans to Sri Lankan Rupee (LKR)
-- Target Database: smart_gym_db
-- ========================================================

USE smart_gym_db;

-- 1. Update PLN-001: Monthly Standard (30 days) -> LKR 6,000.00
UPDATE membership_plans
SET price = 6000.00, updated_at = NOW()
WHERE plan_name = 'Monthly Standard' OR id = 1;

-- 2. Update PLN-002: Quarterly Fitness (90 days) -> LKR 16,500.00
UPDATE membership_plans
SET price = 16500.00, updated_at = NOW()
WHERE plan_name = 'Quarterly Fitness' OR id = 2;

-- 3. Update PLN-003: Half-Yearly Elite (180 days) -> LKR 30,000.00
UPDATE membership_plans
SET price = 30000.00, updated_at = NOW()
WHERE plan_name = 'Half-Yearly Elite' OR id = 3;

-- 4. Update PLN-004: Annual Premium Pro (365 days) -> LKR 54,000.00
UPDATE membership_plans
SET price = 54000.00, updated_at = NOW()
WHERE plan_name = 'Annual Premium Pro' OR id = 4;

-- Verify the updated prices
SELECT id, plan_name, duration_days, price, is_active FROM membership_plans ORDER BY id ASC;
