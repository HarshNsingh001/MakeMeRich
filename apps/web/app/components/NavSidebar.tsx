"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Market Pulse", icon: "📊" },
  { href: "/stocks", label: "Stocks", icon: "📈" },
];

export default function NavSidebar() {
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: "220px",
        minHeight: "100vh",
        background: "var(--bg-secondary)",
        borderRight: "1px solid var(--border)",
        position: "fixed",
        top: 0,
        left: 0,
        zIndex: 40,
        display: "flex",
        flexDirection: "column",
        padding: "24px 0",
      }}
    >
      {/* Logo */}
      <div style={{ padding: "0 20px 28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "linear-gradient(135deg, #3b82f6, #6366f1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              fontWeight: 800,
              color: "#fff",
              flexShrink: 0,
            }}
          >
            M
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>
              MakeMeRich
            </div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              EQUITY INTEL · V1
            </div>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav style={{ flex: 1, padding: "0 12px" }}>
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
                gap: 10,
                padding: "10px 12px",
                borderRadius: 8,
                marginBottom: 4,
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                textDecoration: "none",
                fontSize: 14,
                fontWeight: isActive ? 600 : 500,
                background: isActive ? "var(--bg-card)" : "transparent",
                transition: "all 0.15s",
                borderLeft: isActive ? "2px solid var(--accent-blue)" : "2px solid transparent",
              }}
            >
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer note */}
      <div
        style={{
          padding: "16px 20px",
          borderTop: "1px solid var(--border)",
        }}
      >
        <div style={{ fontSize: 10, color: "var(--text-muted)", lineHeight: 1.6 }}>
          Decision-support tool.
          <br />
          Not financial advice.
        </div>
      </div>
    </aside>
  );
}
