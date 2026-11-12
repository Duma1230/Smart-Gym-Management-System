-- ========================================================
-- Smart Gym Membership & Fitness Management System
-- Safe Seed / Sample Data for Local Development & Testing
-- ========================================================

USE smart_gym_db;

-- --------------------------------------------------------
-- 1. Insert Initial Membership Plans (Prices in LKR)
-- --------------------------------------------------------
INSERT INTO membership_plans (plan_name, description, duration_days, price, is_active) VALUES
('Monthly Standard', 'Access to gym equipment, cardio zone, and locker rooms.', 30, 6000.00, 1),
('Quarterly Fitness', 'Full gym access plus 1 complimentary trainer assessment.', 90, 16500.00, 1),
('Half-Yearly Elite', 'Full gym access, personalized workout review, and locker priority.', 180, 30000.00, 1),
('Annual Premium Pro', 'All-inclusive annual membership with priority trainer assignment and wellness tracking.', 365, 54000.00, 1);

-- --------------------------------------------------------
-- 2. Insert Initial Users
-- Password for all seed users is set to their role default for local testing:
-- Admin:   admin@smartgym.com       / Admin@123
-- Trainer: john.trainer@smartgym.com / Trainer@123
-- Member:  sarah.member@smartgym.com / Member@123
-- Pending: mike.pending@smartgym.com / Member@123
-- --------------------------------------------------------
INSERT INTO users (id, full_name, email, password_hash, role, status, phone) VALUES
(1, 'System Administrator', 'admin@smartgym.com', 'scrypt:32768:8:1$8ASM63KMV2b7mExZ$4fe7ddc77e9651afe4d2a34a4331f73b1fa7983cb366e1bd7753968ce5311209b07d28973ecf741589eaad74024d6c0b3cc218b7e7097acb392584abe842d6c1', 'admin', 'approved', '+1-555-0100'),
(2, 'John Davis', 'john.trainer@smartgym.com', 'scrypt:32768:8:1$VNm7Q7xGQy5XoEyK$7bfebb64ba5364380e89ce68b3e91128866d056dc387b7ac0606778decd3ab1734d2351601739709efcb12010e2a8a04d77978d09ee9365ea433321c726c62b3', 'trainer', 'approved', '+1-555-0101'),
(3, 'Sarah Connor', 'sarah.member@smartgym.com', 'scrypt:32768:8:1$I1bWZKtOjaOzhEDE$fbf6fa5ff061d9c158b213c1eaf0e369d3f8a1c1b4a1aa425e5c688a4b6a59fe0c54faba15076f8500476a94ef4421dfbbdbded13e0f55911ca468924641dc58', 'member', 'approved', '+1-555-0102'),
(4, 'Mike Ross', 'mike.pending@smartgym.com', 'scrypt:32768:8:1$I1bWZKtOjaOzhEDE$fbf6fa5ff061d9c158b213c1eaf0e369d3f8a1c1b4a1aa425e5c688a4b6a59fe0c54faba15076f8500476a94ef4421dfbbdbded13e0f55911ca468924641dc58', 'member', 'pending', '+1-555-0103');

-- --------------------------------------------------------
-- 3. Insert Trainer Profile (User ID 2)
-- --------------------------------------------------------
INSERT INTO trainer_profiles (user_id, specialization, experience_years, bio) VALUES
(2, 'Strength & Conditioning, Functional Movement', 5, 'Certified fitness specialist focused on strength training and injury prevention.');

-- --------------------------------------------------------
-- 4. Insert Member Profiles (User ID 3 and 4)
-- Sarah (approved, assigned to trainer John)
-- Mike (pending approval)
-- --------------------------------------------------------
INSERT INTO member_profiles (user_id, gender, date_of_birth, address, emergency_contact, assigned_trainer_id) VALUES
(3, 'female', '1996-05-14', '742 Evergreen Terrace, Springfield', '+1-555-0999', 2),
(4, 'male', '1999-11-20', '123 Baker Street, Springfield', '+1-555-0888', NULL);

-- --------------------------------------------------------
-- 5. Insert Sample Membership (Sarah - Active Quarterly Plan)
-- --------------------------------------------------------
INSERT INTO memberships (id, member_id, plan_id, start_date, end_date, status, notes) VALUES
(1, 3, 2, '2026-11-01', '2027-01-30', 'active', 'Initial quarterly membership package paid in full.');

-- --------------------------------------------------------
-- 6. Insert Offline Payment (for Sarah's Membership 1)
-- --------------------------------------------------------
INSERT INTO payments (membership_id, member_id, amount, payment_method, payment_date, reference_number, notes, recorded_by_admin_id) VALUES
(1, 3, 16500.00, 'Cash', '2026-11-01', 'REC-2026-001', 'Paid in cash at reception. Membership activated.', 1);

-- --------------------------------------------------------
-- 7. Insert Attendance Records (Sarah)
-- --------------------------------------------------------
INSERT INTO attendance (member_id, attendance_date, check_in_time, status, recorded_by_admin_id) VALUES
(3, '2026-11-02', '07:15:00', 'Present', 1),
(3, '2026-11-04', '07:30:00', 'Present', 1),
(3, '2026-11-06', '07:10:00', 'Present', 1);

-- --------------------------------------------------------
-- 8. Insert Workout Plan & Items (Created by John for Sarah)
-- --------------------------------------------------------
INSERT INTO workout_plans (id, member_id, trainer_id, title, goal, start_date, end_date, status, notes) VALUES
(1, 3, 2, 'Hypertrophy & Core Foundation', 'Lean muscle gain and core strength', '2026-11-01', '2026-11-30', 'active', 'Focus on controlled tempo and full range of motion.');

INSERT INTO workout_plan_items (workout_plan_id, day_of_week, exercise_name, sets, reps, instructions, order_index) VALUES
(1, 'Monday', 'Barbell Squat', 4, '10-12', 'Rest 90 seconds between sets. Warm up thoroughly.', 1),
(1, 'Monday', 'Romanian Deadlift', 3, '12', 'Focus on hamstring stretch and neutral spine.', 2),
(1, 'Wednesday', 'Dumbbell Bench Press', 4, '10-12', 'Squeeze chest at peak contraction.', 1),
(1, 'Wednesday', 'Seated Cable Row', 3, '12-15', 'Full scapular retraction on pull.', 2),
(1, 'Friday', 'Overhead Shoulder Press', 3, '10', 'Keep core braced and ribs down.', 1),
(1, 'Friday', 'Plank Hold', 3, '45-60 sec', 'Maintain straight body alignment.', 2);

-- --------------------------------------------------------
-- 9. Insert Fitness Progress Log (Logged by John for Sarah)
-- --------------------------------------------------------
INSERT INTO fitness_progress (member_id, trainer_id, recorded_date, weight_kg, body_fat_percentage, chest_cm, waist_cm, biceps_cm, trainer_remarks) VALUES
(3, 2, '2026-11-01', 65.50, 24.2, 92.0, 75.0, 28.5, 'Baseline measurement upon joining. Good posture and mobility.'),
(3, 2, '2026-11-08', 64.80, 23.6, 92.0, 74.0, 28.7, 'Solid adherence to week 1 routine. Energy levels improved.');
