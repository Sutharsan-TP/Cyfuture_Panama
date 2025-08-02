-- Targeted Migration - Only add what's actually missing
-- Run this AFTER running check-database-structure.sql to see what exists

-- Add reg_no column (only if missing)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'reg_no'
  ) THEN
    ALTER TABLE target_users ADD COLUMN reg_no TEXT;
  END IF;
END $$;

-- Add email column (only if missing)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'email'
  ) THEN
    ALTER TABLE target_users ADD COLUMN email TEXT;
  END IF;
END $$;

-- Add section column (only if missing)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'section'
  ) THEN
    ALTER TABLE target_users ADD COLUMN section TEXT;
  END IF;
END $$;

-- Add batch_year column (only if missing)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'batch_year'
  ) THEN
    ALTER TABLE target_users ADD COLUMN batch_year INTEGER;
  END IF;
END $$;

-- Add academic_year column (only if missing) - MUST come before constraint
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'academic_year'
  ) THEN
    ALTER TABLE target_users ADD COLUMN academic_year TEXT;
  END IF;
END $$;

-- Update the academic_year constraint (drop and recreate to be safe)
DO $$ 
BEGIN
  -- Drop constraint if it exists
  IF EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'target_users_academic_year_check'
  ) THEN
    ALTER TABLE target_users DROP CONSTRAINT target_users_academic_year_check;
  END IF;
  
  -- Add the constraint (only if academic_year column exists)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'academic_year'
  ) THEN
    ALTER TABLE target_users 
    ADD CONSTRAINT target_users_academic_year_check 
    CHECK (academic_year IN ('2nd Year', '3rd Year'));
  END IF;
END $$;

-- Add department column with default (only if missing)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'department'
  ) THEN
    ALTER TABLE target_users ADD COLUMN department TEXT NOT NULL DEFAULT 'CSE';
  END IF;
END $$;

-- Add updated_at column (only if missing)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE target_users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
  END IF;
END $$;

-- Add columns to user_contest_results (only if missing)
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'user_contest_results' AND column_name = 'department'
  ) THEN
    ALTER TABLE user_contest_results ADD COLUMN department TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'user_contest_results' AND column_name = 'academic_year'
  ) THEN
    ALTER TABLE user_contest_results ADD COLUMN academic_year TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'user_contest_results' AND column_name = 'batch_year'
  ) THEN
    ALTER TABLE user_contest_results ADD COLUMN batch_year INTEGER;
  END IF;
END $$;

-- Create contest_stats table if it doesn't exist
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

-- Verification
SELECT 'Migration step completed!' as status;
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'target_users'
ORDER BY ordinal_position;
