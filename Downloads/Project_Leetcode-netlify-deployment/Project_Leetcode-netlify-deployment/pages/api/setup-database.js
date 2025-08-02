import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const supabase = createClient(supabaseUrl, supabaseKey)

export default async function handler(req, res) {
  if (req.method === 'POST') {
    try {
      console.log('🚀 Running complete database setup...')
      
      // Since we can't run raw SQL directly, let's create tables using the Supabase client
      // First, let's try to insert target users which will tell us if tables exist
      
      const targetUsers = [
        { leetcode_id: 'Abijith_U', display_name: 'ABIJITH U' },
        { leetcode_id: 'Abinav_Kishore', display_name: 'ABINAV KISHORE R S' },
        { leetcode_id: 'aditi_baskaran', display_name: 'ADITI BASKARAN' },
        { leetcode_id: 'Akila_Sriniddhi', display_name: 'AKILA SRINIDDHI N' },
        { leetcode_id: 'amoghvj', display_name: 'AMOGH VIJAY' },
        { leetcode_id: 'Ashwa_govi1', display_name: 'ASHWANTHIKA GOVINDARAJA' },
        { leetcode_id: 'balarathi_p', display_name: 'BALARATHI P' },
        { leetcode_id: 'Barkavi_010', display_name: 'BARKAVI R' },
        { leetcode_id: 'blessow', display_name: 'BLESSOW M' },
        { leetcode_id: 'VEDHADEVAREDDY', display_name: 'DEVAREDDY VEDHA' },
        { leetcode_id: 'Dhiva257', display_name: 'DHIVASHINI R' },
        { leetcode_id: 'GOKUL J', display_name: 'GOKUL J' },
        { leetcode_id: 'Gokul__0', display_name: 'GOKUL V' },
        { leetcode_id: 'Hemhalatha06', display_name: 'HEMHALATHA V R' },
        { leetcode_id: 'hemprasath80', display_name: 'HEMPRASATH SANKAR' },
        { leetcode_id: 'irfanullahbaig', display_name: 'IRFANULLAH BAIG N' },
        { leetcode_id: 'ISHANTHLEEMAN I', display_name: 'I ISHANTH LEEMAN' },
        { leetcode_id: 'MRIDINIJ', display_name: 'J MRIDINI' },
        { leetcode_id: 'Suraj0517', display_name: 'J SURAJ' },
        { leetcode_id: 'Yathish_2006', display_name: 'J YATHISH' },
        { leetcode_id: 'jack-v14', display_name: 'JACK V' },
        { leetcode_id: 'Jaiganesh16', display_name: 'JAIGANESH S' },
        { leetcode_id: 'jeevapriyan10', display_name: 'JEEVA PRIYAN R' },
        { leetcode_id: 'Mohit75', display_name: 'K MOHIT' },
        { leetcode_id: 'shashanthk', display_name: 'K SHASHANTH' },
        { leetcode_id: 'KanishJebaMathewM', display_name: 'KANISH JEBA MATHEW M' },
        { leetcode_id: 'mkaushikkavindra ', display_name: 'KAUSHIK KAVINDRA M' },
        { leetcode_id: 'kaysav18', display_name: 'KAYSAV PIRANAV P' },
        { leetcode_id: 'Keerthana_K_S', display_name: 'KEERTHANA K S' },
        { leetcode_id: 'Madhesh2007 ', display_name: 'L MADHESH' },
        { leetcode_id: 'Lokith_S', display_name: 'LOKITH S' },
        { leetcode_id: 'bhuvaneswar_123_new', display_name: 'M BHUVANESWAR' },
        { leetcode_id: 'Manoj_2007', display_name: 'MANOJ SHIVPRASAD S' },
        { leetcode_id: 'nasht123', display_name: 'NATASHA PATNAIK' },
        { leetcode_id: 'navdeep90', display_name: 'NAVDEEP R' },
        { leetcode_id: 'nithishkumar31', display_name: 'NITHISHKUMAR B' },
        { leetcode_id: '2AsN9Z6O5Q', display_name: 'PEBIN JOSEPH A' },
        { leetcode_id: 'Pio_Godwin', display_name: 'PIO GODWIN M' },
        { leetcode_id: 'v_s_poovendhiran ', display_name: 'POOVENDHIRAN V S' },
        { leetcode_id: 'PREETHIKHA_S', display_name: 'PREETHIKHA S' },
        { leetcode_id: 'Prrajan_saravanan', display_name: 'PRRAJAN SARAVANAN' },
        { leetcode_id: 'prabanjanm', display_name: 'PRABANJAN M' },
        { leetcode_id: 'R_KIRTHANA', display_name: 'R KIRTHANA' },
        { leetcode_id: 'ragavi632007', display_name: 'RAGAVI B' },
        { leetcode_id: 'rohithjagan', display_name: 'ROHITH JAGAN' },
        { leetcode_id: 'Sivahari_S', display_name: 'S SIVAHARI' },
        { leetcode_id: 'SaajidAhamed', display_name: 'SAAJID AHAMED' },
        { leetcode_id: 'Safira_Begum', display_name: 'SAFIRA BEGUM A' },
        { leetcode_id: 'kuK41YJxBS', display_name: 'SANJAY S' },
        { leetcode_id: 'sellamuthu2007', display_name: 'SELLAMUTHU R' },
        { leetcode_id: 'senthamizhselvan-sm_cse-N', display_name: 'SENTHAMIZHSELVAN S' },
        { leetcode_id: 'Sreenithi369', display_name: 'SREENITHI R' },
        { leetcode_id: 'SrijaaiM', display_name: 'SRI JAAI MEENAKSHI M' },
        { leetcode_id: 'sukesh-2006', display_name: 'SUKESH M' },
        { leetcode_id: 'barath80', display_name: 'SUNKIREDDY BARATH' },
        { leetcode_id: 'SYLESH_', display_name: 'SYLESH P' },
        { leetcode_id: 'sutharsan07', display_name: 'T P SUTHARSAN' },
        { leetcode_id: 'tharunraaj7', display_name: 'THARUN RAAJ D A' },
        { leetcode_id: 'prannav_cse19', display_name: 'V G PRANNAV' },
        { leetcode_id: 'Rishi1201', display_name: 'V RISHITHARAN' },
        { leetcode_id: 'Vijitha_M', display_name: 'VIJITHA M' }
      ]
      
      console.log('👥 Inserting target users...')
      const { data: insertedUsers, error: usersError } = await supabase
        .from('target_users')
        .upsert(targetUsers, { onConflict: 'leetcode_id' })
        .select()
      
      if (usersError) {
        console.error('Users insertion error:', usersError)
        return res.status(500).json({ 
          error: 'Failed to insert users - tables may not exist yet', 
          details: usersError,
          hint: 'Please run the complete-supabase-setup.sql script in Supabase SQL Editor first'
        })
      }
      
      console.log('✅ Target users inserted/updated')
      
      res.status(200).json({ 
        success: true, 
        message: 'Database setup completed successfully',
        users_inserted: insertedUsers?.length || targetUsers.length,
        next_step: 'Call /api/setup-contest-460 to load Contest 460 data'
      })
      
    } catch (error) {
      console.error('Database setup error:', error)
      res.status(500).json({ error: 'Database setup failed', details: error.message })
    }
  } else {
    res.setHeader('Allow', ['POST'])
    res.status(405).json({ error: 'Method not allowed' })
  }
}
