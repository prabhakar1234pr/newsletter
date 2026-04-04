import { useState, useEffect, createContext, useContext } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signOut,
  updateProfile,
} from "firebase/auth";
import { auth, googleProvider } from "@/lib/firebase";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Handle redirect result on page load (fires after Google redirect)
    getRedirectResult(auth).catch((err) => {
      console.error("Redirect auth error:", err);
    });

    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
    });
    return unsub;
  }, []);

  const loginWithEmail = (email, password) =>
    signInWithEmailAndPassword(auth, email, password);

  const signupWithEmail = (email, password, name) =>
    createUserWithEmailAndPassword(auth, email, password).then((cred) =>
      updateProfile(cred.user, { displayName: name }).then(() => cred)
    );

  const loginWithGoogle = async () => {
    try {
      // Try popup first; fall back to redirect if blocked
      return await signInWithPopup(auth, googleProvider);
    } catch (err) {
      if (
        err.code === "auth/popup-blocked" ||
        err.code === "auth/popup-closed-by-user" ||
        err.code === "auth/cancelled-popup-request"
      ) {
        return signInWithRedirect(auth, googleProvider);
      }
      throw err;
    }
  };

  const logout = () => signOut(auth);

  const getToken = () => user?.getIdToken();

  return (
    <AuthContext.Provider
      value={{ user, loading, loginWithEmail, signupWithEmail, loginWithGoogle, logout, getToken }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
