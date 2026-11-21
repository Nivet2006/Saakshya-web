/**
 * Firebase Firestore Migration & Initialization Script
 * Seeds initial facilities, staff profiles, and beneficiaries into Firestore database `sakshya-aasha`.
 */

import { initializeApp } from 'firebase/app';
import {
  getFirestore,
  collection,
  doc,
  setDoc,
  getDocs,
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

const INITIAL_BENEFICIARIES = [
  {
    id: 'c0000000-0000-0000-0000-000000001042',
    beneficiary_id: 'BEN-1042',
    full_name: 'Lakshmi Devi',
    age_years: 25,
    gender: 'FEMALE',
    category: 'PREGNANT_WOMAN',
    village: 'Rampur Demo Ward 1',
    household_head: 'Mohan Lal',
    phone_number: '+91 90000 01042',
    rch_id: 'RCH-SYNTH-1042',
    lmp_date: '2026-04-05',
    edd_date: '2027-01-10',
    high_risk_status: true,
    high_risk_reasons: ['Prior ANC watch', 'Td-2 pending'],
    assigned_asha_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'hi-IN',
    created_at: '2026-09-10T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'c0000000-0000-0000-0000-000000001043',
    beneficiary_id: 'BEN-1043',
    full_name: 'Kavitha Rao',
    age_years: 27,
    gender: 'FEMALE',
    category: 'LACTATING_MOTHER',
    village: 'Shantinagar Demo Ward 2',
    household_head: 'Srinivas Rao',
    phone_number: '+91 90000 01043',
    rch_id: 'RCH-SYNTH-1043',
    high_risk_status: false,
    high_risk_reasons: [],
    assigned_asha_id: 'prof-anm-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'kn-IN',
    created_at: '2026-08-20T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'c0000000-0000-0000-0000-000000001044',
    beneficiary_id: 'BEN-1044',
    full_name: 'Baby of Kavitha Rao',
    age_years: 0,
    gender: 'MALE',
    category: 'INFANT',
    village: 'Shantinagar Demo Ward 2',
    household_head: 'Srinivas Rao',
    phone_number: '+91 90000 01044',
    rch_id: 'RCH-SYNTH-1044',
    high_risk_status: true,
    high_risk_reasons: ['HBNC Newborn Follow-up'],
    assigned_asha_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'kn-IN',
    created_at: '2026-11-10T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'c0000000-0000-0000-0000-000000001045',
    beneficiary_id: 'BEN-1045',
    full_name: 'Sunita Kumari',
    age_years: 23,
    gender: 'FEMALE',
    category: 'PREGNANT_WOMAN',
    village: 'Rampur Demo Ward 1',
    household_head: 'Rajesh Kumar',
    phone_number: '+91 90000 01045',
    rch_id: 'RCH-SYNTH-1045',
    lmp_date: '2026-05-01',
    edd_date: '2027-02-05',
    high_risk_status: false,
    high_risk_reasons: [],
    assigned_asha_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'hi-IN',
    created_at: '2026-09-25T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'c0000000-0000-0000-0000-000000001046',
    beneficiary_id: 'BEN-1046',
    full_name: 'Meena Selvam',
    age_years: 1,
    gender: 'FEMALE',
    category: 'CHILD',
    village: 'Kaveri Demo Ward 3',
    household_head: 'Selvam K.',
    phone_number: '+91 90000 01046',
    rch_id: 'RCH-SYNTH-1046',
    high_risk_status: false,
    high_risk_reasons: [],
    assigned_asha_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'ta-IN',
    created_at: '2025-11-15T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'c0000000-0000-0000-0000-000000001047',
    beneficiary_id: 'BEN-1047',
    full_name: 'Anita Devi',
    age_years: 26,
    gender: 'FEMALE',
    category: 'PREGNANT_WOMAN',
    village: 'Rampur Demo Ward 2',
    household_head: 'Mahesh Yadav',
    phone_number: '+91 90000 01047',
    rch_id: 'RCH-SYNTH-1047',
    lmp_date: '2026-03-18',
    edd_date: '2026-12-23',
    high_risk_status: false,
    high_risk_reasons: [],
    assigned_asha_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'hi-IN',
    created_at: '2026-08-12T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'c0000000-0000-0000-0000-000000001048',
    beneficiary_id: 'BEN-1048',
    full_name: 'Lakshmi Narayanan',
    age_years: 29,
    gender: 'FEMALE',
    category: 'LACTATING_MOTHER',
    village: 'Kaveri Demo Ward 3',
    household_head: 'Narayanan S.',
    phone_number: '+91 90000 01048',
    rch_id: 'RCH-SYNTH-1048',
    high_risk_status: false,
    high_risk_reasons: [],
    assigned_asha_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'ta-IN',
    created_at: '2026-10-01T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'c0000000-0000-0000-0000-000000001056',
    beneficiary_id: 'BEN-1056',
    full_name: 'Anitha Sharma',
    age_years: 24,
    gender: 'FEMALE',
    category: 'PREGNANT_WOMAN',
    village: 'Rampur Demo Ward 1',
    household_head: 'Vikram Sharma',
    phone_number: '+91 90000 01056',
    rch_id: 'RCH-SYNTH-1056',
    lmp_date: '2026-04-20',
    edd_date: '2027-01-25',
    high_risk_status: false,
    high_risk_reasons: [],
    assigned_asha_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    preferred_language: 'hi-IN',
    created_at: '2026-09-18T08:00:00Z',
    updated_at: new Date().toISOString(),
  },
];

const INITIAL_FOLLOW_UPS = [
  {
    id: '10000000-0000-0000-0000-000000000002',
    beneficiary_uuid: 'c0000000-0000-0000-0000-000000001042',
    beneficiary_id: 'BEN-1042',
    beneficiary_name: 'Lakshmi Devi',
    asha_worker_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    due_date: '2026-12-05',
    task_type: 'Td-2 Vaccination & ANC Checkup',
    action_type: 'vaccination_followup',
    priority: 'HIGH',
    status: 'PENDING',
    notes: 'Schedule Td-2 dose at next VHND session.',
    created_at: new Date().toISOString(),
  },
  {
    id: '10000000-0000-0000-0000-000000000003',
    beneficiary_uuid: 'c0000000-0000-0000-0000-000000001046',
    beneficiary_id: 'BEN-1046',
    beneficiary_name: 'Meena Selvam',
    asha_worker_id: 'prof-asha-01',
    phc_id: 'fac-phc-rampur-01',
    due_date: '2026-11-16',
    task_type: 'MR-1 Measles-Rubella Overdue Immunisation Follow-up',
    action_type: 'vaccination_followup',
    priority: 'HIGH',
    status: 'OVERDUE',
    notes: 'Mother missed previous Anganwadi session.',
    created_at: new Date().toISOString(),
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

    // 3. Beneficiaries
    console.log('👩‍⚕️ Seeding beneficiaries collection into Firebase Firestore...');
    for (const ben of INITIAL_BENEFICIARIES) {
      await setDoc(doc(db, 'beneficiaries', ben.beneficiary_id), ben, { merge: true });
    }
    console.log(`✅ Seeded ${INITIAL_BENEFICIARIES.length} beneficiaries into Firestore.`);

    // 4. Follow-up Tasks
    console.log('📅 Seeding follow_ups collection into Firebase Firestore...');
    for (const fu of INITIAL_FOLLOW_UPS) {
      await setDoc(doc(db, 'follow_ups', fu.id), fu, { merge: true });
    }
    console.log(`✅ Seeded ${INITIAL_FOLLOW_UPS.length} follow-up tasks into Firestore.`);

    // 5. Audit Log initialization
    console.log('📋 Initializing audit_logs collection...');
    const auditEntry = {
      id: `audit-${Date.now()}`,
      action_type: 'MIGRATION_BENEFICIARIES_SEEDED',
      user_id: 'SYSTEM',
      user_role: 'ADMIN',
      target_type: 'DATABASE_FIREBASE',
      details: 'Seeded initial 8 beneficiaries and follow-ups to Firebase Firestore',
      timestamp: new Date().toISOString(),
    };
    await setDoc(doc(db, 'audit_logs', auditEntry.id), auditEntry);
    console.log('✅ Created audit log entry.');

    console.log('\n🎉 Firebase Firestore migration successfully completed!');
    console.log('All beneficiaries, follow-ups, facilities, and staff are now live in Firebase DB.');
    process.exit(0);
  } catch (err) {
    console.error('❌ Migration failed:', err);
    process.exit(1);
  }
}

runMigration();
