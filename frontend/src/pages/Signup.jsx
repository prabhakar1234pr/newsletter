import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Zap, Eye, EyeOff, Sparkles, Clock, Globe } from "lucide-react";
import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0 },
};

const fadeIn = {
  hidden: { opacity: 0 },
  show:   { opacity: 1 },
};

const BRAND_BULLETS = [
  { icon: Sparkles, text: "AI reads many sources, writes 1 perfect brief" },
  { icon: Clock,    text: "Delivered at your exact time, in your timezone" },
  { icon: Globe,    text: "307 topics — pick exactly what you care about" },
];

const PREVIEW_CARDS = [
  { tag: "SPACE",   color: "#8B5CF6", headline: "NASA's Artemis III Moon Landing Window Set",   date: "Apr 22" },
  { tag: "FILM",    color: "#EC4899", headline: "Cannes 2025 Lineup Stirs Early Controversy",   date: "Apr 22" },
  { tag: "FINANCE", color: "#F59E0B", headline: "Fed Signals Rate Pause Amid Inflation Data",   date: "Apr 22" },
];

const inputStyle = {
  width: "100%",
  height: "46px",
  borderRadius: "11px",
  border: "1px solid rgba(0,0,0,0.12)",
  padding: "0 14px",
  fontSize: "14px",
  color: "#0F172A",
  background: "#fff",
  outline: "none",
  boxSizing: "border-box",
  transition: "border-color 0.2s, box-shadow 0.2s",
};

export default function Signup() {
  const { signupWithEmail, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const handleEmail = async (e) => {
    e.preventDefault();
    if (password.length < 6) { setError("Password must be at least 6 characters."); return; }
    setError("");
    setLoading(true);
    try {
      await signupWithEmail(email, password, name);
      navigate("/onboarding");
    } catch (err) {
      setError(friendlyError(err.code));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setError("");
    try {
      const result = await loginWithGoogle();
      if (result) navigate("/onboarding");
    } catch (err) {
      setError(friendlyError(err.code));
    }
  };

  const focusStyle  = (e) => { e.target.style.borderColor = "#6366F1"; e.target.style.boxShadow = "0 0 0 3px rgba(99,102,241,0.1)"; };
  const blurStyle   = (e) => { e.target.style.borderColor = "rgba(0,0,0,0.12)"; e.target.style.boxShadow = "none"; };

  return (
    <div style={{ minHeight: "100vh", background: "#F8FAFF", display: "flex", fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* ── Left brand panel ─────────────────────────────── */}
      <div
        className="lg-panel"
        style={{ display: "none", width: "45%", background: "#fff", borderRight: "1px solid rgba(0,0,0,0.07)", padding: "48px", flexDirection: "column", justifyContent: "space-between", position: "relative", overflow: "hidden" }}
      >
        {/* Bg blobs */}
        <div style={{ position: "absolute", top: "-80px", left: "-60px", width: "380px", height: "380px", borderRadius: "50%", background: "radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 60%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "5%", right: "-60px", width: "320px", height: "320px", borderRadius: "50%", background: "radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 60%)", pointerEvents: "none" }} />

        {/* Logo */}
        <motion.div initial="hidden" animate="show" variants={fadeIn} transition={{ duration: 0.5 }} style={{ position: "relative" }}>
          <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
            <div style={{ height: "36px", width: "36px", borderRadius: "10px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 14px rgba(99,102,241,0.3)" }}>
              <Zap style={{ height: "18px", width: "18px", color: "#fff" }} />
            </div>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "18px", color: "#0F172A" }}>AI Newsletter</span>
          </Link>
        </motion.div>

        {/* Tagline + bullets + cards */}
        <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.1 } } }} style={{ position: "relative" }}>
          <motion.h2 variants={fadeUp} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "2.4rem", color: "#0F172A", lineHeight: 1.15, marginBottom: "8px", letterSpacing: "-0.02em" }}>
            Start every morning
          </motion.h2>
          <motion.p variants={fadeUp} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "2.4rem", color: "#4F7CFF", lineHeight: 1.15, marginBottom: "36px", letterSpacing: "-0.02em" }}>
            one step ahead.
          </motion.p>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "40px" }}>
            {BRAND_BULLETS.map(({ icon: Icon, text }, i) => (
              <motion.div key={text} variants={fadeUp} transition={{ duration: 0.5, delay: i * 0.05 }}
                style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ height: "34px", width: "34px", borderRadius: "10px", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.15)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Icon style={{ height: "15px", width: "15px", color: "#6366F1" }} />
                </div>
                <span style={{ fontSize: "14px", color: "#64748B" }}>{text}</span>
              </motion.div>
            ))}
          </div>

          {/* Mini card stack */}
          <div style={{ position: "relative", height: "200px" }}>
            {PREVIEW_CARDS.map((c, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1 - i * 0.22, y: 0 }}
                transition={{ delay: 0.7 + i * 0.12, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                style={{
                  position: "absolute",
                  top: i * 56,
                  left: i * 18,
                  right: -(i * 18),
                  background: "#fff",
                  borderRadius: "12px",
                  padding: "14px 16px",
                  border: "1px solid rgba(0,0,0,0.07)",
                  boxShadow: "0 4px 16px rgba(0,0,0,0.06)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
                  <span style={{ background: c.color, color: "#fff", fontSize: "9px", fontWeight: 700, padding: "2px 7px", borderRadius: "5px", letterSpacing: "0.04em", flexShrink: 0 }}>{c.tag}</span>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "#0F172A", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.headline}</span>
                </div>
                <span style={{ fontSize: "11px", color: "#CBD5E1", flexShrink: 0 }}>{c.date}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <p style={{ fontSize: "12px", color: "#CBD5E1", position: "relative" }}>© {new Date().getFullYear()} AI Newsletter · Free forever</p>
      </div>

      {/* ── Right form panel ─────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "32px" }}>
        <motion.div
          initial="hidden"
          animate="show"
          variants={{ show: { transition: { staggerChildren: 0.09 } } }}
          style={{ width: "100%", maxWidth: "400px" }}
        >

          {/* Logo */}
          <motion.div variants={fadeIn} transition={{ duration: 0.4 }} style={{ marginBottom: "36px" }}>
            <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
              <div style={{ height: "34px", width: "34px", borderRadius: "9px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Zap style={{ height: "16px", width: "16px", color: "#fff" }} />
              </div>
              <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "17px", color: "#0F172A" }}>AI Newsletter</span>
            </Link>
          </motion.div>

          {/* Heading */}
          <motion.div variants={fadeUp} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} style={{ marginBottom: "28px" }}>
            <h1 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.75rem", color: "#0F172A", marginBottom: "6px", letterSpacing: "-0.02em" }}>
              Create your account
            </h1>
            <p style={{ fontSize: "14px", color: "#94A3B8" }}>Free forever · No credit card required</p>
          </motion.div>

          {/* Google */}
          <motion.div variants={fadeUp} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
            <motion.button
              onClick={handleGoogle}
              whileHover={{ boxShadow: "0 4px 16px rgba(0,0,0,0.1)", y: -1 }}
              whileTap={{ scale: 0.98 }}
              style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", height: "46px", borderRadius: "12px", background: "#fff", border: "1px solid rgba(0,0,0,0.12)", fontSize: "14px", fontWeight: 600, color: "#0F172A", cursor: "pointer", marginBottom: "20px" }}
            >
              <GoogleIcon />
              Continue with Google
            </motion.button>
          </motion.div>

          {/* Divider */}
          <motion.div variants={fadeIn} transition={{ duration: 0.4 }}
            style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px" }}>
            <div style={{ flex: 1, height: "1px", background: "rgba(0,0,0,0.08)" }} />
            <span style={{ fontSize: "12px", color: "#CBD5E1", whiteSpace: "nowrap" }}>or continue with email</span>
            <div style={{ flex: 1, height: "1px", background: "rgba(0,0,0,0.08)" }} />
          </motion.div>

          {/* Form */}
          <motion.form variants={{ show: { transition: { staggerChildren: 0.07 } } }} onSubmit={handleEmail}>

            <motion.div variants={fadeUp} transition={{ duration: 0.5 }} style={{ marginBottom: "14px" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 500, color: "#374151", marginBottom: "6px" }}>Full name</label>
              <input
                type="text"
                placeholder="Your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                style={inputStyle}
                onFocus={focusStyle}
                onBlur={blurStyle}
              />
            </motion.div>

            <motion.div variants={fadeUp} transition={{ duration: 0.5 }} style={{ marginBottom: "14px" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 500, color: "#374151", marginBottom: "6px" }}>Email</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={inputStyle}
                onFocus={focusStyle}
                onBlur={blurStyle}
              />
            </motion.div>

            <motion.div variants={fadeUp} transition={{ duration: 0.5 }} style={{ marginBottom: "20px" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 500, color: "#374151", marginBottom: "6px" }}>Password</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showPw ? "text" : "password"}
                  placeholder="Min. 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  style={{ ...inputStyle, paddingRight: "42px" }}
                  onFocus={focusStyle}
                  onBlur={blurStyle}
                />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  style={{ position: "absolute", right: "12px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "#94A3B8", padding: "4px", display: "flex" }}>
                  {showPw ? <EyeOff style={{ height: "16px", width: "16px" }} /> : <Eye style={{ height: "16px", width: "16px" }} />}
                </button>
              </div>
            </motion.div>

            {error && (
              <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                style={{ background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)", color: "#DC2626", fontSize: "13px", padding: "10px 14px", borderRadius: "10px", marginBottom: "16px" }}>
                {error}
              </motion.div>
            )}

            <motion.div variants={fadeUp} transition={{ duration: 0.5 }}>
              <motion.button
                type="submit"
                disabled={loading}
                whileHover={!loading ? { scale: 1.02, boxShadow: "0 8px 24px rgba(99,102,241,0.45)" } : {}}
                whileTap={!loading ? { scale: 0.98 } : {}}
                style={{ width: "100%", height: "46px", borderRadius: "12px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "15px", fontWeight: 600, border: "none", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, boxShadow: "0 4px 16px rgba(99,102,241,0.35)", transition: "opacity 0.2s" }}
              >
                {loading ? "Creating account…" : "Create account"}
              </motion.button>
            </motion.div>
          </motion.form>

          <motion.p variants={fadeIn} transition={{ duration: 0.4, delay: 0.5 }}
            style={{ textAlign: "center", fontSize: "14px", color: "#94A3B8", marginTop: "24px" }}>
            Already have an account?{" "}
            <Link to="/login" style={{ color: "#6366F1", fontWeight: 600, textDecoration: "none" }}>
              Sign in
            </Link>
          </motion.p>

        </motion.div>
      </div>

      <style>{`
        @media (min-width: 1024px) {
          .lg-panel { display: flex !important; }
        }
      `}</style>

    </div>
  );
}

function GoogleIcon() {
  return (
    <svg style={{ height: "18px", width: "18px", flexShrink: 0 }} viewBox="0 0 24 24">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}

function friendlyError(code) {
  const map = {
    "auth/email-already-in-use": "An account with this email already exists.",
    "auth/invalid-email":        "Invalid email address.",
    "auth/weak-password":        "Password is too weak.",
  };
  return map[code] || "Something went wrong. Please try again.";
}
