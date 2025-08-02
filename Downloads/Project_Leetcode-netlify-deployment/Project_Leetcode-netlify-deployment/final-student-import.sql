-- Final Setup: Add Missing Columns and Import Students
-- Your table structure is ready! Now we just need to add the missing columns and import data

-- Step 1: Add missing columns
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS department TEXT DEFAULT 'CSE';
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE;

-- Step 2: Add constraint for academic_year (with proper error handling)
DO $$ 
BEGIN
  -- Try to add the constraint, ignore if it already exists
  BEGIN
    ALTER TABLE target_users 
    ADD CONSTRAINT target_users_academic_year_check 
    CHECK (academic_year IN ('2nd Year', '3rd Year'));
  EXCEPTION
    WHEN duplicate_object THEN
      -- Constraint already exists, that's fine
      NULL;
  END;
END $$;

-- Step 3: Clear existing data (since we have better structured data now)
DELETE FROM target_users;
ALTER SEQUENCE target_users_id_seq RESTART WITH 1;

-- Step 4: Now paste the entire content from insert-target-users.sql below this line
-- (Copy everything from insert-target-users.sql and paste it here)

-- The insert-target-users.sql contains all 701 students with proper categorization:
-- - 257 students as "2nd Year" (2024 batch) 
-- - 444 students as "3rd Year" (2023 batch)
-- - Complete with reg numbers, emails, and sections

-- Step 5: Verification (run after importing)
SELECT 'Import completed!' as status;

SELECT 
    academic_year,
    COUNT(*) as student_count,
    COUNT(DISTINCT section) as sections_count
FROM target_users 
GROUP BY academic_year
ORDER BY academic_year;

SELECT 'Sample 2nd year students:' as info;
SELECT leetcode_id, display_name, reg_no, section 
FROM target_users 
WHERE academic_year = '2nd Year' 
LIMIT 5;

SELECT 'Sample 3rd year students:' as info;
SELECT leetcode_id, display_name 
FROM target_users 
WHERE academic_year = '3rd Year' 
LIMIT 5;
