import { createClient as createSupabaseClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

export const isRealSupabaseConfigured =
  supabaseUrl.startsWith('https://') &&
  !supabaseUrl.includes('YOUR_PROJECT_REF') &&
  !supabaseUrl.includes('placeholder-project') &&
  supabaseAnonKey.length > 20 &&
  !supabaseAnonKey.includes('YOUR_SUPABASE_');

export const supabase: SupabaseClient | null = isRealSupabaseConfigured
  ? createSupabaseClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
      },
    })
  : null;
