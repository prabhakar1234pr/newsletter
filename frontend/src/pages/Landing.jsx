import { Link } from "react-router-dom";
import { ArrowRight, Zap } from "lucide-react";
import { TOPICS_CONFIG } from "@/topicsConfig";
import { motion } from "framer-motion";

/* ── Reusable variants ───────────────────────────────────── */
const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show:   { opacity: 1, y: 0 },
};

const fadeIn = {
  hidden: { opacity: 0 },
  show:   { opacity: 1 },
};

/* ── Gmail SVG icon ──────────────────────────────────────── */
function GmailIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
      {/* Envelope body */}
      <path fill="#fff" stroke="#DADCE0" strokeWidth="1.5" d="M4 10h40a2 2 0 0 1 2 2v24a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V12a2 2 0 0 1 2-2z"/>
      {/* Left blue panel */}
      <path fill="#4285F4" d="M2 14v22l12-11z"/>
      {/* Right green panel */}
      <path fill="#34A853" d="M46 14v22L34 25z"/>
      {/* Bottom yellow fold */}
      <path fill="#FBBC04" d="M2 36l12-11 10 7 10-7 12 11H2z"/>
      {/* Top red M */}
      <path fill="#EA4335" d="M2 12l22 15 22-15H2z"/>
    </svg>
  );
}

/* ── Newsletter cards data ───────────────────────────────── */
const CARDS = [
  {
    tag: null,
    tagLabel: null,
    tagColor: null,
    headline: "China's Strategic Goals in the South China Sea",
    preview: "Analysing China's military and economic ambitions in the contested waters of the region...",
    date: "Apr 22",
  },
  {
    tag: "TECH",
    tagLabel: "TECHNOLOGY",
    tagColor: "#3B82F6",
    headline: "Breakthrough in Quantum Computing Efficiency",
    preview: "New advancements are set to revolutionize quantum algorithms and processing speeds.",
    date: "Apr 22",
  },
  {
    tag: "HEALTH",
    tagLabel: "WELLNESS",
    tagColor: "#14B8A6",
    headline: "5 Proven Tips for Better Morning Routines",
    preview: "Simple habits to transform how you start your day, backed by science.",
    date: "Apr 22",
  },
  {
    tag: "FINANCE",
    tagLabel: "MARKETS",
    tagColor: "#F59E0B",
    headline: "Fed Signals Rate Pause Amid Inflation Data",
    preview: "Markets rally as Federal Reserve hints at holding rates steady through Q3...",
    date: "Apr 22",
  },
  {
    tag: "FILM",
    tagLabel: "HOLLYWOOD",
    tagColor: "#EC4899",
    headline: "Cannes 2025 Lineup Stirs Early Controversy",
    preview: "Three debut directors land coveted Palme d'Or competition slots this year...",
    date: "Apr 22",
  },
  {
    tag: "SPACE",
    tagLabel: "SCIENCE",
    tagColor: "#8B5CF6",
    headline: "NASA's Artemis III Moon Landing Window Set",
    preview: "Engineers confirm launch corridor as lunar south pole site selection finalised...",
    date: "Apr 22",
  },
];

/*
  Cards drift diagonally DOWN-RIGHT, exiting through the right
  edge of the viewport. Opacity fades fast so they dissolve
  naturally — no hard clip needed.
*/
const CARD_RESTS = [
  { top:   0, left:   0,   rotate: -1,  zIndex: 6, opacity: 1.00 },
  { top:  55, left:  60,   rotate:  2,  zIndex: 5, opacity: 0.80 },
  { top: 106, left: 128,   rotate:  6,  zIndex: 4, opacity: 0.50 },
  { top: 152, left: 205,   rotate: 11,  zIndex: 3, opacity: 0.24 },
  { top: 192, left: 292,   rotate: 17,  zIndex: 2, opacity: 0.10 },
  { top: 228, left: 388,   rotate: 24,  zIndex: 1, opacity: 0.03 },
];

function NewsCard({ card, rest, index }) {
  const isTop = index === 0;
  return (
    <motion.div
      initial={{ opacity: 0, y: 50, rotate: rest.rotate - 6 }}
      animate={{ opacity: rest.opacity, y: 0, rotate: rest.rotate }}
      transition={{ duration: 0.65, delay: 0.45 + index * 0.12, ease: [0.22, 1, 0.36, 1] }}
      whileHover={isTop ? { y: -6, boxShadow: "0 20px 48px rgba(0,0,0,0.15)", transition: { duration: 0.2 } } : {}}
      style={{
        background: "#FFFFFF",
        borderRadius: "16px",
        padding: "20px",
        boxShadow: "0 8px 32px rgba(0,0,0,0.09), 0 2px 8px rgba(0,0,0,0.05)",
        width: "300px",
        position: "absolute",
        top: rest.top,
        left: rest.left,
        zIndex: rest.zIndex,
        transformOrigin: "bottom left",
      }}
    >
      {card.tag ? (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
          <span style={{ background: card.tagColor, color: "#fff", fontSize: "10px", fontWeight: 700, padding: "3px 8px", borderRadius: "6px", letterSpacing: "0.05em", textTransform: "uppercase" }}>
            {card.tag}
          </span>
          <span style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 500, letterSpacing: "0.04em" }}>
            {card.tagLabel}
          </span>
        </div>
      ) : (
        <div style={{ marginBottom: "10px" }} />
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", marginBottom: "8px" }}>
        <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#0F172A", lineHeight: 1.35, flex: 1 }}>
          {card.headline}
        </h4>
        <span style={{ fontSize: "11px", color: "#CBD5E1", whiteSpace: "nowrap", marginTop: "2px" }}>
          {card.date}
        </span>
      </div>

      <p style={{ fontSize: "12px", color: "#94A3B8", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
        {card.preview}
      </p>
    </motion.div>
  );
}

function StackedCards() {
  return (
    <div style={{ position: "relative" }}>
      {/* Gmail delivery badge — floats above the top card */}
      <motion.div
        initial={{ opacity: 0, y: -10, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: 1.2, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        style={{
          position: "absolute",
          top: "-36px",
          left: "12px",
          zIndex: 20,
          display: "inline-flex",
          alignItems: "center",
          gap: "7px",
          background: "#fff",
          border: "1px solid rgba(0,0,0,0.09)",
          borderRadius: "999px",
          padding: "5px 12px 5px 8px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.08)",
          fontSize: "12px",
          fontWeight: 600,
          color: "#374151",
          whiteSpace: "nowrap",
        }}
      >
        <GmailIcon size={20} />
        Delivered to your inbox
      </motion.div>

      {/* No overflow:hidden — section clips at viewport edge naturally */}
      <div style={{ position: "relative", width: "320px", height: "420px" }}>
        {CARDS.map((card, i) => (
          <NewsCard key={i} card={card} rest={CARD_RESTS[i]} index={i} />
        ))}
      </div>
    </div>
  );
}

/* ── Main ──────────────────────────────────────────────────── */
export default function Landing() {
  return (
    <div style={{ minHeight: "100vh", background: "#F8FAFF", color: "#0F172A", fontFamily: "'Inter', system-ui, sans-serif", overflowX: "hidden" }}>

      {/* ── Nav ──────────────────────────────────────────────── */}
      <motion.nav
        initial="hidden"
        animate="show"
        variants={fadeIn}
        transition={{ duration: 0.5 }}
        style={{ position: "sticky", top: 0, zIndex: 50, background: "rgba(248,250,255,0.85)", backdropFilter: "blur(16px)", borderBottom: "1px solid rgba(0,0,0,0.06)" }}
      >
        <div style={{ maxWidth: "1152px", margin: "0 auto", padding: "0 32px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ height: "32px", width: "32px", borderRadius: "8px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Zap style={{ height: "16px", width: "16px", color: "#fff" }} />
            </div>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "18px", color: "#0F172A" }}>AI Newsletter</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Link to="/login" style={{ padding: "8px 16px", borderRadius: "8px", fontSize: "14px", color: "#64748B", fontWeight: 500, textDecoration: "none" }}>
              Sign in
            </Link>
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Link to="/signup" style={{ padding: "10px 20px", borderRadius: "10px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "14px", fontWeight: 600, textDecoration: "none", display: "flex", alignItems: "center", gap: "6px", boxShadow: "0 4px 14px rgba(99,102,241,0.35)" }}>
                Get started <ArrowRight style={{ height: "14px", width: "14px" }} />
              </Link>
            </motion.div>
          </div>
        </div>
      </motion.nav>

      {/* ── Hero ─────────────────────────────────────────────── */}
      <section style={{ minHeight: "calc(100vh - 64px)", display: "flex", alignItems: "center", position: "relative", overflow: "hidden" }}>

        {/* Background blobs */}
        <div style={{ position: "absolute", right: "-80px", top: "50%", transform: "translateY(-50%)", width: "700px", height: "700px", borderRadius: "50%", background: "radial-gradient(circle at 40% 50%, rgba(99,102,241,0.12) 0%, rgba(59,130,246,0.08) 40%, transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", right: "100px", top: "20%", width: "500px", height: "500px", borderRadius: "50%", background: "radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 60%)", pointerEvents: "none" }} />

        <div style={{ maxWidth: "1152px", margin: "0 auto", padding: "0 32px", width: "100%", position: "relative", zIndex: 10 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "80px", alignItems: "center" }}>

            {/* ── Left: Copy ─────────────────────────────────── */}
            <motion.div
              initial="hidden"
              animate="show"
              variants={{ show: { transition: { staggerChildren: 0.12 } } }}
            >
              <motion.div variants={fadeUp} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
                <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "clamp(2.4rem, 4vw, 3.5rem)", lineHeight: 1.1, color: "#0F172A", letterSpacing: "-0.02em", display: "block" }}>
                  Your AI-powered
                </span>
              </motion.div>

              <motion.div variants={fadeUp} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
                <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "clamp(2.4rem, 4vw, 3.5rem)", lineHeight: 1.1, color: "#0F172A", letterSpacing: "-0.02em", display: "block", marginBottom: "20px" }}>
                  newsletter,{" "}
                  <span style={{ color: "#4F7CFF" }}>on your topic</span>
                </span>
              </motion.div>

              <motion.p
                variants={fadeUp}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                style={{ fontSize: "17px", color: "#64748B", marginBottom: "36px", maxWidth: "400px", lineHeight: 1.65 }}
              >
                Get a custom daily newsletter generated by AI, on the topics you care about most.
              </motion.p>

              <motion.div variants={fadeUp} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
                <motion.div
                  whileHover={{ scale: 1.03, boxShadow: "0 8px 28px rgba(99,102,241,0.55)" }}
                  whileTap={{ scale: 0.97 }}
                  style={{ display: "inline-block" }}
                >
                  <Link
                    to="/signup"
                    style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "14px 28px", borderRadius: "12px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "16px", fontWeight: 600, textDecoration: "none", boxShadow: "0 6px 20px rgba(99,102,241,0.4)" }}
                  >
                    Get started <ArrowRight style={{ height: "16px", width: "16px" }} />
                  </Link>
                </motion.div>
              </motion.div>
            </motion.div>

            {/* ── Right: Stacked cards ─────────────────────── */}
            <div style={{ display: "flex", justifyContent: "center", alignItems: "flex-start", paddingTop: "40px" }}>
              <StackedCards />
            </div>

          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────── */}
      <section style={{ padding: "80px 32px", borderTop: "1px solid rgba(0,0,0,0.06)", background: "#fff" }}>
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
          variants={{ show: { transition: { staggerChildren: 0.12 } } }}
          style={{ maxWidth: "800px", margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "20px", textAlign: "center" }}
        >
          {[
            { emoji: "⏰", title: "Your schedule", desc: "Any hour. Any timezone." },
            { emoji: "✦",  title: "AI synthesis",  desc: "Many sources → 1 perfect brief." },
            { emoji: "🎯", title: "307 topics",     desc: "From Hollywood to quantum physics." },
          ].map(({ emoji, title, desc }) => (
            <motion.div
              key={title}
              variants={fadeUp}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ y: -4, boxShadow: "0 8px 24px rgba(99,102,241,0.1)", transition: { duration: 0.2 } }}
              style={{ borderRadius: "16px", padding: "28px 20px", background: "#F8FAFF", border: "1px solid rgba(99,102,241,0.1)" }}
            >
              <div style={{ fontSize: "24px", marginBottom: "12px" }}>{emoji}</div>
              <div style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "14px", color: "#0F172A", marginBottom: "6px" }}>{title}</div>
              <div style={{ fontSize: "13px", color: "#94A3B8" }}>{desc}</div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ── Topics ───────────────────────────────────────────── */}
      <section style={{ padding: "60px 32px 80px", textAlign: "center", background: "#F8FAFF", borderTop: "1px solid rgba(0,0,0,0.04)" }}>
        <motion.p
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.5 }}
          variants={fadeUp}
          transition={{ duration: 0.5 }}
          style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: "28px" }}
        >
          307 sub-topics across 10 domains
        </motion.p>
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          variants={{ show: { transition: { staggerChildren: 0.025 } } }}
          style={{ display: "flex", flexWrap: "wrap", gap: "8px", justifyContent: "center", maxWidth: "640px", margin: "0 auto" }}
        >
          {Object.keys(TOPICS_CONFIG).map((t) => (
            <motion.span
              key={t}
              variants={fadeIn}
              transition={{ duration: 0.3 }}
              whileHover={{ color: "#4F7CFF", borderColor: "#4F7CFF", y: -2, transition: { duration: 0.15 } }}
              style={{ padding: "6px 14px", borderRadius: "9999px", fontSize: "12px", color: "#64748B", background: "#fff", border: "1px solid rgba(0,0,0,0.09)", cursor: "default" }}
            >
              {t}
            </motion.span>
          ))}
        </motion.div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────── */}
      <section style={{ padding: "100px 32px", textAlign: "center", background: "#fff", borderTop: "1px solid rgba(0,0,0,0.06)", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
          <div style={{ width: "600px", height: "300px", borderRadius: "50%", background: "radial-gradient(ellipse, rgba(99,102,241,0.07), transparent 70%)" }} />
        </div>
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.4 }}
          variants={{ show: { transition: { staggerChildren: 0.13 } } }}
          style={{ position: "relative", maxWidth: "520px", margin: "0 auto" }}
        >
          <motion.div variants={fadeUp} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "clamp(2rem,4vw,3rem)", letterSpacing: "-0.02em", color: "#0F172A", lineHeight: 1.15, display: "block" }}>
              Read smarter,
            </span>
          </motion.div>
          <motion.div variants={fadeUp} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "clamp(2rem,4vw,3rem)", letterSpacing: "-0.02em", color: "#4F7CFF", lineHeight: 1.15, display: "block", marginBottom: "16px" }}>
              starting tomorrow.
            </span>
          </motion.div>
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.5 }}
            style={{ color: "#94A3B8", marginBottom: "32px", fontSize: "15px" }}
          >
            Set up in 60 seconds. First edition tomorrow morning.
          </motion.p>
          <motion.div
            variants={fadeUp}
            transition={{ duration: 0.5 }}
            whileHover={{ scale: 1.04, transition: { duration: 0.15 } }}
            whileTap={{ scale: 0.97 }}
            style={{ display: "inline-block" }}
          >
            <Link
              to="/signup"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "14px 28px", borderRadius: "12px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "16px", fontWeight: 600, textDecoration: "none", boxShadow: "0 6px 20px rgba(99,102,241,0.35)" }}
            >
              Get started free <ArrowRight style={{ height: "16px", width: "16px" }} />
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer style={{ padding: "32px", borderTop: "1px solid rgba(0,0,0,0.06)", background: "#F8FAFF" }}>
        <div style={{ maxWidth: "1152px", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ height: "24px", width: "24px", borderRadius: "6px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Zap style={{ height: "12px", width: "12px", color: "#fff" }} />
            </div>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "14px", color: "#0F172A" }}>AI Newsletter</span>
          </div>
          <div style={{ display: "flex", gap: "20px" }}>
            <Link to="/login"  style={{ fontSize: "13px", color: "#94A3B8", textDecoration: "none" }}>Sign in</Link>
            <Link to="/signup" style={{ fontSize: "13px", color: "#94A3B8", textDecoration: "none" }}>Sign up free</Link>
          </div>
          <p style={{ fontSize: "12px", color: "#CBD5E1" }}>© {new Date().getFullYear()} AI Newsletter</p>
        </div>
      </footer>

    </div>
  );
}
