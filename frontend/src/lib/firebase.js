import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const apiKey = import.meta.env.VITE_FIREBASE_API_KEY;
const appId = import.meta.env.VITE_FIREBASE_APP_ID;

if (!apiKey || apiKey === "PASTE_FROM_FIREBASE_CONSOLE") {
  throw new Error(
    "Missing VITE_FIREBASE_API_KEY in frontend/.env\n" +
    "Go to https://console.firebase.google.com → ai-newsletter-2026 → Project Settings → Your apps → Web app → copy apiKey"
  );
}

// Firebase config — populated from environment variables
const firebaseConfig = {
  apiKey,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId,
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export default app;
