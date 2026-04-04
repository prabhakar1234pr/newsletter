import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { createSubscription } from "@/lib/api";
import { TOPICS_CONFIG } from "@/topicsConfig";
import { ArrowRight, ArrowLeft, Check, Zap, Sparkles, Clock, Globe, Rocket, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

/* ── Data ────────────────────────────────────────────────── */
const TIMEZONES = [
  { label: "IST — India (UTC+5:30)",       value: "Asia/Kolkata" },
  { label: "EST — US Eastern (UTC-5)",      value: "America/New_York" },
  { label: "PST — US Pacific (UTC-8)",      value: "America/Los_Angeles" },
  { label: "GMT — London (UTC+0)",          value: "Europe/London" },
  { label: "CET — Central Europe (UTC+1)",  value: "Europe/Berlin" },
  { label: "JST — Japan (UTC+9)",           value: "Asia/Tokyo" },
  { label: "AEST — Australia (UTC+10)",     value: "Australia/Sydney" },
  { label: "SGT — Singapore (UTC+8)",       value: "Asia/Singapore" },
  { label: "GST — Gulf (UTC+4)",            value: "Asia/Dubai" },
];

const HOURS = Array.from({ length: 24 }, (_, i) => ({
  label: `${String(i).padStart(2, "0")}:00 — ${i === 0 ? "Midnight" : i < 12 ? `${i} AM` : i === 12 ? "Noon" : `${i - 12} PM`}`,
  value: String(i),
}));

const MINUTES = Array.from({ length: 60 }, (_, i) => ({
  label: String(i).padStart(2, "0"),
  value: String(i),
}));

function formatDeliveryClock(hourStr, minuteStr) {
  const h = parseInt(hourStr, 10);
  const m = parseInt(minuteStr, 10);
  const h12 = h % 12 || 12;
  const period = h < 12 ? "AM" : "PM";
  return `${h12}:${String(m).padStart(2, "0")} ${period}`;
}

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

/* ── Reusable select style ───────────────────────────────── */
const selectStyle = {
  width: "100%",
  height: "46px",
  borderRadius: "11px",
  border: "1px solid rgba(0,0,0,0.12)",
  padding: "0 36px 0 14px",
  fontSize: "14px",
  color: "#0F172A",
  background: "#fff",
  outline: "none",
  appearance: "none",
  cursor: "pointer",
  boxSizing: "border-box",
  transition: "border-color 0.2s, box-shadow 0.2s",
};

function NativeSelect({ value, onChange, children, ...rest }) {
  return (
    <div style={{ position: "relative" }}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={selectStyle}
        onFocus={e => { e.target.style.borderColor = "#6366F1"; e.target.style.boxShadow = "0 0 0 3px rgba(99,102,241,0.1)"; }}
        onBlur={e => { e.target.style.borderColor = "rgba(0,0,0,0.12)"; e.target.style.boxShadow = "none"; }}
        {...rest}
      >
        {children}
      </select>
      <ChevronDown style={{ position: "absolute", right: "12px", top: "50%", transform: "translateY(-50%)", height: "16px", width: "16px", color: "#94A3B8", pointerEvents: "none" }} />
    </div>
  );
}

/* ── Stepper ─────────────────────────────────────────────── */
function Stepper({ step }) {
  const steps = ["Pick topic", "Set time", "Confirm"];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "32px" }}>
      {steps.map((label, i) => {
        const idx    = i + 1;
        const done   = step > idx;
        const active = step === idx;
        return (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <motion.div
                animate={{
                  background: done || active ? "linear-gradient(135deg,#6366F1,#3B82F6)" : "#F1F5F9",
                  scale: active ? 1.1 : 1,
                }}
                transition={{ duration: 0.3 }}
                style={{ height: "28px", width: "28px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 700, color: done || active ? "#fff" : "#94A3B8", border: active ? "none" : done ? "none" : "1px solid rgba(0,0,0,0.1)", boxShadow: active ? "0 0 0 4px rgba(99,102,241,0.15)" : "none", flexShrink: 0 }}
              >
                {done ? <Check style={{ height: "12px", width: "12px" }} /> : idx}
              </motion.div>
              <span style={{ fontSize: "13px", fontWeight: 500, color: active ? "#0F172A" : "#94A3B8", transition: "color 0.2s" }}>
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <motion.div
                animate={{ background: step > idx ? "#6366F1" : "#E2E8F0" }}
                transition={{ duration: 0.4 }}
                style={{ height: "1px", width: "32px" }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Topic grid ──────────────────────────────────────────── */
function TopicGrid({ selected, onSelect }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
      {Object.keys(TOPICS_CONFIG).map((t) => {
        const isSelected = selected === t;
        return (
          <motion.button
            key={t}
            type="button"
            onClick={() => onSelect(t)}
            whileHover={{ y: -1, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
            whileTap={{ scale: 0.97 }}
            style={{
              display: "flex", alignItems: "center", gap: "10px", padding: "12px 14px",
              borderRadius: "12px", border: `1.5px solid ${isSelected ? "#6366F1" : "rgba(0,0,0,0.09)"}`,
              background: isSelected ? "rgba(99,102,241,0.06)" : "#fff",
              cursor: "pointer", textAlign: "left", transition: "border-color 0.2s, background 0.2s",
            }}
          >
            <span style={{ fontSize: "18px", lineHeight: 1, flexShrink: 0 }}>{TOPIC_ICONS[t] || "📰"}</span>
            <span style={{ fontSize: "13px", fontWeight: 500, color: isSelected ? "#4F46E5" : "#374151", flex: 1, lineHeight: 1.3 }}>{t}</span>
            {isSelected && <Check style={{ height: "14px", width: "14px", color: "#6366F1", flexShrink: 0 }} />}
          </motion.button>
        );
      })}
    </div>
  );
}

/* ── Page animations ─────────────────────────────────────── */
const stepVariants = {
  enter:  { opacity: 0, x: 24 },
  center: { opacity: 1, x: 0 },
  exit:   { opacity: 0, x: -24 },
};

/* ── Main ────────────────────────────────────────────────── */
export default function Onboarding() {
  const { user, getToken } = useAuth();
  const navigate = useNavigate();

  const [step, setStep]         = useState(1);
  const [topic, setTopic]       = useState("");
  const [subTopic, setSubTopic] = useState("");
  const [hour, setHour]         = useState("8");
  const [minute, setMinute]     = useState("0");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [direction, setDirection] = useState(1);

  const subTopics = topic ? TOPICS_CONFIG[topic] || [] : [];
  const canStep1  = !!topic;
  const canSubmit = topic && hour !== "" && minute !== "" && timezone;

  const goTo = (next) => {
    setDirection(next > step ? 1 : -1);
    setStep(next);
  };

  const handleSubmit = async () => {
    setError("");
    setLoading(true);
    try {
      const token = await getToken();
      await createSubscription(token, {
        topic,
        sub_genre: (subTopic && subTopic !== "_all_") ? subTopic : null,
        delivery_hour: parseInt(hour, 10),
        delivery_minute: parseInt(minute, 10),
        timezone,
        frequency: "daily",
      });
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
      goTo(2);
    } finally {
      setLoading(false);
    }
  };

  const hourLabel = formatDeliveryClock(hour, minute);
  const tzLabel   = TIMEZONES.find((t) => t.value === timezone)?.label?.split(" — ")[0] || timezone;
  const firstName = user?.displayName?.split(" ")[0] || "there";

  return (
    <div style={{ minHeight: "100vh", background: "#F8FAFF", display: "flex", alignItems: "center", justifyContent: "center", padding: "24px", fontFamily: "'Inter', system-ui, sans-serif", position: "relative", overflow: "hidden" }}>

      {/* Bg blobs */}
      <div style={{ position: "absolute", top: "-100px", right: "-100px", width: "500px", height: "500px", borderRadius: "50%", background: "radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 60%)", pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: "-80px", left: "-80px", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 60%)", pointerEvents: "none" }} />

      <div style={{ position: "relative", width: "100%", maxWidth: "480px" }}>

        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          style={{ marginBottom: "32px" }}
        >
          <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
            <div style={{ height: "34px", width: "34px", borderRadius: "9px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 12px rgba(99,102,241,0.3)" }}>
              <Zap style={{ height: "16px", width: "16px", color: "#fff" }} />
            </div>
            <span style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "17px", color: "#0F172A" }}>AI Newsletter</span>
          </Link>
        </motion.div>

        {/* Stepper */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1, duration: 0.4 }}>
          <Stepper step={step} />
        </motion.div>

        {/* Step content */}
        <AnimatePresence mode="wait" custom={direction}>
          {step === 1 && (
            <motion.div
              key="step1"
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            >
              <h1 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.6rem", color: "#0F172A", marginBottom: "6px", letterSpacing: "-0.02em" }}>
                What do you want to read about?
              </h1>
              <p style={{ fontSize: "14px", color: "#94A3B8", marginBottom: "24px" }}>
                Hi {firstName}! Pick your first topic.
              </p>

              <TopicGrid selected={topic} onSelect={(t) => { setTopic(t); setSubTopic(""); }} />

              {/* Sub-topic */}
              <AnimatePresence>
                {topic && subTopics.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0, marginTop: 0 }}
                    animate={{ opacity: 1, height: "auto", marginTop: "16px" }}
                    exit={{ opacity: 0, height: 0, marginTop: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <label style={{ display: "block", fontSize: "13px", fontWeight: 500, color: "#374151", marginBottom: "6px" }}>
                      Sub-topic <span style={{ color: "#CBD5E1", fontWeight: 400 }}>(optional — {subTopics.length} available)</span>
                    </label>
                    <NativeSelect value={subTopic} onChange={setSubTopic}>
                      <option value="_all_">— All of {topic} —</option>
                      {subTopics.map((st) => (
                        <option key={st} value={st}>{st}</option>
                      ))}
                    </NativeSelect>
                  </motion.div>
                )}
              </AnimatePresence>

              <motion.button
                onClick={() => goTo(2)}
                disabled={!canStep1}
                whileHover={canStep1 ? { scale: 1.02, boxShadow: "0 8px 24px rgba(99,102,241,0.45)" } : {}}
                whileTap={canStep1 ? { scale: 0.98 } : {}}
                style={{ width: "100%", marginTop: "24px", height: "48px", borderRadius: "12px", background: canStep1 ? "linear-gradient(135deg,#6366F1,#3B82F6)" : "#E2E8F0", color: canStep1 ? "#fff" : "#94A3B8", fontSize: "15px", fontWeight: 600, border: "none", cursor: canStep1 ? "pointer" : "not-allowed", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", boxShadow: canStep1 ? "0 4px 16px rgba(99,102,241,0.35)" : "none", transition: "background 0.2s" }}
              >
                Continue <ArrowRight style={{ height: "16px", width: "16px" }} />
              </motion.button>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            >
              <h1 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.6rem", color: "#0F172A", marginBottom: "6px", letterSpacing: "-0.02em" }}>
                When should it arrive?
              </h1>
              <p style={{ fontSize: "14px", color: "#94A3B8", marginBottom: "28px" }}>
                Your brief will land in your inbox at this exact time every day (in the timezone below).
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", fontWeight: 500, color: "#374151", marginBottom: "6px" }}>
                    <Clock style={{ height: "13px", width: "13px", color: "#6366F1" }} />
                    Delivery time
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <NativeSelect value={hour} onChange={setHour} aria-label="Hour">
                      {HOURS.map(({ label, value }) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </NativeSelect>
                    <NativeSelect value={minute} onChange={setMinute} aria-label="Minute">
                      {MINUTES.map(({ label, value }) => (
                        <option key={value} value={value}>:{label}</option>
                      ))}
                    </NativeSelect>
                  </div>
                </div>

                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", fontWeight: 500, color: "#374151", marginBottom: "6px" }}>
                    <Globe style={{ height: "13px", width: "13px", color: "#6366F1" }} />
                    Timezone
                  </label>
                  <NativeSelect value={timezone} onChange={setTimezone}>
                    {TIMEZONES.map(({ label, value }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </NativeSelect>
                </div>
              </div>

              {error && <ErrorMsg message={error} />}

              <div style={{ display: "flex", gap: "10px", marginTop: "28px" }}>
                <motion.button
                  onClick={() => goTo(1)}
                  whileHover={{ background: "#F1F5F9" }}
                  style={{ height: "48px", paddingInline: "20px", borderRadius: "12px", background: "#fff", border: "1px solid rgba(0,0,0,0.1)", fontSize: "14px", fontWeight: 500, color: "#374151", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                >
                  <ArrowLeft style={{ height: "15px", width: "15px" }} /> Back
                </motion.button>
                <motion.button
                  onClick={() => goTo(3)}
                  whileHover={{ scale: 1.02, boxShadow: "0 8px 24px rgba(99,102,241,0.45)" }}
                  whileTap={{ scale: 0.98 }}
                  style={{ flex: 1, height: "48px", borderRadius: "12px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "15px", fontWeight: 600, border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", boxShadow: "0 4px 16px rgba(99,102,241,0.35)" }}
                >
                  Review & launch <ArrowRight style={{ height: "16px", width: "16px" }} />
                </motion.button>
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div
              key="step3"
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            >
              <h1 style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 800, fontSize: "1.6rem", color: "#0F172A", marginBottom: "6px", letterSpacing: "-0.02em" }}>
                Ready to launch?
              </h1>
              <p style={{ fontSize: "14px", color: "#94A3B8", marginBottom: "24px" }}>
                Your first brief arrives tomorrow morning. Here's what you set up:
              </p>

              {/* Summary card */}
              <div style={{ borderRadius: "16px", background: "#fff", border: "1px solid rgba(99,102,241,0.2)", boxShadow: "0 4px 16px rgba(99,102,241,0.08)", overflow: "hidden", marginBottom: "24px" }}>
                {/* Accent bar */}
                <div style={{ height: "3px", background: "linear-gradient(90deg,#6366F1,#3B82F6)" }} />
                <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
                  {/* Topic */}
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "28px", lineHeight: 1 }}>{TOPIC_ICONS[topic] || "📰"}</span>
                    <div>
                      <div style={{ fontFamily: "'Plus Jakarta Sans', system-ui", fontWeight: 700, fontSize: "15px", color: "#0F172A" }}>{topic}</div>
                      {subTopic && subTopic !== "_all_" && (
                        <div style={{ fontSize: "12px", color: "#6366F1", marginTop: "2px" }}>Focus: {subTopic}</div>
                      )}
                    </div>
                  </div>

                  <div style={{ height: "1px", background: "rgba(99,102,241,0.1)" }} />

                  {[
                    { icon: Clock,    text: <>Every day at <strong style={{ color: "#0F172A" }}>{hourLabel}</strong></> },
                    { icon: Globe,    text: <>Timezone: <strong style={{ color: "#0F172A" }}>{tzLabel}</strong></> },
                    { icon: Sparkles, text: <>Synthesized from <strong style={{ color: "#0F172A" }}>many sources</strong> by Gemini 2.5 Pro</> },
                  ].map(({ icon: Icon, text }, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{ height: "30px", width: "30px", borderRadius: "8px", background: "rgba(99,102,241,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <Icon style={{ height: "14px", width: "14px", color: "#6366F1" }} />
                      </div>
                      <span style={{ fontSize: "13px", color: "#64748B" }}>{text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {error && <ErrorMsg message={error} />}

              <div style={{ display: "flex", gap: "10px" }}>
                <motion.button
                  onClick={() => goTo(2)}
                  whileHover={{ background: "#F1F5F9" }}
                  style={{ height: "48px", paddingInline: "20px", borderRadius: "12px", background: "#fff", border: "1px solid rgba(0,0,0,0.1)", fontSize: "14px", fontWeight: 500, color: "#374151", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                >
                  <ArrowLeft style={{ height: "15px", width: "15px" }} /> Back
                </motion.button>
                <motion.button
                  onClick={handleSubmit}
                  disabled={!canSubmit || loading}
                  whileHover={!loading ? { scale: 1.02, boxShadow: "0 8px 28px rgba(99,102,241,0.5)" } : {}}
                  whileTap={!loading ? { scale: 0.98 } : {}}
                  style={{ flex: 1, height: "48px", borderRadius: "12px", background: "linear-gradient(135deg,#6366F1,#3B82F6)", color: "#fff", fontSize: "15px", fontWeight: 600, border: "none", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", boxShadow: "0 4px 16px rgba(99,102,241,0.35)" }}
                >
                  {loading ? "Launching…" : <><Rocket style={{ height: "16px", width: "16px" }} /> Launch my brief</>}
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}

function ErrorMsg({ message }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
      style={{ background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)", color: "#DC2626", fontSize: "13px", padding: "10px 14px", borderRadius: "10px", marginTop: "16px" }}
    >
      {message}
    </motion.div>
  );
}
