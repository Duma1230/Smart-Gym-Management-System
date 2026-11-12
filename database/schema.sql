-- ========================================================
-- Smart Gym Membership & Fitness Management System
-- Database Schema: smart_gym_db
-- Target: MySQL 8.0.46+
-- ========================================================

CREATE DATABASE IF NOT EXISTS smart_gym_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_gym_db;

-- --------------------------------------------------------
-- Table 1: users
-- Core authentication and role-based access table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'trainer', 'member') NOT NULL,
    status ENUM('pending', 'approved', 'rejected', 'inactive') NOT NULL DEFAULT 'pending',
    phone VARCHAR(20) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_status (status),
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 2: trainer_profiles
-- Extended details for trainers
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS trainer_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    specialization VARCHAR(150) NULL,
    experience_years INT NOT NULL DEFAULT 0,
    bio TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_trainer_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 3: member_profiles
-- Extended details for gym members and assigned trainer mapping
-- Current membership details are tracked in `memberships` table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS member_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    gender ENUM('male', 'female', 'other') NULL,
    date_of_birth DATE NULL,
    address TEXT NULL,
    emergency_contact VARCHAR(20) NULL,
    assigned_trainer_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_member_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_member_trainer
        FOREIGN KEY (assigned_trainer_id) REFERENCES users (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    INDEX idx_member_trainer (assigned_trainer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 4: membership_plans
-- Gym membership packages and pricing definitions
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS membership_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    duration_days INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_plans_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 5: memberships
-- Supports multiple renewal cycles per member
-- Status transitions: pending_payment -> active -> expired/cancelled
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS memberships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    plan_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('pending_payment', 'active', 'expired', 'cancelled') NOT NULL DEFAULT 'pending_payment',
    notes VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_membership_member
        FOREIGN KEY (member_id) REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_membership_plan
        FOREIGN KEY (plan_id) REFERENCES membership_plans (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    INDEX idx_memberships_member (member_id),
    INDEX idx_memberships_status (status),
    INDEX idx_memberships_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 6: payments
-- Offline payment records tied to a specific membership record
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    membership_id INT NOT NULL,
    member_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('Cash', 'Bank Transfer', 'Card (POS)', 'Cheque') NOT NULL,
    payment_date DATE NOT NULL,
    reference_number VARCHAR(100) NULL,
    notes VARCHAR(255) NULL,
    recorded_by_admin_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_membership
        FOREIGN KEY (membership_id) REFERENCES memberships (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_payment_member
        FOREIGN KEY (member_id) REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_payment_admin
        FOREIGN KEY (recorded_by_admin_id) REFERENCES users (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    INDEX idx_payments_membership (membership_id),
    INDEX idx_payments_member (member_id),
    INDEX idx_payments_date (payment_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 7: attendance
-- Daily attendance manually recorded by admin
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    check_in_time TIME NOT NULL,
    status ENUM('Present', 'Absent') NOT NULL DEFAULT 'Present',
    recorded_by_admin_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_attendance_member
        FOREIGN KEY (member_id) REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_attendance_admin
        FOREIGN KEY (recorded_by_admin_id) REFERENCES users (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT uq_member_daily_attendance
        UNIQUE (member_id, attendance_date),
    INDEX idx_attendance_date (attendance_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 8: workout_plans
-- Workout plans created by trainers for assigned members
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS workout_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    trainer_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    goal VARCHAR(150) NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    status ENUM('active', 'completed', 'archived') NOT NULL DEFAULT 'active',
    notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_workout_member
        FOREIGN KEY (member_id) REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_workout_trainer
        FOREIGN KEY (trainer_id) REFERENCES users (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    INDEX idx_workout_member (member_id),
    INDEX idx_workout_trainer (trainer_id),
    INDEX idx_workout_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 9: workout_plan_items
-- Exercise breakdown by day of week for a workout plan
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS workout_plan_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    workout_plan_id INT NOT NULL,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday') NOT NULL,
    exercise_name VARCHAR(100) NOT NULL,
    sets INT NOT NULL DEFAULT 3,
    reps VARCHAR(50) NOT NULL DEFAULT '10-12',
    instructions VARCHAR(255) NULL,
    order_index INT NOT NULL DEFAULT 1,
    CONSTRAINT fk_item_plan
        FOREIGN KEY (workout_plan_id) REFERENCES workout_plans (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_items_plan (workout_plan_id),
    INDEX idx_items_day (day_of_week)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table 10: fitness_progress
-- Fitness tracking metrics logged by trainers for members
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS fitness_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    trainer_id INT NOT NULL,
    recorded_date DATE NOT NULL,
    weight_kg DECIMAL(5, 2) NOT NULL,
    body_fat_percentage DECIMAL(4, 1) NULL,
    chest_cm DECIMAL(5, 1) NULL,
    waist_cm DECIMAL(5, 1) NULL,
    biceps_cm DECIMAL(5, 1) NULL,
    trainer_remarks TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_progress_member
        FOREIGN KEY (member_id) REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_progress_trainer
        FOREIGN KEY (trainer_id) REFERENCES users (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    INDEX idx_progress_member_date (member_id, recorded_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
