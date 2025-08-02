-- Updated LeetCode Contest Auto-Fetcher Database Schema
-- Enhanced to support department and year-wise categorization

-- Table: contests (unchanged)
CREATE TABLE contests (
  id SERIAL PRIMARY KEY,
  contest_id INTEGER UNIQUE NOT NULL,
  title TEXT NOT NULL,
  contest_type TEXT NOT NULL CHECK (contest_type IN ('weekly', 'biweekly')),
  start_time TIMESTAMP WITH TIME ZONE NOT NULL,
  end_time TIMESTAMP WITH TIME ZONE NOT NULL,
  total_participants INTEGER DEFAULT 0,
  data_fetched BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enhanced Table: target_users
-- Updated to include department, year, and section information
CREATE TABLE target_users (
  id SERIAL PRIMARY KEY,
  leetcode_id TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  reg_no TEXT,
  email TEXT,
  department TEXT NOT NULL DEFAULT 'CSE',
  academic_year TEXT NOT NULL CHECK (academic_year IN ('2nd Year', '3rd Year')),
  batch_year INTEGER NOT NULL, -- 2024, 2023, etc.
  section TEXT, -- A, B, C, etc.
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: user_contest_results (updated with department info)
CREATE TABLE user_contest_results (
  id SERIAL PRIMARY KEY,
  contest_id INTEGER REFERENCES contests(contest_id),
  leetcode_id TEXT REFERENCES target_users(leetcode_id),
  display_name TEXT,
  rank INTEGER,
  score INTEGER,
  finish_time INTEGER,
  matched_variation TEXT,
  original_leetcode_id TEXT,
  participated BOOLEAN DEFAULT FALSE,
  -- Add department and year for easier filtering
  department TEXT,
  academic_year TEXT,
  batch_year INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(contest_id, leetcode_id)
);

-- Table: contest_stats (enhanced with year-wise stats)
CREATE TABLE contest_stats (
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

-- Indexes for better performance
CREATE INDEX idx_contests_start_time ON contests(start_time);
CREATE INDEX idx_contests_type ON contests(contest_type);
CREATE INDEX idx_user_results_contest ON user_contest_results(contest_id);
CREATE INDEX idx_user_results_user ON user_contest_results(leetcode_id);
CREATE INDEX idx_user_results_department ON user_contest_results(department);
CREATE INDEX idx_user_results_year ON user_contest_results(academic_year);
CREATE INDEX idx_target_users_department ON target_users(department);
CREATE INDEX idx_target_users_year ON target_users(academic_year);
CREATE INDEX idx_target_users_batch ON target_users(batch_year);

-- Enhanced function to update contest stats (year-wise)
CREATE OR REPLACE FUNCTION update_contest_stats_enhanced(p_contest_id INTEGER)
RETURNS void AS $$
DECLARE
  dept_rec RECORD;
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
           (SELECT COUNT(*) FROM target_users WHERE active = true)) * 100, 2)
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
             (SELECT COUNT(*) FROM target_users WHERE academic_year = year_rec.academic_year AND active = true)) * 100, 2)
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

-- Updated trigger function
CREATE OR REPLACE FUNCTION trigger_update_contest_stats_enhanced()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM update_contest_stats_enhanced(NEW.contest_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop old trigger and create new one
DROP TRIGGER IF EXISTS auto_update_contest_stats ON user_contest_results;
CREATE TRIGGER auto_update_contest_stats_enhanced
  AFTER INSERT OR UPDATE ON user_contest_results
  FOR EACH ROW
  EXECUTE FUNCTION trigger_update_contest_stats_enhanced();

-- Enable Row Level Security
ALTER TABLE contests ENABLE ROW LEVEL SECURITY;
ALTER TABLE target_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_contest_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE contest_stats ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access
CREATE POLICY "Public read access" ON contests FOR SELECT USING (true);
CREATE POLICY "Public read access" ON target_users FOR SELECT USING (true);
CREATE POLICY "Public read access" ON user_contest_results FOR SELECT USING (true);
CREATE POLICY "Public read access" ON contest_stats FOR SELECT USING (true);

-- Views for easy querying
CREATE VIEW contest_leaderboard_2nd_year AS
SELECT 
  ucr.*,
  tu.reg_no,
  tu.section
FROM user_contest_results ucr
JOIN target_users tu ON ucr.leetcode_id = tu.leetcode_id
WHERE tu.academic_year = '2nd Year'
ORDER BY ucr.contest_id DESC, ucr.rank ASC;

CREATE VIEW contest_leaderboard_3rd_year AS
SELECT 
  ucr.*,
  tu.reg_no,
  tu.section
FROM user_contest_results ucr
JOIN target_users tu ON ucr.leetcode_id = tu.leetcode_id
WHERE tu.academic_year = '3rd Year'
ORDER BY ucr.contest_id DESC, ucr.rank ASC;

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
