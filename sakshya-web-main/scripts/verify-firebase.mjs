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
  console.log('🔍 Reading back from Firebase Firestore...');
  const facSnap = await getDocs(collection(db, 'facilities'));
  console.log(`Facilities found (${facSnap.size}):`, facSnap.docs.map(d => d.data().name));

  const profSnap = await getDocs(collection(db, 'user_profiles'));
  console.log(`User profiles found (${profSnap.size}):`, profSnap.docs.map(d => `${d.data().full_name} (${d.data().role})`));

  const auditSnap = await getDocs(collection(db, 'audit_logs'));
  console.log(`Audit logs found (${auditSnap.size}):`, auditSnap.docs.map(d => d.data().action_type));

  console.log('✨ All Firestore read verifications passed successfully!');
  process.exit(0);
}

verify().catch(err => {
  console.error('Verification failed:', err);
  process.exit(1);
});
