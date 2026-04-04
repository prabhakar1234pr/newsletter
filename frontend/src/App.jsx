import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import History from "@/pages/History";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnlyRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <img
        src="/logo.png"
        alt="AI Newsletter"
        className="h-8 w-8 opacity-40 animate-pulse"
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/login"
            element={<PublicOnlyRoute><Login /></PublicOnlyRoute>}
          />
          <Route
            path="/signup"
            element={<PublicOnlyRoute><Signup /></PublicOnlyRoute>}
          />
          <Route
            path="/onboarding"
            element={<ProtectedRoute><Onboarding /></ProtectedRoute>}
          />
          <Route
            path="/dashboard"
            element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
          />
          <Route
            path="/history/:subscriptionId"
            element={<ProtectedRoute><History /></ProtectedRoute>}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
