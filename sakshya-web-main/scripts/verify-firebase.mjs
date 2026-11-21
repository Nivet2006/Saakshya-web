import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDocs } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyAVS-DrwWQX2Ho3eD_qwk9aU6mNoQksGsg',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'sakshya-aasha.firebaseapp.com',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'sakshya-aasha',
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'sakshya-aasha.firebasestorage.app',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '149471048841',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:149471048841:web:62bcb39a9715243fb34258',
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || 'G-HZRSQ4YK9F',
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

async function verify() {
  console.log('🔍 Checking Firestore live database contents...');
  const benSnap = await getDocs(collection(db, 'beneficiaries'));
  console.log(`Beneficiaries in Firestore (${benSnap.size}):`, benSnap.docs.map(d => `${d.data().beneficiary_id}: ${d.data().full_name}`));

  const fuSnap = await getDocs(collection(db, 'follow_ups'));
  console.log(`Follow-ups in Firestore (${fuSnap.size}):`, fuSnap.docs.map(d => d.data().task_type));

  process.exit(0);
}

verify().catch(e => { console.error(e); process.exit(1); });
