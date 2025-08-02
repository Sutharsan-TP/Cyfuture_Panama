-- Simple Database Migration - Check existing structure first
-- Run this to see what already exists

SELECT 'Current target_users columns:' as info;
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'target_users'
ORDER BY ordinal_position;

-- Check if we need to add columns
SELECT 
  CASE 
    WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'target_users' AND column_name = 'academic_year') 
    THEN 'academic_year column already exists'
    ELSE 'academic_year column MISSING - needs to be added'
  END as academic_year_status,
  
  CASE 
    WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'target_users' AND column_name = 'batch_year') 
    THEN 'batch_year column already exists'
    ELSE 'batch_year column MISSING - needs to be added'
  END as batch_year_status,
  
  CASE 
    WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'target_users' AND column_name = 'reg_no') 
    THEN 'reg_no column already exists'
    ELSE 'reg_no column MISSING - needs to be added'
  END as reg_no_status,
  
  CASE 
    WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'target_users' AND column_name = 'section') 
    THEN 'section column already exists'
    ELSE 'section column MISSING - needs to be added'
  END as section_status;
