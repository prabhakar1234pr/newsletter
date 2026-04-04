import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { getEditions } from "@/lib/api";
import { ArrowLeft, Inbox, Zap, Sparkles, Mail, ChevronDown, X, Calendar, ExternalLink } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const PAGE_SIZE = 8;

function groupByMonth(editions) {
  const groups = {};
  editions.forEach((e) => {
    const date = new Date(e.sent_at?._seconds * 1000 || e.sent_at);
    const key  = date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
    if (!groups[key]) groups[key] = [];
    groups[key].push(e);
  });
  return groups;
}

export default function History() {
  const { subscriptionId } = useParams();
  const { getToken } = useAuth();

  const [editions, setEditions] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [visible, setVisible]   = useState(PAGE_SIZE);
  const [selected, setSelected] = useState(null); // edition open in modal

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

  // Close modal on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") setSelected(null); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const shown   = editions.slice(0, visible);
  const groups  = groupByMonth(shown);
  const hasMore = visible < editions.length;

  return (
    <>
      <div style={{ minHeight: "100vh", background: "#F8FAFF", fontFamily: "'Inter', system-ui, sans-serif", color: "#0F172A" }}>

        {/* ── Nav ─────────────────────────────────────────── */}
        <motion.nav
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}
          style={{ position: "sticky", top: 0, zIndex: 40, background: "rgba(248,250,255,0.88)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(0,0,0,0.07)" }}
        >
          <div style={{ maxWidth: "680px", margin: "0 auto", padding: "0 24px", height: "64px", display: "flex", alignItems: "center", gap: "12px" }}>
            <Link to="/dashboard" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "34px", width: "34px", borderRadius: "8px", background: "#fff", border: "1px solid rgba(0,0,0,0.09)", textDecoration: "none", flexShrink: 0 }}>
              <ArrowLeft style={{ height: "15px", width: "15px", color: "#64748B" }} />
            </Link>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{ height: "30px", width: "30px", borderRadius: "8px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 3px 10px rgba(99,102,241,0.3)" }}>
                <Zap style={{ height: "14px", width: "14px", color: "#fff" }} />
              </div>
              <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "15px", color: "#0F172A" }}>AI Newsletter</span>
              <span style={{ color: "#CBD5E1" }}>/</span>
              <span style={{ fontSize: "14px", color: "#94A3B8" }}>History</span>
            </div>
          </div>
        </motion.nav>

        <div style={{ maxWidth: "680px", margin: "0 auto", padding: "40px 24px 64px" }}>

          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            style={{ marginBottom: "36px" }}
          >
            <h1 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.75rem", color: "#0F172A", letterSpacing: "-0.02em", marginBottom: "4px" }}>
              History
            </h1>
            <p style={{ fontSize: "14px", color: "#94A3B8" }}>
              {loading ? "Loading…" : `${editions.length} edition${editions.length !== 1 ? "s" : ""} delivered · click any to read`}
            </p>
          </motion.div>

          {loading ? (
            <LoadingSkeleton />
          ) : editions.length === 0 ? (
            <EmptyState />
          ) : (
            <>
              {Object.entries(groups).map(([month, items], gi) => (
                <motion.div
                  key={month}
                  initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: gi * 0.06, ease: [0.22, 1, 0.36, 1] }}
                  style={{ marginBottom: "32px" }}
                >
                  {/* Month divider */}
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "#94A3B8", letterSpacing: "0.08em", textTransform: "uppercase", whiteSpace: "nowrap" }}>
                      {month}
                    </span>
                    <div style={{ flex: 1, height: "1px", background: "rgba(0,0,0,0.07)" }} />
                    <span style={{ fontSize: "11px", color: "#CBD5E1", whiteSpace: "nowrap" }}>{items.length} brief{items.length !== 1 ? "s" : ""}</span>
                  </div>

                  {/* Cards */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {items.map((edition) => (
                      <EditionCard
                        key={edition.id}
                        edition={edition}
                        onClick={() => setSelected(edition)}
                      />
                    ))}
                  </div>
                </motion.div>
              ))}

              {/* Load more */}
              {hasMore && (
                <div style={{ display: "flex", justifyContent: "center", marginTop: "8px" }}>
                  <motion.button
                    onClick={() => setVisible((v) => v + PAGE_SIZE)}
                    whileHover={{ y: -1, boxShadow: "0 6px 18px rgba(0,0,0,0.08)" }}
                    whileTap={{ scale: 0.97 }}
                    style={{ display: "inline-flex", alignItems: "center", gap: "7px", padding: "10px 22px", borderRadius: "10px", background: "#fff", border: "1px solid rgba(0,0,0,0.1)", fontSize: "14px", fontWeight: 500, color: "#374151", cursor: "pointer", boxShadow: "0 2px 8px rgba(0,0,0,0.05)" }}
                  >
                    <ChevronDown style={{ height: "15px", width: "15px", color: "#94A3B8" }} />
                    Load {Math.min(PAGE_SIZE, editions.length - visible)} more
                  </motion.button>
                </div>
              )}

              {!hasMore && editions.length > PAGE_SIZE && (
                <p style={{ textAlign: "center", fontSize: "13px", color: "#CBD5E1", marginTop: "16px" }}>
                  All {editions.length} editions loaded
                </p>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Newsletter modal ──────────────────────────────── */}
      <NewsletterModal edition={selected} onClose={() => setSelected(null)} />
    </>
  );
}

/* ── Edition card ────────────────────────────────────────── */
function EditionCard({ edition, onClick }) {
  const date    = new Date(edition.sent_at?._seconds * 1000 || edition.sent_at);
  const dateStr = date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  const timeStr = date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

  return (
    <motion.div
      whileHover={{ y: -1, boxShadow: "0 8px 24px rgba(0,0,0,0.08)", borderColor: "rgba(99,102,241,0.25)", transition: { duration: 0.15 } }}
      whileTap={{ scale: 0.99 }}
      onClick={onClick}
      style={{ borderRadius: "14px", background: "#fff", border: "1px solid rgba(0,0,0,0.07)", padding: "14px 18px", display: "flex", alignItems: "center", gap: "14px", cursor: "pointer", boxShadow: "0 2px 6px rgba(0,0,0,0.04)", transition: "border-color 0.2s" }}
    >
      {/* Icon */}
      <div style={{ height: "38px", width: "38px", borderRadius: "10px", background: "rgba(99,102,241,0.07)", border: "1px solid rgba(99,102,241,0.12)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Mail style={{ height: "15px", width: "15px", color: "#6366F1" }} />
      </div>

      {/* Text */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <h3 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "14px", color: "#0F172A", lineHeight: 1.35, marginBottom: "3px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {edition.subject?.replace(/^AI Newsletter — /, "").replace(/^Brief — /, "")}
        </h3>
        {edition.plain_text_preview && (
          <p style={{ fontSize: "12px", color: "#94A3B8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: "3px" }}>
            {edition.plain_text_preview}
          </p>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "11px", color: "#CBD5E1" }}>
          <Calendar style={{ height: "10px", width: "10px" }} />
          {dateStr} · {timeStr}
        </div>
      </div>

      {/* Arrow hint */}
      <div style={{ color: "#CBD5E1", flexShrink: 0, display: "flex" }}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </motion.div>
  );
}

/* ── Newsletter modal ────────────────────────────────────── */
function NewsletterModal({ edition, onClose }) {
  const date = edition ? new Date(edition.sent_at?._seconds * 1000 || edition.sent_at) : null;
  const dateStr = date?.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });

  return (
    <AnimatePresence>
      {edition && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", backdropFilter: "blur(4px)", zIndex: 50 }}
          />

          {/* Modal panel */}
          <motion.div
            initial={{ opacity: 0, y: 32, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            style={{
              position: "fixed",
              inset: "24px",
              zIndex: 51,
              background: "#fff",
              borderRadius: "20px",
              boxShadow: "0 32px 80px rgba(0,0,0,0.2)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            {/* Modal header */}
            <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(0,0,0,0.07)", display: "flex", alignItems: "center", gap: "14px", flexShrink: 0 }}>
              <div style={{ height: "36px", width: "36px", borderRadius: "10px", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.12)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Mail style={{ height: "15px", width: "15px", color: "#6366F1" }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <h2 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "15px", color: "#0F172A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: "2px" }}>
                  {edition.subject?.replace(/^AI Newsletter — /, "").replace(/^Brief — /, "")}
                </h2>
                <div style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12px", color: "#CBD5E1" }}>
                  <Calendar style={{ height: "11px", width: "11px" }} />
                  {dateStr}
                </div>
              </div>

              {/* Open in new tab */}
              {edition.html_gcs_url && (
                <a href={edition.html_gcs_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none", flexShrink: 0 }}>
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.96 }}
                    title="Open in new tab"
                    style={{ height: "34px", width: "34px", borderRadius: "8px", background: "#F8FAFF", border: "1px solid rgba(0,0,0,0.09)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
                  >
                    <ExternalLink style={{ height: "14px", width: "14px", color: "#64748B" }} />
                  </motion.div>
                </a>
              )}

              {/* Close */}
              <motion.button
                onClick={onClose}
                whileHover={{ background: "#F1F5F9" }}
                whileTap={{ scale: 0.95 }}
                style={{ height: "34px", width: "34px", borderRadius: "8px", background: "#F8FAFF", border: "1px solid rgba(0,0,0,0.09)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 }}
              >
                <X style={{ height: "15px", width: "15px", color: "#64748B" }} />
              </motion.button>
            </div>

            {/* iframe */}
            {edition.html_gcs_url ? (
              <iframe
                src={edition.html_gcs_url}
                title={edition.subject}
                style={{ flex: 1, border: "none", width: "100%", background: "#fff" }}
              />
            ) : (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#94A3B8", fontSize: "14px" }}>
                No content available for this edition.
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/* ── Skeleton ────────────────────────────────────────────── */
function LoadingSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} style={{ borderRadius: "14px", background: "#fff", border: "1px solid rgba(0,0,0,0.07)", padding: "14px 18px", display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ height: "38px", width: "38px", borderRadius: "10px", background: "#F1F5F9", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ height: "13px", background: "#F1F5F9", borderRadius: "5px", width: "60%", marginBottom: "8px" }} />
            <div style={{ height: "11px", background: "#F8FAFF", borderRadius: "5px", width: "85%", marginBottom: "6px" }} />
            <div style={{ height: "10px", background: "#F8FAFF", borderRadius: "5px", width: "30%" }} />
          </div>
          <div style={{ height: "16px", width: "16px", background: "#F1F5F9", borderRadius: "4px" }} />
        </div>
      ))}
    </div>
  );
}

/* ── Empty state ─────────────────────────────────────────── */
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
