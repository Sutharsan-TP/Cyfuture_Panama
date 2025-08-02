-- Simple Step-by-Step Migration
-- Run each section separately if you encounter errors

-- STEP 1: Add basic columns
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS reg_no TEXT;
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS section TEXT;
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS department TEXT DEFAULT 'CSE';
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS academic_year TEXT;
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS batch_year INTEGER;
ALTER TABLE target_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- STEP 2: Add constraint for academic_year
ALTER TABLE target_users 
ADD CONSTRAINT target_users_academic_year_check 
CHECK (academic_year IN ('2nd Year', '3rd Year'));

-- STEP 3: Add columns to user_contest_results
ALTER TABLE user_contest_results ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE user_contest_results ADD COLUMN IF NOT EXISTS academic_year TEXT;
ALTER TABLE user_contest_results ADD COLUMN IF NOT EXISTS batch_year INTEGER;

-- STEP 4: Create contest_stats table
CREATE TABLE IF NOT EXISTS contest_stats (
  id SERIAL PRIMARY KEY,
  contest_id INTEGER REFERENCES contests(contest_id),
  department TEXT DEFAULT 'CSE',
  academic_year TEXT,
  max_score INTEGER,
  min_score INTEGER,
  avg_score DECIMAL(5,2),
  total_scored INTEGER,
  target_users_found INTEGER DEFAULT 0,
  target_users_total INTEGER,
  success_rate DECIMAL(5,2),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(contest_id, department, academic_year)
);

-- STEP 5: Verify structure
SELECT 'Migration completed!' as status;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'target_users'
ORDER BY ordinal_position;
