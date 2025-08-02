-- Migration Script: Add Year-wise Support to Existing Database
-- This script safely adds new columns to existing tables

-- Step 1: Add new columns to target_users table (if they don't exist)
DO $$ 
BEGIN
  -- Add reg_no column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'reg_no'
  ) THEN
    ALTER TABLE target_users ADD COLUMN reg_no TEXT;
  END IF;

  -- Add email column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'email'
  ) THEN
    ALTER TABLE target_users ADD COLUMN email TEXT;
  END IF;

  -- Add department column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'department'
  ) THEN
    ALTER TABLE target_users ADD COLUMN department TEXT NOT NULL DEFAULT 'CSE';
  END IF;

  -- Add academic_year column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'academic_year'
  ) THEN
    ALTER TABLE target_users ADD COLUMN academic_year TEXT;
  END IF;

  -- Add batch_year column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'batch_year'
  ) THEN
    ALTER TABLE target_users ADD COLUMN batch_year INTEGER;
  END IF;

  -- Add section column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'section'
  ) THEN
    ALTER TABLE target_users ADD COLUMN section TEXT;
  END IF;

  -- Add updated_at column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'target_users' AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE target_users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
  END IF;
END $$;

-- Step 2: Add constraint for academic_year after adding the column
DO $$ 
BEGIN
  -- Add check constraint if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name = 'target_users_academic_year_check'
  ) THEN
    ALTER TABLE target_users 
    ADD CONSTRAINT target_users_academic_year_check 
    CHECK (academic_year IN ('2nd Year', '3rd Year'));
  END IF;
END $$;

-- Step 3: Add new columns to user_contest_results table (if they don't exist)
DO $$ 
BEGIN
  -- Add department column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'user_contest_results' AND column_name = 'department'
  ) THEN
    ALTER TABLE user_contest_results ADD COLUMN department TEXT;
  END IF;

  -- Add academic_year column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'user_contest_results' AND column_name = 'academic_year'
  ) THEN
    ALTER TABLE user_contest_results ADD COLUMN academic_year TEXT;
  END IF;

  -- Add batch_year column if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'user_contest_results' AND column_name = 'batch_year'
  ) THEN
    ALTER TABLE user_contest_results ADD COLUMN batch_year INTEGER;
  END IF;
END $$;

-- Step 4: Create contest_stats table if it doesn't exist
CREATE TABLE IF NOT EXISTS contest_stats (
  id SERIAL PRIMARY KEY,
  contest_id INTEGER REFERENCES contests(contest_id),
  department TEXT DEFAULT 'CSE',
  academic_year TEXT, -- NULL for overall stats, '2nd Year'/'3rd Year' for specific stats
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

-- Step 5: Add new indexes (if they don't exist)
DO $$ 
BEGIN
  -- Add indexes only if they don't exist
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_results_department') THEN
    CREATE INDEX idx_user_results_department ON user_contest_results(department);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_results_year') THEN
    CREATE INDEX idx_user_results_year ON user_contest_results(academic_year);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_target_users_department') THEN
    CREATE INDEX idx_target_users_department ON target_users(department);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_target_users_year') THEN
    CREATE INDEX idx_target_users_year ON target_users(academic_year);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_target_users_batch') THEN
    CREATE INDEX idx_target_users_batch ON target_users(batch_year);
  END IF;
END $$;

-- Step 6: Create or replace the enhanced stats function
CREATE OR REPLACE FUNCTION update_contest_stats_enhanced(p_contest_id INTEGER)
RETURNS void AS $$
DECLARE
  year_rec RECORD;
BEGIN
  -- Update overall stats (all departments, all years)
  INSERT INTO contest_stats (
    contest_id, department, academic_year, max_score, min_score, avg_score,
    total_scored, target_users_found, target_users_total, success_rate
  )
  SELECT 
    p_contest_id,
    'CSE',
    NULL,
    MAX(score),
    MIN(score),
    AVG(score)::DECIMAL(5,2),
    COUNT(*) FILTER (WHERE participated = true),
    COUNT(*) FILTER (WHERE participated = true),
    (SELECT COUNT(*) FROM target_users WHERE active = true),
    ROUND((COUNT(*) FILTER (WHERE participated = true)::DECIMAL / 
           GREATEST((SELECT COUNT(*) FROM target_users WHERE active = true), 1)) * 100, 2)
  FROM user_contest_results 
  WHERE contest_id = p_contest_id
  ON CONFLICT (contest_id, department, academic_year) 
  DO UPDATE SET
    max_score = EXCLUDED.max_score,
    min_score = EXCLUDED.min_score,
    avg_score = EXCLUDED.avg_score,
    total_scored = EXCLUDED.total_scored,
    target_users_found = EXCLUDED.target_users_found,
    target_users_total = EXCLUDED.target_users_total,
    success_rate = EXCLUDED.success_rate;

  -- Update year-wise stats
  FOR year_rec IN 
    SELECT DISTINCT academic_year 
    FROM user_contest_results 
    WHERE contest_id = p_contest_id AND academic_year IS NOT NULL
  LOOP
    INSERT INTO contest_stats (
      contest_id, department, academic_year, max_score, min_score, avg_score,
      total_scored, target_users_found, target_users_total, success_rate
    )
    SELECT 
      p_contest_id,
      'CSE',
      year_rec.academic_year,
      MAX(score),
      MIN(score),
      AVG(score)::DECIMAL(5,2),
      COUNT(*) FILTER (WHERE participated = true),
      COUNT(*) FILTER (WHERE participated = true),
      (SELECT COUNT(*) FROM target_users WHERE academic_year = year_rec.academic_year AND active = true),
      ROUND((COUNT(*) FILTER (WHERE participated = true)::DECIMAL / 
             GREATEST((SELECT COUNT(*) FROM target_users WHERE academic_year = year_rec.academic_year AND active = true), 1)) * 100, 2)
    FROM user_contest_results 
    WHERE contest_id = p_contest_id AND academic_year = year_rec.academic_year
    ON CONFLICT (contest_id, department, academic_year) 
    DO UPDATE SET
      max_score = EXCLUDED.max_score,
      min_score = EXCLUDED.min_score,
      avg_score = EXCLUDED.avg_score,
      total_scored = EXCLUDED.total_scored,
      target_users_found = EXCLUDED.target_users_found,
      target_users_total = EXCLUDED.target_users_total,
      success_rate = EXCLUDED.success_rate;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Step 7: Create or replace trigger function
CREATE OR REPLACE FUNCTION trigger_update_contest_stats_enhanced()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM update_contest_stats_enhanced(NEW.contest_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Update trigger (drop old one if exists and create new one)
DROP TRIGGER IF EXISTS auto_update_contest_stats ON user_contest_results;
DROP TRIGGER IF EXISTS auto_update_contest_stats_enhanced ON user_contest_results;
CREATE TRIGGER auto_update_contest_stats_enhanced
  AFTER INSERT OR UPDATE ON user_contest_results
  FOR EACH ROW
  EXECUTE FUNCTION trigger_update_contest_stats_enhanced();

-- Step 9: Create views if they don't exist
DROP VIEW IF EXISTS contest_leaderboard_2nd_year;
CREATE VIEW contest_leaderboard_2nd_year AS
SELECT 
  ucr.*,
  tu.reg_no,
  tu.section
FROM user_contest_results ucr
JOIN target_users tu ON ucr.leetcode_id = tu.leetcode_id
WHERE tu.academic_year = '2nd Year'
ORDER BY ucr.contest_id DESC, ucr.rank ASC;

DROP VIEW IF EXISTS contest_leaderboard_3rd_year;
CREATE VIEW contest_leaderboard_3rd_year AS
SELECT 
  ucr.*,
  tu.reg_no,
  tu.section
FROM user_contest_results ucr
JOIN target_users tu ON ucr.leetcode_id = tu.leetcode_id
WHERE tu.academic_year = '3rd Year'
ORDER BY ucr.contest_id DESC, ucr.rank ASC;

DROP VIEW IF EXISTS contest_leaderboard_combined;
CREATE VIEW contest_leaderboard_combined AS
SELECT 
  ucr.*,
  tu.reg_no,
  tu.section,
  tu.academic_year,
  tu.batch_year
FROM user_contest_results ucr
JOIN target_users tu ON ucr.leetcode_id = tu.leetcode_id
ORDER BY ucr.contest_id DESC, ucr.rank ASC;

-- Step 10: Verification
SELECT 'Migration completed successfully!' as status;

-- Check the updated target_users structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'target_users'
ORDER BY ordinal_position;
