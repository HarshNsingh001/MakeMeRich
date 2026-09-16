"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Market Pulse", icon: "📊" },
  { href: "/opportunities", label: "Opportunities", icon: "🎯" },
  { href: "/stocks", label: "Stock Screener", icon: "📈" },
  { href: "/sectors", label: "Sector Rotation", icon: "🔄" },
  { href: "/alerts", label: "Alerts", icon: "🔔" },
  { href: "/backtest", label: "Backtest Lab", icon: "🧪" },
];

export default function NavSidebar() {
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: "240px",
        minHeight: "100vh",
        background: "var(--bg-secondary)",
        borderRight: "1px solid var(--border)",
        position: "fixed",
        top: 0,
        left: 0,
        zIndex: 40,
        display: "flex",
        flexDirection: "column",
        padding: "32px 0 24px",
      }}
    >
      {/* Logo */}
      <div style={{ padding: "0 24px 40px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              background: "linear-gradient(135deg, var(--accent-blue-bright), var(--accent-purple))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
              fontWeight: 800,
              color: "#fff",
              flexShrink: 0,
              boxShadow: "0 4px 14px rgba(99,102,241,0.3)"
            }}
          >
            M
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 17, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
              MakeMeRich
            </div>
            <div style={{ fontSize: 10, color: "var(--text-secondary)", letterSpacing: "0.08em", marginTop: 2, fontWeight: 600 }}>
              AI EQUITY INTEL
            </div>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav style={{ flex: 1, padding: "0 16px" }}>
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
                borderRadius: 10,
                marginBottom: 6,
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                textDecoration: "none",
                fontSize: 14,
                fontWeight: isActive ? 600 : 500,
                background: isActive ? "var(--bg-card-hover)" : "transparent",
                transition: "all 0.2s",
                border: "1px solid",
                borderColor: isActive ? "var(--border-light)" : "transparent",
                boxShadow: isActive ? "0 2px 8px rgba(0,0,0,0.2)" : "none",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "var(--bg-card)";
                  (e.currentTarget as HTMLElement).style.color = "var(--text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)";
                }
              }}
            >
              <span style={{ fontSize: 18, filter: isActive ? "none" : "grayscale(100%) opacity(0.7)" }}>
                {item.icon}
              </span>
              {item.label}
              {isActive && (
                <div style={{ marginLeft: "auto", width: 4, height: 16, background: "var(--accent-blue-bright)", borderRadius: 4 }} />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Connection Status & Footer note */}
      <div style={{ padding: "0 24px" }}>
        <div style={{ 
          background: "var(--bg-card)", 
          border: "1px solid var(--border)", 
          borderRadius: 8, 
          padding: "12px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 16
        }}>
          <span className="live-dot" />
          <span style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 500 }}>
            System Online
          </span>
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5 }}>
          AI Decision Support.
          <br />
          Not financial advice.
        </div>
      </div>
    </aside>
  );
}
