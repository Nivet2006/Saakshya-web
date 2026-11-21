/**
 * Firebase Firestore Migration & Initialization Script
 * Sets up collections and initializes staff/facility records for Sakshya ASHA Field Register.
 */

import { initializeApp } from 'firebase/app';
import {
  getFirestore,
  collection,
  doc,
  setDoc,
  getDocs,
  deleteDoc,
} from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyAVS-DrwWQX2Ho3eD_qwk9aU6mNoQksGsg',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'sakshya-aasha.firebaseapp.com',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'sakshya-aasha',
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'sakshya-aasha.firebasestorage.app',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '149471048841',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:149471048841:web:62bcb39a9715243fb34258',
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || 'G-HZRSQ4YK9F',
};

console.log('🚀 Starting Firebase Firestore Migration for project:', firebaseConfig.projectId);

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

const INITIAL_FACILITIES = [
  {
    id: 'fac-phc-rampur-01',
    code: 'PHC-RAMPUR-01',
    name: 'Rampur Primary Health Centre',
    facility_type: 'PHC',
    district: 'Varanasi',
    state: 'Uttar Pradesh',
    pincode: '221005',
    contact_phone: '+91 542 2230001',
    emergency_transport_phone: '108',
    created_at: new Date().toISOString(),
  },
  {
    id: 'fac-chc-shantinagar-01',
    code: 'CHC-SHANTINAGAR-01',
    name: 'Shantinagar Community Health Centre (FRU)',
    facility_type: 'CHC',
    district: 'Mandya',
    state: 'Karnataka',
    pincode: '571401',
    contact_phone: '+91 823 2240002',
    emergency_transport_phone: '108',
    created_at: new Date().toISOString(),
  },
];

const INITIAL_PROFILES = [
  {
    id: 'prof-asha-01',
    worker_code: 'ASHA-DEMO-01',
    role: 'ASHA_WORKER',
    full_name: 'Sunita Verma',
    phone_number: '+91 98765 00101',
    phc_id: 'fac-phc-rampur-01',
    phc_name: 'Rampur Primary Health Centre',
    assigned_area: 'Rampur Ward 1 & 2',
    preferred_language: 'hi-IN',
    is_active: true,
    is_online: true,
    last_active_at: new Date().toISOString(),
  },
  {
    id: 'prof-anm-01',
    worker_code: 'ANM-DEMO-01',
    role: 'PHC_SUPERVISOR',
    full_name: 'Padma Murthy',
    phone_number: '+91 98765 00102',
    phc_id: 'fac-phc-rampur-01',
    phc_name: 'Rampur Primary Health Centre',
    assigned_area: 'Rampur Sector A',
    preferred_language: 'kn-IN',
    is_active: true,
    is_online: true,
    last_active_at: new Date().toISOString(),
  },
  {
    id: 'prof-moic-01',
    worker_code: 'DOC-DEMO-01',
    role: 'PHC_SUPERVISOR',
    full_name: 'Dr. Sunita Rao (MOIC)',
    phone_number: '+91 98765 00103',
    phc_id: 'fac-phc-rampur-01',
    phc_name: 'Rampur Primary Health Centre',
    assigned_area: 'Rampur PHC Command Center',
    preferred_language: 'hi-IN',
    is_active: true,
    is_online: true,
    last_active_at: new Date().toISOString(),
  },
];

async function runMigration() {
  try {
    // 1. Facilities
    console.log('📦 Migrating facilities collection...');
    for (const fac of INITIAL_FACILITIES) {
      await setDoc(doc(db, 'facilities', fac.id), fac, { merge: true });
    }
    console.log(`✅ Seeded ${INITIAL_FACILITIES.length} facilities.`);

    // 2. User Profiles
    console.log('👤 Migrating user_profiles collection...');
    for (const prof of INITIAL_PROFILES) {
      await setDoc(doc(db, 'user_profiles', prof.id), prof, { merge: true });
    }
    console.log(`✅ Seeded ${INITIAL_PROFILES.length} staff user profiles.`);

    // 3. Audit Log initialization
    console.log('📋 Initializing audit_logs collection...');
    const auditEntry = {
      id: `audit-${Date.now()}`,
      action_type: 'MIGRATION_INITIALIZED',
      user_id: 'SYSTEM',
      user_role: 'ADMIN',
      target_type: 'DATABASE_FIREBASE',
      details: 'Firebase Firestore migration completed for sakshya-aasha',
      timestamp: new Date().toISOString(),
    };
    await setDoc(doc(db, 'audit_logs', auditEntry.id), auditEntry);
    console.log('✅ Created initial audit log entry.');

    console.log('\n🎉 Firebase Firestore migration successfully completed!');
    console.log('Database is ready with:');
    console.log(' - facilities');
    console.log(' - user_profiles');
    console.log(' - beneficiaries (ready for dynamic registration)');
    console.log(' - visits (ready for voice visits)');
    console.log(' - follow_ups');
    console.log(' - danger_alerts');
    console.log(' - audit_logs');
    process.exit(0);
  } catch (err) {
    console.error('❌ Migration failed:', err);
    process.exit(1);
  }
}

runMigration();
