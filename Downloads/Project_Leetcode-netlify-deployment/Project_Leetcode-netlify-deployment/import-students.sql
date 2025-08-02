-- Step 2: Update existing users and import new ones
-- Run this AFTER the database-migration.sql script

-- First, clear all existing data to avoid conflicts
DELETE FROM user_contest_results;
DELETE FROM target_users;
ALTER SEQUENCE target_users_id_seq RESTART WITH 1;

-- Now import all the new student data
-- Copy and paste the content from insert-target-users.sql below this line

-- Verification queries
SELECT 
    academic_year,
    COUNT(*) as student_count,
    COUNT(DISTINCT section) as sections
FROM target_users 
GROUP BY academic_year
ORDER BY academic_year;

SELECT 
    academic_year,
    section,
    COUNT(*) as count
FROM target_users 
WHERE section IS NOT NULL
GROUP BY academic_year, section
ORDER BY academic_year, section;
