"use client";

import { useState, useEffect } from "react";

interface Alert {
  id: number;
  symbol: string;
  exchange: string;
  condition: string;
  threshold_value: number;
  is_active: boolean;
}

interface Notification {
  id: number;
  title: string;
  body: string;
  related_symbol: string | null;
  is_read: boolean;
  created_at: string;
}

const CONDITION_OPTIONS = [
  { value: "PRICE_ABOVE", label: "Price Above" },
  { value: "PRICE_BELOW", label: "Price Below" },
  { value: "RSI_ABOVE", label: "RSI Above" },
  { value: "RSI_BELOW", label: "RSI Below" },
  { value: "OPPORTUNITY_HIGH", label: "Opportunity = HIGH" },
  { value: "OPPORTUNITY_MODERATE", label: "Opportunity = MODERATE" },
];

const conditionLabel = (c: string) => CONDITION_OPTIONS.find(o => o.value === c)?.label ?? c;

function AlertBadge({ condition }: { condition: string }) {
  const isPrice = condition.includes("PRICE");
  const isRsi = condition.includes("RSI");
  const color = isPrice ? "var(--accent-blue-bright)" : isRsi ? "var(--accent-purple)" : "var(--accent-green)";
  return (
    <span style={{ padding: "3px 8px", borderRadius: 6, fontSize: 11, fontWeight: 700, color, background: `color-mix(in srgb, ${color} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${color} 25%, transparent)` }}>
      {conditionLabel(condition)}
    </span>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [newSymbol, setNewSymbol] = useState("");
  const [newCondition, setNewCondition] = useState("PRICE_ABOVE");
  const [newThreshold, setNewThreshold] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers = token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };

  const loadData = async () => {
    setLoading(true);
    try {
      const [ar, nr] = await Promise.allSettled([
        fetch("/api/alerts", { headers }).then(r => r.json()),
        fetch("/api/notifications", { headers }).then(r => r.json()),
      ]);
      if (ar.status === "fulfilled" && Array.isArray(ar.value)) setAlerts(ar.value);
      if (nr.status === "fulfilled" && Array.isArray(nr.value)) setNotifications(nr.value);
    } catch (e: any) {
      setError("Failed to load alerts. Please log in.");
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const createAlert = async () => {
    if (!newSymbol || !newThreshold) return;
    setCreating(true);
    setCreateError(null);
    try {
      const res = await fetch("/api/alerts", {
        method: "POST",
        headers,
        body: JSON.stringify({ symbol: newSymbol.toUpperCase(), condition: newCondition, threshold_value: parseFloat(newThreshold) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed to create alert");
      setAlerts(prev => [data, ...prev]);
      setNewSymbol("");
      setNewThreshold("");
    } catch (e: any) {
      setCreateError(e.message);
    }
    setCreating(false);
  };

  const deleteAlert = async (id: number) => {
    await fetch(`/api/alerts/${id}`, { method: "DELETE", headers });
    setAlerts(prev => prev.filter(a => a.id !== id));
  };

  const markRead = async (id: number) => {
    await fetch(`/api/notifications/${id}/read`, { method: "PATCH", headers });
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const inputStyle: React.CSSProperties = {
    padding: "9px 14px", background: "var(--bg-secondary)", border: "1px solid var(--border-light)",
    borderRadius: 8, color: "var(--text-primary)", fontSize: 13, outline: "none", width: "100%",
  };

  return (
    <div style={{ padding: "40px 48px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.03em", color: "var(--text-primary)", marginBottom: 6 }}>
          Alerts & Notifications
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
          Set price and signal alerts. Get notified when your conditions are triggered.
        </p>
      </div>

      {!token && (
        <div style={{ padding: "16px 20px", background: "rgba(245,158,11,0.07)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: 10, marginBottom: 28, fontSize: 13, color: "var(--accent-yellow)" }}>
          ⚠ You need to log in to manage alerts. Alerts require authentication.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
        {/* Left: Active Alerts */}
        <div>
          {/* Create alert form */}
          <div className="card" style={{ padding: 24, marginBottom: 24 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 20 }}>
              + Create New Alert
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Symbol</label>
                <input id="alert-symbol" value={newSymbol} onChange={e => setNewSymbol(e.target.value.toUpperCase())} placeholder="e.g. RELIANCE" style={inputStyle} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Condition</label>
                <select id="alert-condition" value={newCondition} onChange={e => setNewCondition(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
                  {CONDITION_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Threshold Value</label>
                <input id="alert-threshold" type="number" value={newThreshold} onChange={e => setNewThreshold(e.target.value)} placeholder="e.g. 3000" style={inputStyle} />
              </div>
              {createError && (
                <div style={{ fontSize: 12, color: "var(--accent-red)" }}>⚠ {createError}</div>
              )}
              <button
                id="create-alert-btn"
                onClick={createAlert}
                disabled={creating || !newSymbol || !newThreshold}
                style={{ padding: "10px", background: "var(--accent-blue)", color: "#fff", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", border: "none", marginTop: 4, opacity: (!newSymbol || !newThreshold) ? 0.5 : 1 }}
              >
                {creating ? "Creating…" : "Create Alert"}
              </button>
            </div>
          </div>

          {/* Alert list */}
          <div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 14 }}>
              Active Alerts ({alerts.filter(a => a.is_active).length})
            </div>
            {loading ? (
              [1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 60, marginBottom: 10, borderRadius: 10 }} />)
            ) : alerts.length === 0 ? (
              <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)", fontSize: 13 }}>
                No alerts yet. Create your first alert above.
              </div>
            ) : alerts.map(a => (
              <div key={a.id} className="card" style={{ padding: "14px 18px", marginBottom: 10, display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)", fontFamily: "'JetBrains Mono', monospace" }}>{a.symbol}</span>
                    <AlertBadge condition={a.condition} />
                    {!a.is_active && <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Inactive</span>}
                  </div>
                  <div className="font-mono" style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Threshold: ₹{a.threshold_value.toLocaleString("en-IN")}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: a.is_active ? "var(--accent-green)" : "var(--border-light)", boxShadow: a.is_active ? "0 0 6px var(--accent-green)" : "none" }} />
                  <button onClick={() => deleteAlert(a.id)} style={{ padding: "4px 10px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 6, color: "var(--accent-red)", fontSize: 12, cursor: "pointer", fontWeight: 600 }}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Notifications */}
        <div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 14, display: "flex", alignItems: "center", gap: 10 }}>
            Notification Inbox
            {unreadCount > 0 && (
              <span style={{ padding: "2px 8px", background: "var(--accent-blue)", color: "#fff", borderRadius: 99, fontSize: 11, fontWeight: 700 }}>{unreadCount} unread</span>
            )}
          </div>

          {loading ? (
            [1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 80, marginBottom: 10, borderRadius: 10 }} />)
          ) : notifications.length === 0 ? (
            <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)", fontSize: 13 }}>
              <div style={{ fontSize: 40, marginBottom: 10 }}>🔔</div>
              No notifications yet. Alerts will appear here when triggered.
            </div>
          ) : notifications.map(n => (
            <div key={n.id} className="card" style={{ padding: "14px 18px", marginBottom: 10, borderColor: n.is_read ? "var(--border)" : "rgba(99,102,241,0.3)", background: n.is_read ? "var(--bg-card)" : "rgba(99,102,241,0.04)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {!n.is_read && <div style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent-blue)", flexShrink: 0 }} />}
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{n.title}</span>
                </div>
                {n.related_symbol && (
                  <span className="font-mono" style={{ fontSize: 11, color: "var(--accent-blue-bright)", fontWeight: 600 }}>{n.related_symbol}</span>
                )}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: 8 }}>{n.body}</div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{new Date(n.created_at).toLocaleString("en-IN")}</span>
                {!n.is_read && (
                  <button onClick={() => markRead(n.id)} style={{ fontSize: 11, color: "var(--accent-blue-bright)", background: "none", border: "none", cursor: "pointer", fontWeight: 600 }}>
                    Mark read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SEBI disclaimer */}
      <div style={{ marginTop: 40, padding: "12px 16px", background: "rgba(99,102,241,0.04)", border: "1px solid rgba(99,102,241,0.12)", borderRadius: 8, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
        <strong style={{ color: "var(--accent-blue-bright)" }}>Disclaimer:</strong> Price alerts are informational only. Triggering of an alert does not constitute a buy/sell recommendation. This platform is a decision-support tool, not a SEBI-registered research analyst service.
      </div>
    </div>
  );
}
