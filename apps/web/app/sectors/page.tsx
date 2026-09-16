"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface SectorStat {
  sector: string;
  peer_count: number;
  pe_median: number | null;
  pe_mean: number | null;
  pe_p25: number | null;
  pe_p75: number | null;
  pb_median: number | null;
}

const PE_MAX = 60; // for bar scaling

function PeBar({ value, max = PE_MAX, color }: { value: number | null; max?: number; color: string }) {
  const pct = value == null ? 0 : Math.min((value / max) * 100, 100);
  return (
    <div style={{ height: 6, background: "var(--border)", borderRadius: 4, overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.6s cubic-bezier(0.23,1,0.32,1)" }} />
    </div>
  );
}

function ValuationBadge({ pe }: { pe: number | null }) {
  if (pe == null) return null;
  const label = pe < 15 ? "CHEAP" : pe < 30 ? "FAIR" : "PRICEY";
  const color = pe < 15 ? "var(--accent-green)" : pe < 30 ? "var(--accent-yellow)" : "var(--accent-red)";
  return (
    <span style={{ padding: "3px 8px", borderRadius: 6, fontSize: 10, fontWeight: 700, color, background: `color-mix(in srgb, ${color} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${color} 20%, transparent)` }}>
      {label}
    </span>
  );
}

const SECTOR_COLORS: Record<string, string> = {
  "Financial Services": "#6366f1",
  "Technology": "#06b6d4",
  "Energy": "#f59e0b",
  "Healthcare": "#10b981",
  "Consumer Cyclical": "#a855f7",
  "Consumer Defensive": "#ec4899",
  "Industrials": "#8b5cf6",
  "Basic Materials": "#f97316",
  "Utilities": "#14b8a6",
  "Real Estate": "#84cc16",
  "Communication Services": "#3b82f6",
};

const barColor = (sector: string) => SECTOR_COLORS[sector] ?? "var(--accent-blue-bright)";

export default function SectorsPage() {
  const [sectors, setSectors] = useState<SectorStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"pe_median" | "pe_p25" | "pb_median" | "peer_count">("pe_median");
  const [filterMin, setFilterMin] = useState("");
  const [filterMax, setFilterMax] = useState("");

  useEffect(() => {
    fetch("/api/stocks/sectors/summary")
      .then(r => r.json())
      .then((d: SectorStat[]) => { setSectors(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const sorted = [...sectors]
    .filter(s => {
      const v = s[sortBy] ?? 0;
      if (filterMin && v < parseFloat(filterMin)) return false;
      if (filterMax && v > parseFloat(filterMax)) return false;
      return true;
    })
    .sort((a, b) => (a[sortBy] ?? 999) - (b[sortBy] ?? 999));

  const cheapest = sorted[0];
  const priciest = sorted[sorted.length - 1];

  const inputStyle: React.CSSProperties = { padding: "7px 12px", background: "var(--bg-secondary)", border: "1px solid var(--border-light)", borderRadius: 8, color: "var(--text-primary)", fontSize: 12, outline: "none", width: 90 };

  return (
    <div style={{ padding: "40px 48px", maxWidth: 1300, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.03em", color: "var(--text-primary)", marginBottom: 6 }}>
          Sector Rotation Dashboard
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
          Sector-relative valuation — median PE sorted cheapest to most expensive. Cached hourly.
        </p>
      </div>

      {/* Summary cards */}
      {!loading && sectors.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, marginBottom: 32 }}>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8, fontWeight: 600 }}>Cheapest Sector</div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--accent-green)", marginBottom: 4 }}>{cheapest?.sector ?? "—"}</div>
            <div className="font-mono" style={{ fontSize: 14, color: "var(--text-secondary)" }}>Median PE: {cheapest?.pe_median?.toFixed(1) ?? "—"}</div>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8, fontWeight: 600 }}>Most Expensive</div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--accent-red)", marginBottom: 4 }}>{priciest?.sector ?? "—"}</div>
            <div className="font-mono" style={{ fontSize: 14, color: "var(--text-secondary)" }}>Median PE: {priciest?.pe_median?.toFixed(1) ?? "—"}</div>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8, fontWeight: 600 }}>Sectors Tracked</div>
            <div style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", letterSpacing: "-0.03em" }}>{sectors.length}</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{sectors.reduce((a, b) => a + b.peer_count, 0)} stocks total</div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div style={{ display: "flex", gap: 16, marginBottom: 24, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 500 }}>Sort by:</div>
        {(["pe_median", "pe_p25", "pb_median", "peer_count"] as const).map(key => (
          <button key={key} onClick={() => setSortBy(key)} style={{ padding: "6px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer", border: "1px solid", borderColor: sortBy === key ? "var(--accent-blue)" : "var(--border-light)", background: sortBy === key ? "rgba(99,102,241,0.12)" : "var(--bg-secondary)", color: sortBy === key ? "var(--accent-blue-bright)" : "var(--text-secondary)" }}>
            {key === "pe_median" ? "PE Median" : key === "pe_p25" ? "PE P25 (cheap zone)" : key === "pb_median" ? "PB Median" : "Stock Count"}
          </button>
        ))}
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>PE range:</span>
          <input type="number" placeholder="Min" value={filterMin} onChange={e => setFilterMin(e.target.value)} style={inputStyle} />
          <span style={{ color: "var(--text-muted)" }}>–</span>
          <input type="number" placeholder="Max" value={filterMax} onChange={e => setFilterMax(e.target.value)} style={inputStyle} />
        </div>
      </div>

      {/* Sector table */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[1,2,3,4,5].map(i => <div key={i} className="skeleton" style={{ height: 90, borderRadius: 12 }} />)}
        </div>
      ) : sorted.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-muted)" }}>No sector data available.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {sorted.map((s, rank) => {
            const color = barColor(s.sector);
            return (
              <div key={s.sector} className="card" style={{ padding: "20px 24px", display: "grid", gridTemplateColumns: "32px 220px 1fr 1fr 1fr 120px", gap: 20, alignItems: "center" }}>
                {/* Rank */}
                <div className="font-mono" style={{ fontSize: 14, color: "var(--text-muted)", fontWeight: 700 }}>#{rank + 1}</div>

                {/* Sector name */}
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>{s.sector}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{s.peer_count} stocks</div>
                </div>

                {/* PE Median + bar */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>PE Median</span>
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <span className="font-mono" style={{ fontSize: 13, fontWeight: 700, color }}>{s.pe_median?.toFixed(1) ?? "—"}</span>
                      <ValuationBadge pe={s.pe_median} />
                    </div>
                  </div>
                  <PeBar value={s.pe_median} color={color} />
                </div>

                {/* PE P25 / P75 */}
                <div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>PE Range (P25 – P75)</div>
                  <div className="font-mono" style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    {s.pe_p25?.toFixed(1) ?? "—"} — {s.pe_p75?.toFixed(1) ?? "—"}
                  </div>
                  <div style={{ marginTop: 6, height: 4, background: "var(--border)", borderRadius: 4, position: "relative" }}>
                    {s.pe_p25 != null && s.pe_p75 != null && (
                      <div style={{ position: "absolute", left: `${(s.pe_p25 / PE_MAX) * 100}%`, width: `${((s.pe_p75 - s.pe_p25) / PE_MAX) * 100}%`, height: "100%", background: color, opacity: 0.5, borderRadius: 4 }} />
                    )}
                  </div>
                </div>

                {/* PB */}
                <div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>PB Median</div>
                  <div className="font-mono" style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>{s.pb_median?.toFixed(2) ?? "—"}</div>
                </div>

                {/* Screen this sector */}
                <div style={{ textAlign: "right" }}>
                  <Link href={`/stocks?sector=${encodeURIComponent(s.sector)}`} style={{ padding: "6px 14px", background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: 8, fontSize: 12, color: "var(--accent-blue-bright)", fontWeight: 600, whiteSpace: "nowrap" }}>
                    Screen →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Disclaimer */}
      <div style={{ marginTop: 40, padding: "12px 16px", background: "rgba(99,102,241,0.04)", border: "1px solid rgba(99,102,241,0.12)", borderRadius: 8, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
        <strong style={{ color: "var(--accent-blue-bright)" }}>Note:</strong> Sector PE is computed from the latest available `Fundamental` snapshot per stock, PiT-safe. Only stocks with positive PE are included. Cached for 1 hour. Sector classification is from instrument master. This is a quantitative signal — not a buy/sell recommendation.
      </div>
    </div>
  );
}
