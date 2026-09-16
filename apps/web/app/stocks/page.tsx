"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Stock {
  symbol: string;
  company_name: string | null;
  sector: string | null;
  industry: string | null;
}

interface StocksResponse {
  total: number;
  page: number;
  page_size: number;
  items: Stock[];
}

export default function StocksPage() {
  const [data, setData] = useState<StocksResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    const delay = setTimeout(() => {
      fetch(`/api/stocks?page=${page}&page_size=20${search ? `&search=${search}` : ""}`)
        .then((r) => r.json())
        .then((d) => {
          setData(d);
          setLoading(false);
          setError(null);
        })
        .catch((e) => {
          setError("Failed to fetch stocks");
          setLoading(false);
        });
    }, 300);

    return () => clearTimeout(delay);
  }, [page, search]);

  return (
    <div style={{ padding: "48px 64px", maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ marginBottom: 40, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: 36, fontWeight: 800, color: "var(--text-primary)", marginBottom: 8, letterSpacing: "-0.03em" }}>
            Stock Screener
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 16 }}>
            Browse {data ? data.total.toLocaleString("en-IN") : "all"} supported instruments
          </p>
        </div>

        <div>
          <input
            type="text"
            placeholder="Search symbol (e.g. RELIANCE)..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              padding: "12px 20px",
              borderRadius: 10,
              color: "var(--text-primary)",
              width: 320,
              fontSize: 14,
              outline: "none",
              transition: "border-color 0.2s, box-shadow 0.2s"
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--accent-blue)";
              e.currentTarget.style.boxShadow = "0 0 0 3px var(--accent-blue-glow)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.boxShadow = "none";
            }}
          />
        </div>
      </div>

      {error && (
        <div style={{ background: "var(--accent-red-glow)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 12, padding: "16px 24px", color: "var(--accent-red)", marginBottom: 32 }}>
          ⚠ {error}
        </div>
      )}

      <div className="card" style={{ overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-secondary)" }}>
              <th style={{ padding: "16px 24px", fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Symbol</th>
              <th style={{ padding: "16px 24px", fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Company</th>
              <th style={{ padding: "16px 24px", fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Sector / Industry</th>
              <th style={{ padding: "16px 24px", fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", textAlign: "right" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data && Array(10).fill(0).map((_, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "16px 24px" }}><div className="skeleton" style={{ height: 20, width: 80 }} /></td>
                <td style={{ padding: "16px 24px" }}><div className="skeleton" style={{ height: 20, width: 160 }} /></td>
                <td style={{ padding: "16px 24px" }}><div className="skeleton" style={{ height: 20, width: 120 }} /></td>
                <td style={{ padding: "16px 24px", textAlign: "right" }}><div className="skeleton" style={{ height: 32, width: 90, marginLeft: "auto" }} /></td>
              </tr>
            ))}

            {data?.items.map((stock, i) => (
              <tr 
                key={stock.symbol} 
                className={`animate-fade-in-up-delay-${(i % 3) + 1}`}
                style={{ borderBottom: "1px solid var(--border)", transition: "background 0.2s" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-card-hover)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <td style={{ padding: "16px 24px", width: "20%" }}>
                  <span className="font-mono" style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: 15 }}>
                    {stock.symbol}
                  </span>
                </td>
                <td style={{ padding: "16px 24px", width: "35%", color: "var(--text-secondary)", fontSize: 14 }}>
                  {stock.company_name || "—"}
                </td>
                <td style={{ padding: "16px 24px", width: "30%" }}>
                  {stock.sector ? (
                    <div>
                      <div style={{ fontSize: 14, color: "var(--text-primary)", marginBottom: 2 }}>{stock.sector}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{stock.industry}</div>
                    </div>
                  ) : (
                    <span style={{ color: "var(--text-muted)", fontSize: 14 }}>—</span>
                  )}
                </td>
                <td style={{ padding: "16px 24px", width: "15%", textAlign: "right" }}>
                  <Link 
                    href={`/stocks/${stock.symbol}`}
                    style={{
                      display: "inline-block",
                      padding: "8px 16px",
                      background: "rgba(99,102,241,0.1)",
                      color: "var(--accent-blue-bright)",
                      borderRadius: 6,
                      fontSize: 13,
                      fontWeight: 600,
                      transition: "background 0.2s"
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(99,102,241,0.2)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(99,102,241,0.1)")}
                  >
                    Analyze
                  </Link>
                </td>
              </tr>
            ))}

            {data?.items.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: "48px", textAlign: "center", color: "var(--text-muted)" }}>
                  No stocks found matching "{search}"
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {data && data.total > data.page_size && (
          <div style={{ padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border)" }}>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Showing {(data.page - 1) * data.page_size + 1} to {Math.min(data.page * data.page_size, data.total)} of {data.total}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                style={{
                  padding: "8px 16px",
                  background: page === 1 ? "transparent" : "var(--bg-secondary)",
                  border: `1px solid ${page === 1 ? "var(--border)" : "var(--border-light)"}`,
                  color: page === 1 ? "var(--text-muted)" : "var(--text-primary)",
                  borderRadius: 6,
                  cursor: page === 1 ? "not-allowed" : "pointer",
                  fontSize: 13,
                  fontWeight: 500
                }}
              >
                Previous
              </button>
              <button
                disabled={page * data.page_size >= data.total}
                onClick={() => setPage(p => p + 1)}
                style={{
                  padding: "8px 16px",
                  background: page * data.page_size >= data.total ? "transparent" : "var(--bg-secondary)",
                  border: `1px solid ${page * data.page_size >= data.total ? "var(--border)" : "var(--border-light)"}`,
                  color: page * data.page_size >= data.total ? "var(--text-muted)" : "var(--text-primary)",
                  borderRadius: 6,
                  cursor: page * data.page_size >= data.total ? "not-allowed" : "pointer",
                  fontSize: 13,
                  fontWeight: 500
                }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
