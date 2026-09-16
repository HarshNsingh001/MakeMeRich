import type { Metadata } from "next";
import "./globals.css";
import NavSidebar from "./components/NavSidebar";

export const metadata: Metadata = {
  title: "MakeMeRich — Indian Equity Intelligence Platform",
  description:
    "AI-assisted Indian equity research platform. Evidence-based market intelligence for NSE stocks — not a profit guarantee.",
  keywords: ["NSE", "Indian stocks", "equity research", "market intelligence", "NIFTY"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased">
        <div className="flex min-h-screen">
          <NavSidebar />
          <main style={{ marginLeft: "220px", flex: 1, minHeight: "100vh" }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
