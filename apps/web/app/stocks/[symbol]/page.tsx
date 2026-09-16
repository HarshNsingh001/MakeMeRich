"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { use } from "react";

interface Quote {
  ltp: number;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  change: number | null;
  change_pct: number | null;
  quote_timestamp: string;
}

interface Instrument {
  symbol: string;
  exchange: string;
  name: string;
  sector: string | null;
  industry: string | null;
  instrument_type: string;
  isin: string | null;
}

interface Technical {
  timeframe: string;
  timestamp: string;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  ema_9: number | null;
  ema_21: number | null;
  ema_50: number | null;
  ema_200: number | null;
  atr_14: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  adx_14: number | null;
  volume_ratio: number | null;
}

interface Fundamentals {
  market_cap: number | null;
  pe_ratio: number | null;
  pb_ratio: number | null;
  ev_ebitda: number | null;
  dividend_yield: number | null;
  promoter_holding_pct: number | null;
  fii_holding_pct: number | null;
  dii_holding_pct: number | null;
}

function MetricRow({ label, value, highlight }: { label: string; value: string; highlight?: "positive" | "negative" | "neutral" }) {
  const color =
    highlight === "positive" ? "var(--accent-green)" :
    highlight === "negative" ? "var(--accent-red)" :
    "var(--text-primary)";
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{label}</span>
      <span className="font-mono" style={{ fontSize: 14, fontWeight: 600, color }}>{value}</span>
    </div>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 24px", marginBottom: 16 }}>
      <h2 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.07em", textTransform: "uppercase", marginBottom: 14 }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

export default function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = use(params);
  const [detail, setDetail] = useState<{ instrument: Instrument; quote: Quote | null } | null>(null);
  const [technical, setTechnical] = useState<Technical | null>(null);
  const [fundamentals, setFundamentals] = useState<Fundamentals | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sym = symbol.toUpperCase();

  useEffect(() => {
    Promise.allSettled([
      fetch(`/api/stocks/${sym}`).then((r) => r.json()),
      fetch(`/api/stocks/${sym}/technical`).then((r) => r.json()),
      fetch(`/api/stocks/${sym}/fundamentals`).then((r) => r.json()),
    ]).then(([detailRes, techRes, fundRes]) => {
      if (detailRes.status === "fulfilled") setDetail(detailRes.value);
      else setError(`Stock ${sym} not found`);
      if (techRes.status === "fulfilled" && !techRes.value.detail) setTechnical(techRes.value);
      if (fundRes.status === "fulfilled" && !fundRes.value.detail) setFundamentals(fundRes.value);
      setLoading(false);
    });
  }, [sym]);

  const fmt = (n: number | null, dec = 2) =>
    n == null ? "—" : n.toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const fmtCr = (n: number | null) =>
    n == null ? "—" : `₹${(n / 1e7).toFixed(0)} Cr`;

  if (loading) return <div style={{ padding: 48, color: "var(--text-muted)", fontSize: 14 }}>Loading {sym}...</div>;
  if (error) return <div style={{ padding: 48, color: "var(--accent-red)", fontSize: 14 }}>{error}</div>;
  if (!detail) return null;

  const { instrument, quote } = detail;
  const isUp = quote?.change_pct != null && quote.change_pct >= 0;

  return (
    <div style={{ padding: "40px 48px", maxWidth: 1100 }}>
      {/* Breadcrumb */}
      <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20 }}>
        <Link href="/stocks" style={{ color: "var(--accent-blue)", textDecoration: "none" }}>Stocks</Link>
        {" / "}
        <span>{sym}</span>
      </div>

      {/* Stock header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
              <h1 className="font-mono" style={{ fontSize: 30, fontWeight: 800, color: "var(--text-primary)" }}>{sym}</h1>
              <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 4, background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)", fontWeight: 600 }}>
                {instrument.exchange}
              </span>
            </div>
            <div style={{ fontSize: 15, color: "var(--text-secondary)", marginBottom: 4 }}>{instrument.name}</div>
            {instrument.sector && (
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{instrument.sector} · {instrument.industry ?? ""}</div>
            )}
          </div>

          {/* Price block */}
          {quote ? (
            <div style={{ textAlign: "right" }}>
              <div className="font-mono" style={{ fontSize: 34, fontWeight: 800, color: "var(--text-primary)" }}>
                ₹{fmt(quote.ltp)}
              </div>
              <div
                className="font-mono"
                style={{ fontSize: 15, fontWeight: 600, color: isUp ? "var(--accent-green)" : "var(--accent-red)" }}
              >
                {isUp ? "+" : ""}{fmt(quote.change)} ({isUp ? "+" : ""}{fmt(quote.change_pct)}%)
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                O: {fmt(quote.open)} · H: {fmt(quote.high)} · L: {fmt(quote.low)}
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No quote data — ingest market data first</div>
          )}
        </div>
      </div>

      {/* Two column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Technical indicators */}
        <SectionCard title="Technical Indicators">
          {!technical ? (
            <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No technical data. Run the feature engine after ingesting candles.</div>
          ) : (
            <>
              <MetricRow label="RSI (14)" value={fmt(technical.rsi_14)}
                highlight={technical.rsi_14 != null ? (technical.rsi_14 > 70 ? "negative" : technical.rsi_14 < 30 ? "positive" : "neutral") : "neutral"} />
              <MetricRow label="MACD" value={fmt(technical.macd)} />
              <MetricRow label="MACD Signal" value={fmt(technical.macd_signal)} />
              <MetricRow label="EMA 9" value={`₹${fmt(technical.ema_9)}`} />
              <MetricRow label="EMA 21" value={`₹${fmt(technical.ema_21)}`} />
              <MetricRow label="EMA 50" value={`₹${fmt(technical.ema_50)}`} />
              <MetricRow label="EMA 200" value={`₹${fmt(technical.ema_200)}`} />
              <MetricRow label="ATR (14)" value={fmt(technical.atr_14)} />
              <MetricRow label="ADX (14)" value={fmt(technical.adx_14)} />
              <MetricRow label="BB Upper" value={`₹${fmt(technical.bb_upper)}`} />
              <MetricRow label="BB Lower" value={`₹${fmt(technical.bb_lower)}`} />
              <MetricRow label="Volume Ratio" value={fmt(technical.volume_ratio)}
                highlight={technical.volume_ratio != null ? (technical.volume_ratio > 1.5 ? "positive" : "neutral") : "neutral"} />
            </>
          )}
        </SectionCard>

        {/* Fundamentals */}
        <SectionCard title="Fundamentals">
          {!fundamentals ? (
            <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No fundamental data. Ingest fundamentals to see valuation metrics.</div>
          ) : (
            <>
              <MetricRow label="Market Cap" value={fmtCr(fundamentals.market_cap)} />
              <MetricRow label="P/E Ratio" value={fmt(fundamentals.pe_ratio)} />
              <MetricRow label="P/B Ratio" value={fmt(fundamentals.pb_ratio)} />
              <MetricRow label="EV/EBITDA" value={fmt(fundamentals.ev_ebitda)} />
              <MetricRow label="Dividend Yield" value={fundamentals.dividend_yield != null ? `${fmt(fundamentals.dividend_yield)}%` : "—"} />
              <MetricRow label="Promoter Holding" value={fundamentals.promoter_holding_pct != null ? `${fmt(fundamentals.promoter_holding_pct)}%` : "—"}
                highlight={fundamentals.promoter_holding_pct != null && fundamentals.promoter_holding_pct > 50 ? "positive" : "neutral"} />
              <MetricRow label="FII Holding" value={fundamentals.fii_holding_pct != null ? `${fmt(fundamentals.fii_holding_pct)}%` : "—"} />
              <MetricRow label="DII Holding" value={fundamentals.dii_holding_pct != null ? `${fmt(fundamentals.dii_holding_pct)}%` : "—"} />
            </>
          )}
        </SectionCard>
      </div>

      {/* Disclaimer */}
      <div style={{ marginTop: 20, padding: "12px 18px", background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: 8, fontSize: 12, color: "var(--text-muted)" }}>
        All data shown is for informational purposes only. This is not financial advice. Always do your own research.
      </div>
    </div>
  );
}
