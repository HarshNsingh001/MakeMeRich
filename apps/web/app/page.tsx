"use client";

import { useEffect, useState } from "react";

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
        padding: "4px 12px",
        borderRadius: 99,
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
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
  value: string;
  sub?: string;
  positive?: boolean | null;
}) {
  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "20px 24px",
        transition: "border-color 0.2s",
      }}
      onMouseEnter={(e) =>
        ((e.currentTarget as HTMLElement).style.borderColor = "var(--border-light)")
      }
      onMouseLeave={(e) =>
        ((e.currentTarget as HTMLElement).style.borderColor = "var(--border)")
      }
    >
      <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, letterSpacing: "0.05em", textTransform: "uppercase" }}>
        {label}
      </div>
      <div
        className="font-mono"
        style={{
          fontSize: 24,
          fontWeight: 700,
          color:
            positive === true
              ? "var(--accent-green)"
              : positive === false
              ? "var(--accent-red)"
              : "var(--text-primary)",
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>
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
        setError("API offline — start the FastAPI server on port 8000");
        setLoading(false);
      });
  }, []);

  const fmt = (n: number | null, dec = 2) =>
    n == null ? "—" : n.toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec });

  return (
    <div style={{ padding: "40px 48px", maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", marginBottom: 6 }}>
          Market Pulse
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
          Real-time Indian equity market overview — evidence-based regime classification
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div
          style={{
            background: "var(--accent-red-glow)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 10,
            padding: "14px 20px",
            color: "var(--accent-red)",
            fontSize: 14,
            marginBottom: 28,
          }}
        >
          ⚠ {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !error && (
        <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading market data...</div>
      )}

      {/* Market overview */}
      {market && !loading && (
        <div className="animate-fade-in-up">
          {/* Regime banner */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 14,
              padding: "24px 28px",
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                Market Regime
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <RegimeBadge regime={market.regime} />
                {market.regime_confidence != null && (
                  <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    {(market.regime_confidence * 100).toFixed(0)}% confidence
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>NIFTY 50</div>
                <div className="font-mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>
                  {fmt(market.nifty_close)}
                </div>
                {market.nifty_change_pct != null && (
                  <div
                    className="font-mono"
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: market.nifty_change_pct >= 0 ? "var(--accent-green)" : "var(--accent-red)",
                    }}
                  >
                    {market.nifty_change_pct >= 0 ? "+" : ""}
                    {fmt(market.nifty_change_pct)}%
                  </div>
                )}
              </div>

              <div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>India VIX</div>
                <div className="font-mono" style={{ fontSize: 22, fontWeight: 700,
                  color: market.india_vix != null && market.india_vix > 20 ? "var(--accent-red)" : "var(--text-primary)" }}>
                  {fmt(market.india_vix)}
                </div>
              </div>
            </div>
          </div>

          {/* Stats grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: 14,
              marginBottom: 28,
            }}
          >
            <StatCard
              label="EMA 50"
              value={fmt(market.nifty_ema_50)}
              sub="50-day EMA"
            />
            <StatCard
              label="EMA 200"
              value={fmt(market.nifty_ema_200)}
              sub="200-day EMA"
            />
            <StatCard
              label="Adv / Dec Ratio"
              value={market.advance_decline_ratio != null ? fmt(market.advance_decline_ratio) : "—"}
              sub={
                market.advances != null && market.declines != null
                  ? `${market.advances} adv · ${market.declines} dec`
                  : undefined
              }
              positive={
                market.advance_decline_ratio != null
                  ? market.advance_decline_ratio > 1
                  : null
              }
            />
          </div>

          {/* Disclaimer */}
          <div
            style={{
              padding: "12px 18px",
              background: "rgba(59,130,246,0.06)",
              border: "1px solid rgba(59,130,246,0.15)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--text-muted)",
            }}
          >
            This is a decision-support tool. Market regime is computed from NIFTY EMAs, India VIX and
            advance/decline breadth. It is not a trading signal or financial advice.
          </div>
        </div>
      )}

      {/* No data state */}
      {market && !loading && market.nifty_close == null && (
        <div
          style={{
            marginTop: 20,
            padding: "20px 24px",
            background: "var(--bg-card)",
            borderRadius: 12,
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
            fontSize: 14,
          }}
        >
          No market data yet. Run the ingestion pipeline to populate NIFTY data.
        </div>
      )}
    </div>
  );
}
