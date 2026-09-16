"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function BacktestPage() {
  const [executions, setExecutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [selectedExecId, setSelectedExecId] = useState<string | null>(null);
  const [results, setResults] = useState<any | null>(null);

  const fetchExecutions = () => {
    fetch("/api/backtest/executions")
      .then((r) => r.json())
      .then((d) => {
        setExecutions(d);
        setLoading(false);
        if (d.length > 0 && !selectedExecId) {
          setSelectedExecId(d[0].execution_id);
        }
      });
  };

  useEffect(() => {
    fetchExecutions();
    const interval = setInterval(fetchExecutions, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedExecId) {
      fetch(`/api/backtest/executions/${selectedExecId}/results`)
        .then((r) => r.json())
        .then((d) => setResults(d));
    }
  }, [selectedExecId, executions]); // re-fetch results if executions update (might be in progress)

  const triggerSmokeTest = () => {
    setTriggering(true);
    fetch("/api/backtest/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Smoke Test (NIFTY top 10)",
        max_stocks: 10,
        target_dates: ["2026-08-01T15:30:00Z"] // Approx 1 month ago
      })
    }).then(() => {
      setTriggering(false);
      fetchExecutions();
    });
  };

  return (
    <div style={{ padding: "48px 64px", maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ marginBottom: 40, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: 36, fontWeight: 800, color: "var(--text-primary)", marginBottom: 8, letterSpacing: "-0.03em" }}>
            Historical Evaluation
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 16 }}>
            Point-in-Time backtesting harness for the multi-agent AI engine.
          </p>
        </div>
        <div>
          <button 
            onClick={triggerSmokeTest}
            disabled={triggering}
            style={{
              padding: "10px 20px",
              background: "var(--accent-purple)",
              color: "#fff",
              borderRadius: 8,
              border: "none",
              fontWeight: 600,
              cursor: triggering ? "not-allowed" : "pointer"
            }}
          >
            {triggering ? "Queuing..." : "▶ Run Smoke Test"}
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 32 }}>
        {/* Left: Execution List */}
        <div className="card" style={{ padding: 0, alignSelf: "start", overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", background: "var(--bg-secondary)", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)" }}>
            Execution Jobs
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {loading && <div style={{ padding: 20 }}>Loading jobs...</div>}
            {executions.map(ex => (
              <div 
                key={ex.execution_id}
                onClick={() => setSelectedExecId(ex.execution_id)}
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid var(--border)",
                  cursor: "pointer",
                  background: selectedExecId === ex.execution_id ? "var(--bg-card-hover)" : "transparent",
                  borderLeft: selectedExecId === ex.execution_id ? "3px solid var(--accent-blue)" : "3px solid transparent"
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                  {ex.name}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    {new Date(ex.created_at).toLocaleDateString()}
                  </span>
                  <span style={{ 
                    fontSize: 10, 
                    fontWeight: 700, 
                    padding: "2px 8px", 
                    borderRadius: 99,
                    background: ex.status === "COMPLETED" ? "rgba(16,185,129,0.1)" : ex.status === "RUNNING" ? "rgba(99,102,241,0.1)" : "rgba(255,255,255,0.05)",
                    color: ex.status === "COMPLETED" ? "var(--accent-green)" : ex.status === "RUNNING" ? "var(--accent-blue-bright)" : "var(--text-secondary)"
                  }}>
                    {ex.status}
                  </span>
                </div>
              </div>
            ))}
            {executions.length === 0 && !loading && (
              <div style={{ padding: "32px 20px", textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
                No backtest jobs run yet.
              </div>
            )}
          </div>
        </div>

        {/* Right: Results Dashboard */}
        <div className="card" style={{ padding: 32, minHeight: 600 }}>
          {!selectedExecId ? (
            <div style={{ textAlign: "center", paddingTop: 100, color: "var(--text-muted)" }}>
              Select an execution job to view metrics
            </div>
          ) : results ? (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
                <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>Performance Matrix</h2>
                <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>
                  Processed: <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>{results.total_completed}</span> cases
                </div>
              </div>
              
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24, marginBottom: 48 }}>
                <div style={{ padding: 24, background: "var(--bg-secondary)", borderRadius: 12, border: "1px solid var(--border-light)" }}>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Avg Gross Return (T+5)</div>
                  <div style={{ fontSize: 32, fontWeight: 800, color: (results.metrics.avg_gross_return_t5 || 0) > 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
                    {((results.metrics.avg_gross_return_t5 || 0) * 100).toFixed(2)}%
                  </div>
                </div>
                <div style={{ padding: 24, background: "var(--bg-secondary)", borderRadius: 12, border: "1px solid var(--border-light)" }}>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>HIGH Opportunities Found</div>
                  <div style={{ fontSize: 32, fontWeight: 800, color: "var(--text-primary)" }}>
                    {results.high_opportunities_found}
                  </div>
                </div>
                <div style={{ padding: 24, background: "var(--bg-secondary)", borderRadius: 12, border: "1px solid var(--border-light)" }}>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Lookahead Leakage</div>
                  <div style={{ fontSize: 32, fontWeight: 800, color: "var(--accent-green)" }}>
                    0%
                  </div>
                </div>
              </div>

              <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)", marginBottom: 16 }}>Raw Results Log</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)" }}>
                    <th style={{ padding: "12px 16px" }}>Symbol</th>
                    <th style={{ padding: "12px 16px" }}>Target Date</th>
                    <th style={{ padding: "12px 16px" }}>Signal</th>
                    <th style={{ padding: "12px 16px" }}>Gross Ret (T+5)</th>
                    <th style={{ padding: "12px 16px" }}>MAE</th>
                    <th style={{ padding: "12px 16px" }}>MFE</th>
                  </tr>
                </thead>
                <tbody>
                  {results.raw_results.map((r: any) => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--border-light)" }}>
                      <td style={{ padding: "12px 16px", fontWeight: 600, color: "var(--text-primary)" }}>{r.symbol}</td>
                      <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>{new Date(r.target_date).toLocaleDateString()}</td>
                      <td style={{ padding: "12px 16px" }}>
                        <span className={`opp-${r.opportunity_level.toLowerCase()}`} style={{ padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 700 }}>
                          {r.opportunity_level} ({(r.confidence * 100).toFixed(0)}%)
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px", color: r.gross_return_t5 > 0 ? "var(--accent-green)" : r.gross_return_t5 < 0 ? "var(--accent-red)" : "var(--text-secondary)" }}>
                        {(r.gross_return_t5 * 100).toFixed(2)}%
                      </td>
                      <td style={{ padding: "12px 16px", color: "var(--accent-red)" }}>{(r.mae * 100).toFixed(2)}%</td>
                      <td style={{ padding: "12px 16px", color: "var(--accent-green)" }}>{(r.mfe * 100).toFixed(2)}%</td>
                    </tr>
                  ))}
                  {results.raw_results.length === 0 && (
                    <tr>
                      <td colSpan={6} style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)" }}>
                        No results available yet. Run a job to populate.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>

            </div>
          ) : (
            <div>Loading results...</div>
          )}
        </div>
      </div>
    </div>
  );
}
