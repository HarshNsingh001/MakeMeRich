"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Stock {
  symbol: string;
  exchange: string;
  name: string;
  sector: string | null;
  industry: string | null;
  instrument_type: string;
  isin: string | null;
  is_active: boolean;
}

interface PaginatedStocks {
  total: number;
  page: number;
  page_size: number;
  items: Stock[];
}

export default function StocksPage() {
  const [data, setData] = useState<PaginatedStocks | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sector, setSector] = useState("");
  const [page, setPage] = useState(1);

  const fetchStocks = (q: string, sec: string, pg: number) => {
    setLoading(true);
    const params = new URLSearchParams({
      search: q,
      sector: sec,
      page: String(pg),
      page_size: "50",
    });
    fetch(`/api/stocks?${params}`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => { setError("API offline — start FastAPI on port 8000"); setLoading(false); });
  };

  useEffect(() => { fetchStocks(search, sector, page); }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchStocks(search, sector, 1);
  };

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <div style={{ padding: "40px 48px", maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", marginBottom: 6 }}>
          Stocks
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
          NSE equity universe — search and filter
        </p>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search symbol or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: "1 1 240px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "10px 16px",
            color: "var(--text-primary)",
            fontSize: 14,
            outline: "none",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
        />
        <input
          type="text"
          placeholder="Sector filter..."
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          style={{
            flex: "1 1 180px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "10px 16px",
            color: "var(--text-primary)",
            fontSize: 14,
            outline: "none",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
        />
        <button
          type="submit"
          style={{
            background: "var(--accent-blue)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 24px",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            transition: "opacity 0.15s",
          }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.opacity = "0.85")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.opacity = "1")}
        >
          Search
        </button>
      </form>

      {/* Error */}
      {error && (
        <div style={{ color: "var(--accent-red)", fontSize: 14, padding: "14px 20px", background: "var(--accent-red-glow)", borderRadius: 8, marginBottom: 20 }}>
          ⚠ {error}
        </div>
      )}

      {/* Total count */}
      {data && (
        <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 14 }}>
          {data.total.toLocaleString()} stocks found
        </div>
      )}

      {/* Table */}
      <div
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["Symbol", "Name", "Sector", "Exchange", "Type"].map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "14px 20px",
                    textAlign: "left",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    letterSpacing: "0.07em",
                    textTransform: "uppercase",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
                  Loading...
                </td>
              </tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
                  No stocks found. Ingest the instrument master first.
                </td>
              </tr>
            )}
            {data?.items.map((stock, i) => (
              <tr
                key={stock.symbol}
                style={{
                  borderBottom: i < data.items.length - 1 ? "1px solid var(--border)" : "none",
                  transition: "background 0.15s",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--bg-card-hover)")}
                onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
              >
                <td style={{ padding: "14px 20px" }}>
                  <Link
                    href={`/stocks/${stock.symbol}`}
                    style={{ textDecoration: "none" }}
                  >
                    <span
                      className="font-mono"
                      style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-blue)" }}
                    >
                      {stock.symbol}
                    </span>
                  </Link>
                </td>
                <td style={{ padding: "14px 20px", fontSize: 14, color: "var(--text-primary)", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {stock.name}
                </td>
                <td style={{ padding: "14px 20px", fontSize: 13, color: "var(--text-secondary)" }}>
                  {stock.sector ?? "—"}
                </td>
                <td style={{ padding: "14px 20px", fontSize: 13, color: "var(--text-secondary)" }}>
                  {stock.exchange}
                </td>
                <td style={{ padding: "14px 20px" }}>
                  <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 4, background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)", fontWeight: 600 }}>
                    {stock.instrument_type}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div style={{ display: "flex", gap: 8, marginTop: 20, alignItems: "center" }}>
          <button
            onClick={() => { const p = Math.max(1, page - 1); setPage(p); fetchStocks(search, sector, p); }}
            disabled={page === 1}
            style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-secondary)", cursor: page === 1 ? "not-allowed" : "pointer", fontSize: 13 }}
          >
            ← Prev
          </button>
          <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Page {page} of {totalPages}</span>
          <button
            onClick={() => { const p = Math.min(totalPages, page + 1); setPage(p); fetchStocks(search, sector, p); }}
            disabled={page === totalPages}
            style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-secondary)", cursor: page === totalPages ? "not-allowed" : "pointer", fontSize: 13 }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
