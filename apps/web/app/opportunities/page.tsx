"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Opportunity {
  id: number;
  symbol: string;
  opportunity_level: "HIGH" | "MODERATE" | "LOW";
  confidence: number;
  current_price: number;
  time_horizon: string;
  timestamp: string;
}

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/opportunities/today")
      .then((r) => r.json())
      .then((d) => {
        setOpportunities(d);
        setLoading(false);
      })
      .catch((e) => {
        setError("Failed to fetch opportunities.");
        setLoading(false);
      });
  }, []);

  const fmt = (n: number) => n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <div style={{ padding: "48px 64px", maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ marginBottom: 40, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 style={{ fontSize: 36, fontWeight: 800, color: "var(--text-primary)", marginBottom: 8, letterSpacing: "-0.03em" }}>
            AI Opportunities
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 16 }}>
            Top setups identified by the V3 Opportunity Engine today
          </p>
        </div>
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
          }}>
          ⚠ {error}
        </div>
      )}

      {loading && !error && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 24 }}>
          <div className="skeleton" style={{ height: 200 }} />
          <div className="skeleton" style={{ height: 200 }} />
          <div className="skeleton" style={{ height: 200 }} />
        </div>
      )}

      {!loading && !error && opportunities.length === 0 && (
        <div className="card" style={{ padding: "48px", textAlign: "center", borderStyle: "dashed" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🕵️‍♂️</div>
          <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>No Opportunities Yet</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            The AI engine hasn't generated any HIGH/MODERATE opportunities today. Run the batch generator to find setups.
          </p>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 24 }}>
        {opportunities.map((opp, idx) => (
          <Link
            href={`/stocks/${opp.symbol}`}
            key={opp.id}
            className={`card animate-fade-in-up-delay-${(idx % 3) + 1}`}
            style={{ padding: "24px", display: "block", position: "relative", overflow: "hidden" }}
          >
            {opp.opportunity_level === "HIGH" && (
              <div style={{ position: "absolute", top: -30, right: -30, width: 120, height: 120, background: "var(--accent-green)", filter: "blur(50px)", opacity: 0.15, borderRadius: "50%" }} />
            )}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <div className="font-mono" style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                  {opp.symbol}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2, fontWeight: 500 }}>
                  ₹{fmt(opp.current_price)}
                </div>
              </div>
              <span className={`opp-${opp.opportunity_level.toLowerCase()}`} style={{
                padding: "6px 12px",
                borderRadius: 99,
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.08em",
              }}>
                {opp.opportunity_level}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 24, paddingtop: 16, borderTop: "1px solid var(--border)" }}>
              <div style={{ paddingTop: 16 }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Confidence</div>
                <div className="font-mono" style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                  {(opp.confidence * 100).toFixed(0)}%
                </div>
              </div>
              <div style={{ paddingTop: 16 }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Horizon</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
                  {opp.time_horizon}
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
