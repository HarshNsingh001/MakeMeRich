"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface MarketOverview {
  date: string;
  regime: string | null;
  regime_confidence: number | null;
  nifty_close: number | null;
  nifty_change_pct: number | null;
  nifty_ema_50: number | null;
  nifty_ema_200: number | null;
  india_vix: number | null;
  advance_decline_ratio: number | null;
  advances: number | null;
  declines: number | null;
}

function RegimeBadge({ regime }: { regime: string | null }) {
  const label = regime ?? "UNKNOWN";
  const cls = `regime-${label.toLowerCase()}`;
  return (
    <span
      className={cls}
      style={{
        padding: "6px 16px",
        borderRadius: 99,
        fontSize: 13,
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        boxShadow: "0 4px 12px rgba(0,0,0,0.2)"
      }}
    >
      {label}
    </span>
  );
}

function StatCard({
  label,
  value,
  sub,
  positive,
}: {
  label: string;
  value: string | React.ReactNode;
  sub?: string;
  positive?: boolean | null;
}) {
  return (
    <div className="card" style={{ padding: "24px", position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: -20, right: -20, width: 100, height: 100, background: "var(--accent-blue)", filter: "blur(60px)", opacity: 0.1, borderRadius: "50%" }} />
      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8, letterSpacing: "0.05em", textTransform: "uppercase", fontWeight: 600 }}>
        {label}
      </div>
      <div
        className="font-mono"
        style={{
          fontSize: 28,
          fontWeight: 700,
          color:
            positive === true
              ? "var(--accent-green)"
              : positive === false
              ? "var(--accent-red)"
              : "var(--text-primary)",
          letterSpacing: "-0.03em"
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6, fontWeight: 500 }}>{sub}</div>
      )}
    </div>
  );
}

export default function HomePage() {
  const [market, setMarket] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/market/overview")
      .then((r) => r.json())
      .then((d) => {
        setMarket(d);
        setLoading(false);
      })
      .catch((e) => {
        setError("API offline — please start the backend server.");
        setLoading(false);
      });
  }, []);

  const fmt = (n: number | null, dec = 2) =>
    n == null ? "—" : n.toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec });

  return (
    <div style={{ padding: "48px 64px", maxWidth: 1400, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 40, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 style={{ fontSize: 36, fontWeight: 800, color: "var(--text-primary)", marginBottom: 8, letterSpacing: "-0.03em" }}>
            Market Pulse
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 16 }}>
            Real-time Indian equity market regime and breadth
          </p>
        </div>
        
        <Link href="/opportunities" style={{
          padding: "10px 24px",
          background: "var(--accent-blue)",
          color: "#fff",
          borderRadius: 8,
          fontSize: 14,
          fontWeight: 600,
          boxShadow: "0 4px 14px var(--accent-blue-glow)",
          transition: "transform 0.2s, filter 0.2s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.filter = "brightness(1.1)")}
        onMouseLeave={(e) => (e.currentTarget.style.filter = "brightness(1)")}
        >
          View AI Opportunities →
        </Link>
      </div>

      {error && (
        <div style={{
            background: "var(--accent-red-glow)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 12,
            padding: "16px 24px",
            color: "var(--accent-red)",
            fontSize: 15,
            marginBottom: 32,
            fontWeight: 500
          }}>
          ⚠ {error}
        </div>
      )}

      {loading && !error && (
        <div style={{ display: "grid", gap: 24 }}>
          <div className="skeleton" style={{ height: 140 }} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24 }}>
            <div className="skeleton" style={{ height: 120 }} />
            <div className="skeleton" style={{ height: 120 }} />
            <div className="skeleton" style={{ height: 120 }} />
          </div>
        </div>
      )}

      {market && !loading && market.nifty_close != null && (
        <div className="animate-fade-in-up">
          {/* Regime banner */}
          <div className="card card-glow"
            style={{
              padding: "32px 40px",
              marginBottom: 32,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 24,
              background: "linear-gradient(135deg, var(--bg-card) 0%, rgba(99,102,241,0.05) 100%)",
            }}
          >
            <div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 600 }}>
                Current Market Regime
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <RegimeBadge regime={market.regime} />
                {market.regime_confidence != null && (
                  <span style={{ fontSize: 14, color: "var(--text-muted)", fontWeight: 500 }}>
                    {(market.regime_confidence * 100).toFixed(0)}% confidence
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: 48, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6, fontWeight: 500 }}>NIFTY 50</div>
                <div className="font-mono" style={{ fontSize: 32, fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.04em" }}>
                  {fmt(market.nifty_close)}
                </div>
                {market.nifty_change_pct != null && (
                  <div
                    className="font-mono"
                    style={{
                      fontSize: 15,
                      fontWeight: 600,
                      marginTop: 4,
                      color: market.nifty_change_pct >= 0 ? "var(--accent-green)" : "var(--accent-red)",
                    }}
                  >
                    {market.nifty_change_pct >= 0 ? "▲ +" : "▼ "}
                    {fmt(market.nifty_change_pct)}%
                  </div>
                )}
              </div>

              <div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6, fontWeight: 500 }}>India VIX</div>
                <div className="font-mono" style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.04em",
                  color: market.india_vix != null && market.india_vix > 20 ? "var(--accent-red)" : "var(--text-primary)" }}>
                  {fmt(market.india_vix)}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 6, fontWeight: 500 }}>
                  Volatility Index
                </div>
              </div>
            </div>
          </div>

          {/* Stats grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 24,
              marginBottom: 40,
            }}
          >
            <StatCard
              label="EMA 50"
              value={fmt(market.nifty_ema_50)}
              sub="50-day Exponential Moving Average"
            />
            <StatCard
              label="EMA 200"
              value={fmt(market.nifty_ema_200)}
              sub="200-day Trend Indicator"
            />
            <StatCard
              label="Adv / Dec Ratio"
              value={
                market.advance_decline_ratio != null ? (
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    {fmt(market.advance_decline_ratio)}
                    <span style={{ fontSize: 14, color: "var(--text-muted)", fontWeight: 500 }}>x</span>
                  </div>
                ) : "—"
              }
              sub={
                market.advances != null && market.declines != null
                  ? `${market.advances} Advancing · ${market.declines} Declining`
                  : undefined
              }
              positive={
                market.advance_decline_ratio != null
                  ? market.advance_decline_ratio > 1
                  : null
              }
            />
          </div>

          <div
            style={{
              padding: "16px 24px",
              background: "rgba(99,102,241,0.05)",
              border: "1px solid rgba(99,102,241,0.15)",
              borderRadius: 12,
              fontSize: 13,
              color: "var(--text-secondary)",
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: "var(--accent-blue-bright)" }}>Disclaimer:</strong> This is a decision-support tool. Market regime is computed quantitatively from NIFTY EMAs, India VIX and advance/decline breadth. It is not financial advice.
          </div>
        </div>
      )}
    </div>
  );
}
