import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { initializeFirestore, getFirestore } from 'firebase/firestore';

export const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyAVS-DrwWQX2Ho3eD_qwk9aU6mNoQksGsg',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'sakshya-aasha.firebaseapp.com',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'sakshya-aasha',
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'sakshya-aasha.firebasestorage.app',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '149471048841',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:149471048841:web:62bcb39a9715243fb34258',
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || 'G-HZRSQ4YK9F',
};

// Initialize Firebase (safely singleton for Next.js SSR & client re-renders)
export const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Use auto-detect long polling to prevent Safari/browser WebKit "Listen/channel access control checks" CORS blocks
export const db = getApps().length > 0
  ? getFirestore(app)
  : initializeFirestore(app, {
      experimentalAutoDetectLongPolling: true,
    });

export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId && firebaseConfig.projectId !== 'demo-project'
);

export async function initAnalytics() {
  if (typeof window !== 'undefined') {
    try {
      const { getAnalytics, isSupported } = await import('firebase/analytics');
      if (await isSupported()) {
        return getAnalytics(app);
      }
    } catch {
      // Ignore in environments where analytics isn't supported
    }
  }
  return null;
}
