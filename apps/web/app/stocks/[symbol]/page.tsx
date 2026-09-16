"use client";

import { useState, use, useEffect } from "react";
import Link from "next/link";

/* ── Types ────────────────────────────────────────────────── */
interface Quote {
  ltp: number; open: number; high: number; low: number; close: number;
  volume: number; change: number; change_pct: number; quote_timestamp: string;
}
interface Technical {
  rsi_14: number | null; adx_14: number | null; ema_50: number | null;
  ema_200: number | null; macd: number | null; macd_signal: number | null;
  bb_upper: number | null; bb_lower: number | null; volume_ratio: number | null;
  atr_14: number | null;
}
interface Fundamentals {
  pe_ratio: number | null; pb_ratio: number | null; ev_ebitda: number | null;
  dividend_yield: number | null; promoter_holding_pct: number | null;
  fii_holding_pct: number | null; dii_holding_pct: number | null;
  market_cap: number | null; book_value: number | null; as_of_date: string;
}
interface SectorValuation {
  sector: string; pe_percentile: number | null; valuation_label: string;
  sector_pe_median: number | null; discount_to_median_pct: number | null;
  peer_count: number;
}
interface AgentEvidence {
  thesis?: string; signals?: Record<string, string>; confidence?: number;
  raw_evidence?: Array<{ metric: string; value: string | number; interpretation: string }>;
}
interface AnalysisResult {
  symbol: string; sector: string | null;
  sector_valuation: SectorValuation | null;
  opportunity_state: {
    opportunity_level: string; confidence: number; risk_level: string;
    time_horizon: string; evidence_strength: number;
    supporting_factors: string[]; contradictory_factors: string[];
    invalidation_conditions: string[];
  } | null;
  evidence: {
    market_regime: AgentEvidence | null; historical: AgentEvidence | null;
    technical: AgentEvidence | null; fundamental: AgentEvidence | null;
    entry: AgentEvidence | null; risk: AgentEvidence | null;
  };
  critic_feedback: string | null; is_valid: boolean;
}

/* ── Helpers ─────────────────────────────────────────────── */
const fmt = (n: number | null | undefined, dec = 2) =>
  n == null ? "—" : n.toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec });

const crore = (n: number | null) =>
  n == null ? "—" : n >= 1e7 ? `₹${(n / 1e7).toFixed(0)} Cr` : fmt(n, 0);

/* ── Sub-components ──────────────────────────────────────── */
function KVRow({ label, value, color }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>{label}</span>
      <span style={{ fontSize: 14, fontWeight: 600, color: color ?? "var(--text-primary)", fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
    </div>
  );
}

function GaugeMeter({ value, label, low = 30, high = 70 }: { value: number | null; label: string; low?: number; high?: number }) {
  if (value == null) return <div style={{ fontSize: 13, color: "var(--text-muted)" }}>—</div>;
  const color = value < low ? "var(--accent-green)" : value > high ? "var(--accent-red)" : "var(--accent-yellow)";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{label}</span>
        <span className="font-mono" style={{ fontSize: 13, color, fontWeight: 700 }}>{fmt(value, 1)}</span>
      </div>
      <div style={{ height: 4, background: "var(--border)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(value, 100)}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.6s" }} />
      </div>
    </div>
  );
}

function SectorValuationCard({ sv }: { sv: SectorValuation }) {
  const labelColor = sv.valuation_label === "CHEAP" ? "var(--accent-green)" :
    sv.valuation_label === "EXPENSIVE" ? "var(--accent-red)" : "var(--accent-yellow)";
  const pct = sv.pe_percentile ?? 50;
  return (
    <div className="card" style={{ padding: 20, marginBottom: 20 }}>
      <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12, fontWeight: 600 }}>
        Sector Valuation vs Peers
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <span style={{ padding: "4px 12px", borderRadius: 99, fontSize: 13, fontWeight: 700, color: labelColor, background: `color-mix(in srgb, ${labelColor} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${labelColor} 25%, transparent)` }}>
          {sv.valuation_label}
        </span>
        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{sv.sector}</span>
        <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: "auto" }}>{sv.peer_count} peers</span>
      </div>
      {/* Percentile track */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Cheapest</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Most Expensive</span>
        </div>
        <div style={{ position: "relative", height: 6, background: "var(--border)", borderRadius: 4 }}>
          <div style={{ position: "absolute", left: `${pct}%`, top: -3, width: 12, height: 12, borderRadius: "50%", background: labelColor, transform: "translateX(-50%)", boxShadow: `0 0 8px ${labelColor}` }} />
        </div>
        <div style={{ textAlign: "center", marginTop: 8, fontSize: 12, color: "var(--text-secondary)" }}>
          PE Percentile: <span className="font-mono" style={{ color: labelColor, fontWeight: 700 }}>{fmt(sv.pe_percentile, 1)}</span>
          {sv.discount_to_median_pct != null && (
            <span style={{ marginLeft: 12, color: sv.discount_to_median_pct < 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
              ({sv.discount_to_median_pct > 0 ? "+" : ""}{fmt(sv.discount_to_median_pct, 1)}% vs sector median PE {fmt(sv.sector_pe_median, 1)})
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function AgentCard({ name, evidence, icon }: { name: string; evidence: AgentEvidence | null; icon: string }) {
  const [open, setOpen] = useState(false);
  const conf = evidence?.confidence;
  const confColor = conf == null ? "var(--text-muted)" : conf > 0.65 ? "var(--accent-green)" : conf > 0.4 ? "var(--accent-yellow)" : "var(--accent-red)";
  return (
    <div className="card" style={{ marginBottom: 12, overflow: "hidden" }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{ width: "100%", padding: "16px 20px", display: "flex", alignItems: "center", gap: 12, background: "none", border: "none", cursor: "pointer", textAlign: "left" }}
      >
        <span style={{ fontSize: 20 }}>{icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{name}</div>
          {evidence?.thesis && (
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.4, maxWidth: 480 }}>
              {evidence.thesis.slice(0, 120)}{evidence.thesis.length > 120 ? "…" : ""}
            </div>
          )}
        </div>
        {conf != null && (
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>Confidence</div>
            <div className="font-mono" style={{ fontSize: 18, fontWeight: 800, color: confColor }}>{(conf * 100).toFixed(0)}%</div>
          </div>
        )}
        <span style={{ color: "var(--text-muted)", fontSize: 16, marginLeft: 8 }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && evidence && (
        <div style={{ padding: "0 20px 20px", borderTop: "1px solid var(--border)" }}>
          {/* Signals */}
          {evidence.signals && Object.keys(evidence.signals).length > 0 && (
            <div style={{ marginTop: 16, marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10, fontWeight: 600 }}>Signals</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {Object.entries(evidence.signals).map(([k, v]) => (
                  <span key={k} style={{ padding: "4px 10px", background: "var(--bg-secondary)", border: "1px solid var(--border-light)", borderRadius: 6, fontSize: 12, color: "var(--text-primary)" }}>
                    <span style={{ color: "var(--text-muted)" }}>{k}: </span>{v}
                  </span>
                ))}
              </div>
            </div>
          )}
          {/* Full thesis */}
          {evidence.thesis && (
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8, fontWeight: 600 }}>Full Thesis</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7, background: "var(--bg-secondary)", padding: "12px 16px", borderRadius: 8, border: "1px solid var(--border-light)" }}>
                {evidence.thesis}
              </div>
            </div>
          )}
          {/* Raw evidence */}
          {evidence.raw_evidence && evidence.raw_evidence.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8, fontWeight: 600 }}>Data Points</div>
              {evidence.raw_evidence.map((e, i) => (
                <div key={i} style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 12, color: "var(--accent-blue-bright)", fontWeight: 600, minWidth: 80 }}>{e.metric}</span>
                  <span className="font-mono" style={{ fontSize: 12, color: "var(--text-primary)", minWidth: 60 }}>{String(e.value)}</span>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", flex: 1 }}>{e.interpretation}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EntryZonesView({ evidence }: { evidence: AgentEvidence | null }) {
  if (!evidence) return (
    <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-muted)" }}>
      <div style={{ fontSize: 40, marginBottom: 12 }}>📍</div>
      <div>Run AI Analysis to generate entry zones</div>
    </div>
  );

  // Parse entry zones from raw_evidence
  const zones = evidence.raw_evidence ?? [];
  const thesis = evidence.thesis ?? "";

  return (
    <div>
      {/* Thesis */}
      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10, fontWeight: 600 }}>Entry Agent Thesis</div>
        <div style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.7 }}>{thesis || "No thesis generated."}</div>
      </div>

      {/* Signal-based zones */}
      {zones.length > 0 ? (
        <div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12, fontWeight: 600 }}>Evidence Points</div>
          {zones.map((z, i) => (
            <div key={i} className="card" style={{ padding: "14px 18px", marginBottom: 8, display: "flex", gap: 16, alignItems: "flex-start" }}>
              <div style={{ width: 3, background: i === 0 ? "var(--accent-green)" : "var(--accent-blue)", borderRadius: 4, alignSelf: "stretch", flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--accent-blue-bright)", marginBottom: 4 }}>{z.metric}</div>
                <div className="font-mono" style={{ fontSize: 14, color: "var(--text-primary)", marginBottom: 4 }}>{String(z.value)}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{z.interpretation}</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)", fontSize: 13 }}>
          Entry zone data is embedded in the agent thesis above.
        </div>
      )}

      {/* Disclaimer */}
      <div style={{ marginTop: 20, padding: "12px 16px", background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: 8, fontSize: 12, color: "var(--accent-yellow)", lineHeight: 1.5 }}>
        ⚠ Entry zones are derived from historical support levels, ATR bands, and moving averages. They represent areas of potential interest — not guaranteed support. Always size positions appropriately.
      </div>
    </div>
  );
}

function RiskView({ evidence, opp }: { evidence: AgentEvidence | null; opp: AnalysisResult["opportunity_state"] }) {
  const invalidations = opp?.invalidation_conditions ?? [];
  const contradictory = opp?.contradictory_factors ?? [];
  const supporting = opp?.supporting_factors ?? [];

  return (
    <div>
      {/* Risk level banner */}
      {opp && (
        <div className="card" style={{ padding: "20px 24px", marginBottom: 20, display: "flex", gap: 40, alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Risk Level</div>
            <span style={{ padding: "6px 14px", borderRadius: 99, fontSize: 14, fontWeight: 700, color: opp.risk_level === "HIGH" ? "var(--accent-red)" : opp.risk_level === "LOW" ? "var(--accent-green)" : "var(--accent-yellow)", background: opp.risk_level === "HIGH" ? "rgba(239,68,68,0.1)" : opp.risk_level === "LOW" ? "rgba(16,185,129,0.1)" : "rgba(245,158,11,0.1)", border: `1px solid ${opp.risk_level === "HIGH" ? "rgba(239,68,68,0.3)" : opp.risk_level === "LOW" ? "rgba(16,185,129,0.3)" : "rgba(245,158,11,0.3)"}` }}>
              {opp.risk_level}
            </span>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Evidence Strength</div>
            <div className="font-mono" style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>{(opp.evidence_strength * 100).toFixed(0)}%</div>
          </div>
        </div>
      )}

      {/* Risk agent thesis */}
      {evidence?.thesis && (
        <div className="card" style={{ padding: 20, marginBottom: 20, borderColor: "rgba(239,68,68,0.2)" }}>
          <div style={{ fontSize: 11, color: "var(--accent-red)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10, fontWeight: 600 }}>Bear / Risk Thesis</div>
          <div style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.7 }}>{evidence.thesis}</div>
        </div>
      )}

      {/* Invalidation conditions */}
      {invalidations.length > 0 && (
        <div className="card" style={{ padding: 20, marginBottom: 16, borderColor: "rgba(239,68,68,0.15)" }}>
          <div style={{ fontSize: 12, color: "var(--accent-red)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14, fontWeight: 700 }}>🚨 Invalidation Conditions</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {invalidations.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 12px", background: "rgba(239,68,68,0.05)", borderRadius: 8, border: "1px solid rgba(239,68,68,0.1)" }}>
                <span style={{ color: "var(--accent-red)", fontSize: 14, flexShrink: 0 }}>✕</span>
                <span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contradictory factors */}
      {contradictory.length > 0 && (
        <div className="card" style={{ padding: 20, marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: "var(--accent-yellow)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14, fontWeight: 700 }}>⚠ Contradictory Factors</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {contradictory.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 12px", background: "rgba(245,158,11,0.05)", borderRadius: 8 }}>
                <span style={{ color: "var(--accent-yellow)", fontSize: 14, flexShrink: 0 }}>△</span>
                <span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supporting factors */}
      {supporting.length > 0 && (
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontSize: 12, color: "var(--accent-green)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14, fontWeight: 700 }}>✓ Supporting Factors</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {supporting.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 12px", background: "rgba(16,185,129,0.05)", borderRadius: 8 }}>
                <span style={{ color: "var(--accent-green)", fontSize: 14, flexShrink: 0 }}>✓</span>
                <span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────── */
export default function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const resolvedParams = use(params);
  const symbol = resolvedParams.symbol.toUpperCase();

  const [tab, setTab] = useState<"overview" | "technical" | "fundamentals" | "entry" | "debate" | "risk">("overview");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [tech, setTech] = useState<Technical | null>(null);
  const [fund, setFund] = useState<Fundamentals | null>(null);
  const [sv, setSv] = useState<SectorValuation | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [loadingData, setLoadingData] = useState(true);

  // Load market data
  useEffect(() => {
    const load = async () => {
      setLoadingData(true);
      try {
        const [qr, tr, fr, svr] = await Promise.allSettled([
          fetch(`/api/stocks/${symbol}`).then(r => r.json()),
          fetch(`/api/stocks/${symbol}/technical`).then(r => r.json()),
          fetch(`/api/stocks/${symbol}/fundamentals`).then(r => r.json()),
          fetch(`/api/stocks/${symbol}/sector-valuation`).then(r => r.json()),
        ]);
        if (qr.status === "fulfilled" && qr.value?.quote) setQuote(qr.value.quote);
        if (tr.status === "fulfilled" && !tr.value?.detail) setTech(tr.value);
        if (fr.status === "fulfilled" && !fr.value?.detail) setFund(fr.value);
        if (svr.status === "fulfilled" && !svr.value?.detail) setSv(svr.value);
      } catch {}
      setLoadingData(false);
    };
    load();
  }, [symbol]);

  const runAnalysis = () => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    setAnalysis(null);
    setElapsed(0);
    const iv = setInterval(() => setElapsed(e => e + 1), 1000);
    fetch(`/api/stocks/${symbol}/analysis`)
      .then(r => r.json())
      .then(d => {
        clearInterval(iv);
        if (d.detail) throw new Error(d.detail);
        setAnalysis(d);
        setAnalysisLoading(false);
        if (tab === "overview") setTab("debate");
      })
      .catch(e => {
        clearInterval(iv);
        setAnalysisError(e.message || "Analysis failed.");
        setAnalysisLoading(false);
      });
  };

  const opp = analysis?.opportunity_state;
  const oppColor = !opp ? "var(--text-muted)" :
    opp.opportunity_level === "HIGH" ? "var(--accent-green)" :
    opp.opportunity_level === "MODERATE" ? "var(--accent-yellow)" : "var(--accent-red)";

  const TABS = [
    { id: "overview", label: "Overview" },
    { id: "technical", label: "Technical" },
    { id: "fundamentals", label: "Fundamentals" },
    { id: "entry", label: "Entry Zones" },
    { id: "debate", label: "Agent Debate" },
    { id: "risk", label: "Risk & Invalidation" },
  ] as const;

  return (
    <div style={{ padding: "40px 48px", maxWidth: 1400, margin: "0 auto" }}>
      {/* Breadcrumb */}
      <Link href="/stocks" style={{ color: "var(--text-muted)", fontSize: 13, fontWeight: 500, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 20 }}>
        ← Stock Screener
      </Link>

      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 36, fontWeight: 900, letterSpacing: "-0.04em", color: "var(--text-primary)", marginBottom: 6 }}>
            {symbol}
          </h1>
          {sv && (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{sv.sector}</span>
              <span style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--text-muted)" }} />
              <span style={{ padding: "2px 8px", borderRadius: 6, fontSize: 12, fontWeight: 700,
                color: sv.valuation_label === "CHEAP" ? "var(--accent-green)" : sv.valuation_label === "EXPENSIVE" ? "var(--accent-red)" : "var(--accent-yellow)",
                background: sv.valuation_label === "CHEAP" ? "rgba(16,185,129,0.1)" : sv.valuation_label === "EXPENSIVE" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)",
              }}>
                {sv.valuation_label} vs peers
              </span>
            </div>
          )}
        </div>

        {/* Quote */}
        {quote ? (
          <div style={{ textAlign: "right" }}>
            <div className="font-mono" style={{ fontSize: 36, fontWeight: 900, letterSpacing: "-0.04em", color: "var(--text-primary)" }}>
              ₹{fmt(quote.ltp)}
            </div>
            <div className="font-mono" style={{ fontSize: 15, fontWeight: 600, color: quote.change_pct >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
              {quote.change_pct >= 0 ? "▲" : "▼"} {Math.abs(quote.change_pct).toFixed(2)}% ({quote.change >= 0 ? "+" : ""}{fmt(quote.change)})
            </div>
          </div>
        ) : loadingData ? (
          <div className="skeleton" style={{ width: 160, height: 60 }} />
        ) : null}
      </div>

      {/* AI Analysis trigger / result header */}
      {!analysis && !analysisLoading && (
        <div style={{ padding: "14px 20px", background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: 10, marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            🧠 Run the 8-node AI pipeline to unlock Agent Debate, Entry Zones and Risk views
          </div>
          <button onClick={runAnalysis} style={{ padding: "8px 20px", background: "var(--accent-blue)", color: "#fff", borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: "pointer", border: "none", boxShadow: "0 4px 14px var(--accent-blue-glow)", flexShrink: 0 }}>
            Run AI Analysis →
          </button>
        </div>
      )}

      {analysisLoading && (
        <div style={{ padding: "14px 20px", background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: 10, marginBottom: 24, display: "flex", alignItems: "center", gap: 14 }}>
          <div className="ai-spinner" />
          <span style={{ fontSize: 13, color: "var(--accent-blue-bright)", fontWeight: 500 }}>AI agents are reasoning… {elapsed}s</span>
        </div>
      )}

      {analysisError && (
        <div style={{ padding: "12px 18px", background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 10, marginBottom: 20, color: "var(--accent-red)", fontSize: 13 }}>
          ⚠ {analysisError}
        </div>
      )}

      {opp && (
        <div style={{ padding: "16px 24px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 10, marginBottom: 24, display: "flex", gap: 40, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>AI Opportunity</div>
            <span style={{ padding: "5px 14px", borderRadius: 99, fontSize: 15, fontWeight: 800, color: oppColor, background: `color-mix(in srgb, ${oppColor} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${oppColor} 25%, transparent)` }}>
              {opp.opportunity_level}
            </span>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Confidence</div>
            <div className="font-mono" style={{ fontSize: 22, fontWeight: 900, color: "var(--text-primary)" }}>{(opp.confidence * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Risk</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: opp.risk_level === "HIGH" ? "var(--accent-red)" : opp.risk_level === "LOW" ? "var(--accent-green)" : "var(--accent-yellow)" }}>{opp.risk_level}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Time Horizon</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>{opp.time_horizon}</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 28, borderBottom: "1px solid var(--border)", paddingBottom: 0 }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "10px 18px", fontSize: 13, fontWeight: 600, border: "none", background: "none", cursor: "pointer",
              color: tab === t.id ? "var(--accent-blue-bright)" : "var(--text-secondary)",
              borderBottom: tab === t.id ? "2px solid var(--accent-blue)" : "2px solid transparent",
              marginBottom: -1, transition: "all 0.15s",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in-up" key={tab}>

        {/* ── OVERVIEW ─────────────────────────────────────── */}
        {tab === "overview" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <div>
              {sv && <SectorValuationCard sv={sv} />}
              {/* Quote stats */}
              <div className="card" style={{ padding: 20 }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12, fontWeight: 600 }}>Price Details</div>
                {quote ? (
                  <>
                    <KVRow label="Open" value={`₹${fmt(quote.open)}`} />
                    <KVRow label="Day High" value={`₹${fmt(quote.high)}`} color="var(--accent-green)" />
                    <KVRow label="Day Low" value={`₹${fmt(quote.low)}`} color="var(--accent-red)" />
                    <KVRow label="Prev Close" value={`₹${fmt(quote.close)}`} />
                    <KVRow label="Volume" value={quote.volume?.toLocaleString("en-IN") ?? "—"} />
                  </>
                ) : <div className="skeleton" style={{ height: 160 }} />}
              </div>
            </div>
            <div>
              {/* Quick technicals */}
              <div className="card" style={{ padding: 20, marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16, fontWeight: 600 }}>Quick Technicals</div>
                {tech ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    <GaugeMeter value={tech.rsi_14 ? Number(tech.rsi_14) : null} label="RSI (14)" low={30} high={70} />
                    <GaugeMeter value={tech.adx_14 ? Number(tech.adx_14) : null} label="ADX (14)" low={20} high={40} />
                    <KVRow label="EMA 50" value={`₹${fmt(tech.ema_50 ? Number(tech.ema_50) : null)}`} />
                    <KVRow label="EMA 200" value={`₹${fmt(tech.ema_200 ? Number(tech.ema_200) : null)}`} />
                    <KVRow label="Volume Ratio" value={fmt(tech.volume_ratio ? Number(tech.volume_ratio) : null)} color={tech.volume_ratio && Number(tech.volume_ratio) > 1.2 ? "var(--accent-green)" : undefined} />
                  </div>
                ) : <div className="skeleton" style={{ height: 180 }} />}
              </div>
              {/* Quick fundamentals */}
              <div className="card" style={{ padding: 20 }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12, fontWeight: 600 }}>Quick Fundamentals</div>
                {fund ? (
                  <>
                    <KVRow label="P/E Ratio" value={fmt(fund.pe_ratio)} />
                    <KVRow label="P/B Ratio" value={fmt(fund.pb_ratio)} />
                    <KVRow label="Market Cap" value={crore(fund.market_cap)} />
                    <KVRow label="Promoter Holding" value={`${fmt(fund.promoter_holding_pct, 1)}%`} />
                  </>
                ) : <div className="skeleton" style={{ height: 160 }} />}
              </div>
            </div>
          </div>
        )}

        {/* ── TECHNICAL ────────────────────────────────────── */}
        {tab === "technical" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <div className="card" style={{ padding: 24 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 18, fontWeight: 600 }}>Momentum</div>
              {tech ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <GaugeMeter value={tech.rsi_14 ? Number(tech.rsi_14) : null} label="RSI (14)" />
                  <GaugeMeter value={tech.adx_14 ? Number(tech.adx_14) : null} label="ADX (14) — Trend Strength" low={20} high={50} />
                  <KVRow label="MACD" value={fmt(tech.macd ? Number(tech.macd) : null)} color={tech.macd && Number(tech.macd) > 0 ? "var(--accent-green)" : "var(--accent-red)"} />
                  <KVRow label="MACD Signal" value={fmt(tech.macd_signal ? Number(tech.macd_signal) : null)} />
                  <KVRow label="ATR (14)" value={fmt(tech.atr_14 ? Number(tech.atr_14) : null)} />
                  <KVRow label="Volume Ratio" value={fmt(tech.volume_ratio ? Number(tech.volume_ratio) : null)} color={tech.volume_ratio && Number(tech.volume_ratio) > 1.5 ? "var(--accent-green)" : undefined} />
                </div>
              ) : <div className="skeleton" style={{ height: 220 }} />}
            </div>
            <div className="card" style={{ padding: 24 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 18, fontWeight: 600 }}>Trend</div>
              {tech && quote ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {[
                    { label: "EMA 50", val: tech.ema_50 },
                    { label: "EMA 200", val: tech.ema_200 },
                    { label: "BB Upper", val: tech.bb_upper },
                    { label: "BB Lower", val: tech.bb_lower },
                  ].map(({ label, val }) => {
                    const v = val ? Number(val) : null;
                    const pos = v != null ? (quote.ltp > v ? "var(--accent-green)" : "var(--accent-red)") : undefined;
                    return <KVRow key={label} label={label} value={`₹${fmt(v)}`} color={pos} />;
                  })}
                  <div style={{ marginTop: 12, padding: "12px", background: "var(--bg-secondary)", borderRadius: 8, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
                    Green = LTP is above this level (bullish context) | Red = LTP is below (bearish context)
                  </div>
                </div>
              ) : <div className="skeleton" style={{ height: 220 }} />}
            </div>
          </div>
        )}

        {/* ── FUNDAMENTALS ─────────────────────────────────── */}
        {tab === "fundamentals" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <div>
              <div className="card" style={{ padding: 24, marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 18, fontWeight: 600 }}>Valuation</div>
                {fund ? (
                  <>
                    <KVRow label="P/E Ratio" value={fmt(fund.pe_ratio)} />
                    <KVRow label="P/B Ratio" value={fmt(fund.pb_ratio)} />
                    <KVRow label="EV / EBITDA" value={fmt(fund.ev_ebitda)} />
                    <KVRow label="Dividend Yield" value={`${fmt(fund.dividend_yield, 2)}%`} />
                    <KVRow label="Book Value" value={`₹${fmt(fund.book_value)}`} />
                    <KVRow label="Market Cap" value={crore(fund.market_cap)} />
                  </>
                ) : <div className="skeleton" style={{ height: 200 }} />}
              </div>
              {sv && <SectorValuationCard sv={sv} />}
            </div>
            <div className="card" style={{ padding: 24 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 18, fontWeight: 600 }}>Shareholding</div>
              {fund ? (
                <>
                  {[
                    { label: "Promoter Holding", val: fund.promoter_holding_pct, color: fund.promoter_holding_pct && fund.promoter_holding_pct > 50 ? "var(--accent-green)" : undefined },
                    { label: "FII Holding", val: fund.fii_holding_pct, color: "var(--accent-blue-bright)" },
                    { label: "DII Holding", val: fund.dii_holding_pct, color: "var(--accent-purple)" },
                  ].map(({ label, val, color }) => (
                    <div key={label} style={{ marginBottom: 20 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{label}</span>
                        <span className="font-mono" style={{ fontSize: 14, fontWeight: 700, color: color ?? "var(--text-primary)" }}>{fmt(val, 1)}%</span>
                      </div>
                      <div style={{ height: 6, background: "var(--border)", borderRadius: 4 }}>
                        <div style={{ width: `${Math.min(val ?? 0, 100)}%`, height: "100%", background: color ?? "var(--border-light)", borderRadius: 4 }} />
                      </div>
                    </div>
                  ))}
                </>
              ) : <div className="skeleton" style={{ height: 200 }} />}
            </div>
          </div>
        )}

        {/* ── ENTRY ZONES ──────────────────────────────────── */}
        {tab === "entry" && (
          <div style={{ maxWidth: 760 }}>
            {analysis
              ? <EntryZonesView evidence={analysis.evidence.entry} />
              : (
                <div style={{ textAlign: "center", padding: "80px 0" }}>
                  <div style={{ fontSize: 48, marginBottom: 12 }}>📍</div>
                  <div style={{ fontSize: 16, color: "var(--text-secondary)", marginBottom: 20 }}>Entry zones require AI analysis</div>
                  <button onClick={runAnalysis} disabled={analysisLoading} style={{ padding: "10px 24px", background: "var(--accent-blue)", color: "#fff", borderRadius: 8, fontWeight: 600, cursor: "pointer", border: "none" }}>
                    {analysisLoading ? `Thinking… ${elapsed}s` : "Run AI Analysis →"}
                  </button>
                </div>
              )}
          </div>
        )}

        {/* ── AGENT DEBATE ─────────────────────────────────── */}
        {tab === "debate" && (
          <div style={{ maxWidth: 800 }}>
            {analysis ? (
              <>
                {/* Critic feedback */}
                {analysis.critic_feedback && (
                  <div style={{ padding: "16px 20px", background: "rgba(245,158,11,0.05)", borderLeft: "3px solid var(--accent-yellow)", borderRadius: "0 10px 10px 0", marginBottom: 24, fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    <div style={{ fontSize: 11, color: "var(--accent-yellow)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700, marginBottom: 8 }}>Adversarial Critic</div>
                    {analysis.critic_feedback}
                  </div>
                )}
                {/* All agents */}
                {[
                  { name: "Market Regime", evidence: analysis.evidence.market_regime, icon: "🌐" },
                  { name: "Historical", evidence: analysis.evidence.historical, icon: "📚" },
                  { name: "Technical", evidence: analysis.evidence.technical, icon: "📊" },
                  { name: "Fundamental", evidence: analysis.evidence.fundamental, icon: "💼" },
                  { name: "Entry / Price", evidence: analysis.evidence.entry, icon: "📍" },
                  { name: "Risk / Bear", evidence: analysis.evidence.risk, icon: "⚠" },
                ].map(({ name, evidence, icon }) => (
                  <AgentCard key={name} name={name} evidence={evidence} icon={icon} />
                ))}
              </>
            ) : (
              <div style={{ textAlign: "center", padding: "80px 0" }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>🤖</div>
                <div style={{ fontSize: 16, color: "var(--text-secondary)", marginBottom: 20 }}>Agent evidence requires AI analysis</div>
                <button onClick={runAnalysis} disabled={analysisLoading} style={{ padding: "10px 24px", background: "var(--accent-blue)", color: "#fff", borderRadius: 8, fontWeight: 600, cursor: "pointer", border: "none" }}>
                  {analysisLoading ? `Thinking… ${elapsed}s` : "Run AI Analysis →"}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── RISK & INVALIDATION ──────────────────────────── */}
        {tab === "risk" && (
          <div style={{ maxWidth: 760 }}>
            {analysis
              ? <RiskView evidence={analysis.evidence.risk} opp={opp ?? null} />
              : (
                <div style={{ textAlign: "center", padding: "80px 0" }}>
                  <div style={{ fontSize: 48, marginBottom: 12 }}>⚠️</div>
                  <div style={{ fontSize: 16, color: "var(--text-secondary)", marginBottom: 20 }}>Risk view requires AI analysis</div>
                  <button onClick={runAnalysis} disabled={analysisLoading} style={{ padding: "10px 24px", background: "var(--accent-blue)", color: "#fff", borderRadius: 8, fontWeight: 600, cursor: "pointer", border: "none" }}>
                    {analysisLoading ? `Thinking… ${elapsed}s` : "Run AI Analysis →"}
                  </button>
                </div>
              )}
          </div>
        )}

      </div>

      {/* SEBI Disclaimer */}
      <div style={{ marginTop: 40, padding: "14px 20px", background: "rgba(99,102,241,0.04)", border: "1px solid rgba(99,102,241,0.12)", borderRadius: 10, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
        <strong style={{ color: "var(--accent-blue-bright)" }}>SEBI Disclaimer:</strong> This platform is a decision-support tool only. AI-generated analyses do not constitute financial advice, research reports, or investment recommendations under SEBI (Research Analysts) Regulations, 2014. All opportunity assessments are probabilistic. Past patterns do not guarantee future returns. Users must conduct their own due diligence before making investment decisions.
      </div>
    </div>
  );
}
