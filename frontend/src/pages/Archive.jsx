import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { getEditions } from "@/lib/api";
import { ArrowLeft, ExternalLink, Calendar, Inbox, Zap, Sparkles, Mail } from "lucide-react";
import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0 },
};

const fadeIn = {
  hidden: { opacity: 0 },
  show:   { opacity: 1 },
};

export default function Archive() {
  const { subscriptionId } = useParams();
  const { getToken } = useAuth();

  const [editions, setEditions] = useState([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const token = await getToken();
        const data  = await getEditions(token, subscriptionId);
        setEditions(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, [subscriptionId, getToken]);

  return (
    <div style={{ minHeight: "100vh", background: "#F8FAFF", fontFamily: "'Inter', system-ui, sans-serif", color: "#0F172A" }}>

      {/* ── Nav ─────────────────────────────────────────────── */}
      <motion.nav
        initial="hidden" animate="show" variants={fadeIn} transition={{ duration: 0.4 }}
        style={{ position: "sticky", top: 0, zIndex: 50, background: "rgba(248,250,255,0.88)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(0,0,0,0.07)" }}
      >
        <div style={{ maxWidth: "720px", margin: "0 auto", padding: "0 24px", height: "64px", display: "flex", alignItems: "center", gap: "12px" }}>
          <Link to="/dashboard" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "34px", width: "34px", borderRadius: "8px", background: "#fff", border: "1px solid rgba(0,0,0,0.09)", textDecoration: "none", flexShrink: 0 }}>
            <ArrowLeft style={{ height: "15px", width: "15px", color: "#64748B" }} />
          </Link>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ height: "30px", width: "30px", borderRadius: "8px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 3px 10px rgba(99,102,241,0.3)" }}>
              <Zap style={{ height: "14px", width: "14px", color: "#fff" }} />
            </div>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "15px", color: "#0F172A" }}>AI Newsletter</span>
            <span style={{ color: "#CBD5E1", fontSize: "15px" }}>/</span>
            <span style={{ fontSize: "14px", color: "#94A3B8" }}>Archive</span>
          </div>
        </div>
      </motion.nav>

      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "40px 24px" }}>

        {/* ── Header ─────────────────────────────────────────── */}
        <motion.div
          initial="hidden" animate="show"
          variants={{ show: { transition: { staggerChildren: 0.1 } } }}
          style={{ marginBottom: "36px" }}
        >
          <motion.h1
            variants={fadeUp} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.75rem", color: "#0F172A", letterSpacing: "-0.02em", marginBottom: "4px" }}
          >
            Past editions
          </motion.h1>
          <motion.p variants={fadeUp} transition={{ duration: 0.5 }} style={{ fontSize: "14px", color: "#94A3B8" }}>
            {loading ? "Loading…" : `${editions.length} edition${editions.length !== 1 ? "s" : ""} delivered`}
          </motion.p>
        </motion.div>

        {/* ── Content ─────────────────────────────────────────── */}
        {loading ? (
          <LoadingSkeleton />
        ) : editions.length === 0 ? (
          <EmptyState />
        ) : (
          <TimelineList editions={editions} />
        )}
      </div>
    </div>
  );
}

function TimelineList({ editions }) {
  return (
    <div style={{ position: "relative" }}>
      {/* Vertical timeline line */}
      <div style={{
        position: "absolute",
        left: "15px",
        top: "20px",
        bottom: "20px",
        width: "2px",
        background: "linear-gradient(to bottom, rgba(99,102,241,0.4), rgba(99,102,241,0.05) 80%, transparent)",
        borderRadius: "999px",
      }} />

      <motion.div
        initial="hidden" animate="show"
        variants={{ show: { transition: { staggerChildren: 0.07 } } }}
        style={{ display: "flex", flexDirection: "column", gap: "16px" }}
      >
        {editions.map((edition, i) => (
          <EditionCard key={edition.id} edition={edition} index={i} />
        ))}
      </motion.div>
    </div>
  );
}

function EditionCard({ edition }) {
  const date    = new Date(edition.sent_at?._seconds * 1000 || edition.sent_at);
  const dateStr = date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  return (
    <motion.div
      variants={fadeUp}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      style={{ display: "flex", alignItems: "flex-start", gap: "20px" }}
    >
      {/* Timeline dot */}
      <div style={{ flexShrink: 0, marginTop: "18px", position: "relative", zIndex: 1 }}>
        <div style={{ height: "32px", width: "32px", borderRadius: "50%", background: "#fff", border: "2px solid rgba(99,102,241,0.25)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}>
          <Mail style={{ height: "13px", width: "13px", color: "#6366F1" }} />
        </div>
      </div>

      {/* Card */}
      <motion.div
        whileHover={{ y: -2, boxShadow: "0 10px 28px rgba(0,0,0,0.08)", transition: { duration: 0.2 } }}
        style={{ flex: 1, borderRadius: "16px", background: "#fff", border: "1px solid rgba(0,0,0,0.07)", padding: "20px", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Date */}
            <div style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12px", color: "#CBD5E1", marginBottom: "8px" }}>
              <Calendar style={{ height: "12px", width: "12px" }} />
              {dateStr}
            </div>

            {/* Subject */}
            <h3 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "15px", color: "#0F172A", lineHeight: 1.4, marginBottom: "8px" }}>
              {edition.subject?.replace(/^AI Newsletter — /, "").replace(/^Brief — /, "")}
            </h3>

            {/* Preview */}
            {edition.plain_text_preview && (
              <p style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                {edition.plain_text_preview}
              </p>
            )}
          </div>

          {edition.html_gcs_url && (
            <a href={edition.html_gcs_url} target="_blank" rel="noopener noreferrer" style={{ flexShrink: 0, textDecoration: "none" }}>
              <motion.div
                whileHover={{ scale: 1.04, boxShadow: "0 4px 14px rgba(99,102,241,0.3)" }}
                whileTap={{ scale: 0.97 }}
                style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "8px 14px", borderRadius: "9px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "13px", fontWeight: 600, boxShadow: "0 2px 10px rgba(99,102,241,0.25)", cursor: "pointer" }}
              >
                Read
                <ExternalLink style={{ height: "12px", width: "12px" }} />
              </motion.div>
            </a>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {[1, 2, 3].map((i) => (
        <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "20px" }}>
          <div style={{ height: "32px", width: "32px", borderRadius: "50%", background: "#E2E8F0", flexShrink: 0, marginTop: "18px" }} />
          <div style={{ flex: 1, borderRadius: "16px", background: "#fff", border: "1px solid rgba(0,0,0,0.07)", padding: "20px" }}>
            <div style={{ height: "11px", background: "#F1F5F9", borderRadius: "6px", width: "100px", marginBottom: "10px" }} />
            <div style={{ height: "15px", background: "#F1F5F9", borderRadius: "6px", width: "70%", marginBottom: "10px" }} />
            <div style={{ height: "12px", background: "#F8FAFF", borderRadius: "6px", width: "100%", marginBottom: "6px" }} />
            <div style={{ height: "12px", background: "#F8FAFF", borderRadius: "6px", width: "60%" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      style={{ textAlign: "center", padding: "80px 24px" }}
    >
      <div style={{ display: "flex", justifyContent: "center", marginBottom: "24px" }}>
        <div style={{ position: "relative" }}>
          <div style={{ height: "80px", width: "80px", borderRadius: "20px", background: "rgba(99,102,241,0.07)", border: "1px solid rgba(99,102,241,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Inbox style={{ height: "36px", width: "36px", color: "#6366F1" }} />
          </div>
          <div style={{ position: "absolute", top: "-4px", right: "-4px", height: "22px", width: "22px", borderRadius: "50%", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Sparkles style={{ height: "11px", width: "11px", color: "#fff" }} />
          </div>
        </div>
      </div>
      <h2 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.2rem", color: "#0F172A", marginBottom: "8px" }}>
        Your first edition is on its way.
      </h2>
      <p style={{ fontSize: "14px", color: "#94A3B8", maxWidth: "280px", margin: "0 auto", lineHeight: 1.6 }}>
        Your first brief will appear here after delivery. Check back tomorrow morning.
      </p>
    </motion.div>
  );
}
