import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { getSubscriptions, updateSubscription } from "@/lib/api";
import { Bell, BellOff, Plus, LogOut, Clock, Globe, BookOpen, Zap, Sparkles, History, Trash2 } from "lucide-react";
import { deleteSubscription } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0 },
};

const fadeIn = {
  hidden: { opacity: 0 },
  show:   { opacity: 1 },
};

const TOPIC_ICONS = {
  "AI & Technology":         "⚡",
  "Geopolitics":             "🌍",
  "Cinema":                  "🎬",
  "Sports":                  "🏆",
  "Business & Finance":      "📈",
  "Science & Environment":   "🔬",
  "Health & Wellness":       "🧬",
  "Gaming & Esports":        "🎮",
  "Culture & Entertainment": "🎨",
  "Education & Careers":     "🎓",
};

const TOPIC_COLORS = {
  "AI & Technology":         { from: "#6366F1", to: "#3B82F6" },
  "Geopolitics":             { from: "#10B981", to: "#14B8A6" },
  "Cinema":                  { from: "#F43F5E", to: "#EC4899" },
  "Sports":                  { from: "#F59E0B", to: "#F97316" },
  "Business & Finance":      { from: "#22C55E", to: "#10B981" },
  "Science & Environment":   { from: "#06B6D4", to: "#3B82F6" },
  "Health & Wellness":       { from: "#EC4899", to: "#F43F5E" },
  "Gaming & Esports":        { from: "#8B5CF6", to: "#7C3AED" },
  "Culture & Entertainment": { from: "#F97316", to: "#F59E0B" },
  "Education & Careers":     { from: "#38BDF8", to: "#6366F1" },
};

const DEFAULT_COLOR = { from: "#6366F1", to: "#3B82F6" };

export default function Dashboard() {
  const { user, logout, getToken } = useAuth();
  const navigate = useNavigate();

  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading]             = useState(true);
  const [toggling, setToggling]           = useState(null);
  const [deleting, setDeleting]           = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const token = await getToken();
        const data  = await getSubscriptions(token);
        setSubscriptions(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, [getToken]);

  const toggleActive = async (sub) => {
    setToggling(sub.id);
    try {
      const token = await getToken();
      await updateSubscription(token, sub.id, { is_active: !sub.is_active });
      setSubscriptions((prev) =>
        prev.map((s) => (s.id === sub.id ? { ...s, is_active: !s.is_active } : s))
      );
    } catch (err) {
      console.error(err);
    } finally {
      setToggling(null);
    }
  };

  const handleDelete = async (id) => {
    setDeleting(id);
    try {
      const token = await getToken();
      await deleteSubscription(token, id);
      setSubscriptions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      console.error(err);
    } finally {
      setDeleting(null);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const initials = (user?.displayName || user?.email || "U")
    .split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);

  const activeCount = subscriptions.filter((s) => s.is_active).length;

  return (
    <div style={{ minHeight: "100vh", background: "#F8FAFF", fontFamily: "'Inter', system-ui, sans-serif", color: "#0F172A" }}>

      {/* ── Nav ─────────────────────────────────────────────── */}
      <motion.nav
        initial="hidden" animate="show" variants={fadeIn} transition={{ duration: 0.4 }}
        style={{ position: "sticky", top: 0, zIndex: 50, background: "rgba(248,250,255,0.88)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(0,0,0,0.07)" }}
      >
        <div style={{ maxWidth: "960px", margin: "0 auto", padding: "0 24px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link to="/" style={{ display: "flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
            <div style={{ height: "32px", width: "32px", borderRadius: "8px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 12px rgba(99,102,241,0.3)" }}>
              <Zap style={{ height: "15px", width: "15px", color: "#fff" }} />
            </div>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "17px", color: "#0F172A" }}>AI Newsletter</span>
          </Link>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "13px", color: "#94A3B8", maxWidth: "180px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {user?.displayName || user?.email}
            </span>
            <div style={{ height: "32px", width: "32px", borderRadius: "50%", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "12px", fontWeight: 700, flexShrink: 0 }}>
              {initials}
            </div>
            <motion.button
              onClick={handleLogout}
              whileHover={{ color: "#0F172A" }}
              title="Sign out"
              style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8", padding: "6px", display: "flex", borderRadius: "8px" }}
            >
              <LogOut style={{ height: "16px", width: "16px" }} />
            </motion.button>
          </div>
        </div>
      </motion.nav>

      <div style={{ maxWidth: "960px", margin: "0 auto", padding: "40px 24px" }}>

        {/* ── Page header ─────────────────────────────────── */}
        <motion.div
          initial="hidden" animate="show"
          variants={{ show: { transition: { staggerChildren: 0.1 } } }}
          style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "28px" }}
        >
          <motion.div variants={fadeUp} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
            <h1 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.75rem", color: "#0F172A", letterSpacing: "-0.02em", marginBottom: "4px" }}>
              Your briefs
            </h1>
            <p style={{ fontSize: "14px", color: "#94A3B8" }}>
              {loading ? "Loading…" : `${subscriptions.length} newsletter${subscriptions.length !== 1 ? "s" : ""} · ${activeCount} active`}
            </p>
          </motion.div>

          <motion.div variants={fadeUp} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
            <Link to="/onboarding" style={{ textDecoration: "none" }}>
              <motion.div
                whileHover={{ scale: 1.03, boxShadow: "0 8px 24px rgba(99,102,241,0.45)" }}
                whileTap={{ scale: 0.97 }}
                style={{ display: "inline-flex", alignItems: "center", gap: "7px", padding: "10px 18px", borderRadius: "10px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "14px", fontWeight: 600, boxShadow: "0 4px 14px rgba(99,102,241,0.35)", cursor: "pointer" }}
              >
                <Plus style={{ height: "15px", width: "15px" }} />
                Add topic
              </motion.div>
            </Link>
          </motion.div>
        </motion.div>

        {/* ── Stats strip ─────────────────────────────────── */}
        {!loading && subscriptions.length > 0 && (
          <motion.div
            initial="hidden" animate="show"
            variants={{ show: { transition: { staggerChildren: 0.08 } } }}
            style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "12px", marginBottom: "32px" }}
          >
            {[
              { label: "Active briefs",  value: activeCount,           icon: Sparkles },
              { label: "Topics covered", value: subscriptions.length,  icon: Globe },
              { label: "Next delivery",  value: "Tomorrow",            icon: Clock },
            ].map(({ label, value, icon: Icon }) => (
              <motion.div
                key={label}
                variants={fadeUp}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                style={{ borderRadius: "14px", background: "#fff", border: "1px solid rgba(0,0,0,0.07)", padding: "16px 18px", display: "flex", alignItems: "center", gap: "12px", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}
              >
                <div style={{ height: "36px", width: "36px", borderRadius: "10px", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.14)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Icon style={{ height: "16px", width: "16px", color: "#6366F1" }} />
                </div>
                <div>
                  <div style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.3rem", color: "#0F172A", lineHeight: 1 }}>{value}</div>
                  <div style={{ fontSize: "12px", color: "#94A3B8", marginTop: "3px" }}>{label}</div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* ── Content ─────────────────────────────────────── */}
        {loading ? (
          <LoadingSkeleton />
        ) : subscriptions.length === 0 ? (
          <EmptyState />
        ) : (
          <motion.div
            initial="hidden" animate="show"
            variants={{ show: { transition: { staggerChildren: 0.07 } } }}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}
          >
            {subscriptions.map((sub, i) => (
              <SubscriptionCard
                key={sub.id}
                sub={sub}
                index={i}
                toggling={toggling === sub.id}
                onToggle={() => toggleActive(sub)}
                deleting={deleting === sub.id}
                onDelete={() => handleDelete(sub.id)}
              />
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
}

function SubscriptionCard({ sub, toggling, onToggle, deleting, onDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const colors = TOPIC_COLORS[sub.topic] || DEFAULT_COLOR;
  const icon   = TOPIC_ICONS[sub.topic] || "📰";

  return (
    <motion.div
      variants={fadeUp}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -3, boxShadow: "0 12px 32px rgba(0,0,0,0.09)", transition: { duration: 0.2 } }}
      layout
      style={{ borderRadius: "16px", background: "#fff", border: "1px solid rgba(0,0,0,0.07)", overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,0.05)" }}
    >
      {/* Top accent bar */}
      <div style={{ height: "3px", background: `linear-gradient(90deg, ${colors.from}, ${colors.to})` }} />

      <div style={{ padding: "20px" }}>
        {/* Title row */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ height: "42px", width: "42px", borderRadius: "12px", background: `linear-gradient(135deg, ${colors.from}, ${colors.to})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "18px", flexShrink: 0 }}>
              {icon}
            </div>
            <div>
              <h3 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "15px", color: "#0F172A", lineHeight: 1.3 }}>{sub.topic}</h3>
              {sub.sub_genre && (
                <span style={{ fontSize: "12px", color: "#6366F1", marginTop: "2px", display: "block" }}>{sub.sub_genre}</span>
              )}
            </div>
          </div>
          <span style={{
            fontSize: "11px", fontWeight: 600, padding: "3px 10px", borderRadius: "999px", flexShrink: 0,
            background: sub.is_active ? "rgba(16,185,129,0.1)" : "rgba(0,0,0,0.05)",
            color:      sub.is_active ? "#059669"              : "#94A3B8",
            border:     `1px solid ${sub.is_active ? "rgba(16,185,129,0.2)" : "rgba(0,0,0,0.08)"}`,
          }}>
            {sub.is_active ? "Active" : "Paused"}
          </span>
        </div>

        {/* Meta row */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12px", color: "#94A3B8" }}>
            <Clock style={{ height: "13px", width: "13px" }} />
            {String(sub.delivery_hour ?? 0).padStart(2, "0")}:{String(sub.delivery_minute ?? 0).padStart(2, "0")} daily
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12px", color: "#94A3B8" }}>
            <Globe style={{ height: "13px", width: "13px" }} />
            {sub.timezone.split("/")[1]?.replace("_", " ") || sub.timezone}
          </span>
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: "8px", paddingTop: "14px", borderTop: "1px solid rgba(0,0,0,0.06)" }}>

          {/* History */}
          <Link to={`/history/${sub.id}`} style={{ flex: 1, textDecoration: "none" }}>
            <motion.button
              whileHover={{ background: "#F1F5F9" }}
              style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", height: "36px", borderRadius: "8px", background: "#F8FAFF", border: "1px solid rgba(0,0,0,0.07)", fontSize: "13px", fontWeight: 500, color: "#64748B", cursor: "pointer" }}
            >
              <History style={{ height: "13px", width: "13px" }} />
              History
            </motion.button>
          </Link>

          {/* Pause / Resume */}
          <motion.button
            onClick={onToggle}
            disabled={toggling}
            whileHover={!toggling ? { scale: 1.02 } : {}}
            whileTap={!toggling ? { scale: 0.97 } : {}}
            style={{
              flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
              height: "36px", borderRadius: "8px", fontSize: "13px", fontWeight: 600,
              cursor: toggling ? "not-allowed" : "pointer", opacity: toggling ? 0.6 : 1,
              background: sub.is_active ? "#fff" : "linear-gradient(135deg,#6366F1,#3B82F6)",
              border: sub.is_active ? "1px solid rgba(0,0,0,0.1)" : "none",
              color: sub.is_active ? "#374151" : "#fff",
              boxShadow: sub.is_active ? "none" : "0 2px 10px rgba(99,102,241,0.3)",
            }}
          >
            {toggling ? "…" : sub.is_active
              ? <><BellOff style={{ height: "13px", width: "13px" }} />Pause</>
              : <><Bell style={{ height: "13px", width: "13px" }} />Resume</>
            }
          </motion.button>

          {/* Delete */}
          <motion.button
            onClick={() => setConfirmDelete(true)}
            whileHover={{ background: "rgba(239,68,68,0.07)" }}
            whileTap={{ scale: 0.95 }}
            title="Delete subscription"
            style={{ height: "36px", width: "36px", borderRadius: "8px", background: "#F8FAFF", border: "1px solid rgba(0,0,0,0.07)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 }}
          >
            <Trash2 style={{ height: "14px", width: "14px", color: "#94A3B8" }} />
          </motion.button>
        </div>

        {/* Inline delete confirmation */}
        <AnimatePresence>
          {confirmDelete && (
            <motion.div
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: "auto", marginTop: "12px" }}
              exit={{ opacity: 0, height: 0, marginTop: 0 }}
              transition={{ duration: 0.2 }}
              style={{ overflow: "hidden" }}
            >
              <div style={{ background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.15)", borderRadius: "10px", padding: "12px 14px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
                <span style={{ fontSize: "13px", color: "#DC2626", fontWeight: 500 }}>
                  Delete this subscription?
                </span>
                <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                  <motion.button
                    onClick={() => setConfirmDelete(false)}
                    whileHover={{ background: "#F1F5F9" }}
                    style={{ padding: "5px 12px", borderRadius: "7px", background: "#fff", border: "1px solid rgba(0,0,0,0.1)", fontSize: "12px", fontWeight: 500, color: "#64748B", cursor: "pointer" }}
                  >
                    Cancel
                  </motion.button>
                  <motion.button
                    onClick={() => { setConfirmDelete(false); onDelete(); }}
                    disabled={deleting}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    style={{ padding: "5px 12px", borderRadius: "7px", background: "#EF4444", border: "none", fontSize: "12px", fontWeight: 600, color: "#fff", cursor: "pointer", opacity: deleting ? 0.6 : 1 }}
                  >
                    {deleting ? "Deleting…" : "Delete"}
                  </motion.button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} style={{ borderRadius: "16px", background: "#fff", border: "1px solid rgba(0,0,0,0.07)", overflow: "hidden" }}>
          <div style={{ height: "3px", background: "linear-gradient(90deg, #E2E8F0, #F1F5F9)" }} />
          <div style={{ padding: "20px" }}>
            <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
              <div style={{ height: "42px", width: "42px", borderRadius: "12px", background: "#F1F5F9", flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ height: "14px", background: "#F1F5F9", borderRadius: "6px", marginBottom: "8px", width: "60%" }} />
                <div style={{ height: "11px", background: "#F8FAFF", borderRadius: "6px", width: "40%" }} />
              </div>
            </div>
            <div style={{ height: "11px", background: "#F8FAFF", borderRadius: "6px", width: "50%", marginBottom: "16px" }} />
            <div style={{ height: "36px", background: "#F8FAFF", borderRadius: "8px" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      style={{ textAlign: "center", padding: "80px 24px" }}
    >
      <div style={{ display: "flex", justifyContent: "center", marginBottom: "24px" }}>
        <div style={{ position: "relative" }}>
          <div style={{ height: "80px", width: "80px", borderRadius: "20px", background: "rgba(99,102,241,0.07)", border: "1px solid rgba(99,102,241,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <BookOpen style={{ height: "36px", width: "36px", color: "#6366F1" }} />
          </div>
          <div style={{ position: "absolute", top: "-4px", right: "-4px", height: "22px", width: "22px", borderRadius: "50%", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Sparkles style={{ height: "11px", width: "11px", color: "#fff" }} />
          </div>
        </div>
      </div>

      <h2 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.3rem", color: "#0F172A", marginBottom: "8px" }}>
        Your briefs live here.
      </h2>
      <p style={{ fontSize: "14px", color: "#94A3B8", marginBottom: "28px", maxWidth: "280px", margin: "0 auto 28px", lineHeight: 1.6 }}>
        Add your first topic and get AI-curated intelligence every morning.
      </p>

      <Link to="/onboarding" style={{ textDecoration: "none" }}>
        <motion.div
          whileHover={{ scale: 1.03, boxShadow: "0 8px 24px rgba(99,102,241,0.4)" }}
          whileTap={{ scale: 0.97 }}
          style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "12px 22px", borderRadius: "12px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "15px", fontWeight: 600, boxShadow: "0 4px 14px rgba(99,102,241,0.3)", cursor: "pointer" }}
        >
          <Plus style={{ height: "16px", width: "16px" }} />
          Create your first brief
        </motion.div>
      </Link>
    </motion.div>
  );
}
