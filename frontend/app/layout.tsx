import type { Metadata } from "next";
import Link from "next/link";
import { Activity, ArrowUpRight, ChartNoAxesCombined, FlaskConical, ScanLine } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = { title: "Basecamp · Momentum Research", description: "Transparent US momentum breakout research" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-icon"><ChartNoAxesCombined size={22} /></span>basecamp<span className="brand-dot">.</span></Link>
      <div className="workspace-label">RESEARCH WORKSPACE</div>
      <nav aria-label="Main navigation">
        <Link href="/"><ScanLine size={18} /> Market dashboard</Link>
        <Link href="/backtests"><FlaskConical size={18} /> Backtesting <span className="soon">P3</span></Link>
      </nav>
      <div className="sidebar-note"><Activity size={18}/><strong>Process over prediction.</strong><p>Find the setup. Define the risk.<br/>Let the market confirm.</p></div>
      <a className="api-link" href="https://massive.com/docs/rest/stocks/overview" target="_blank" rel="noreferrer">Market data documentation <ArrowUpRight size={14}/></a>
      <div className="sidebar-footer">MOMENTUM RESEARCH / V0.1</div>
    </aside>
    <div className="main-shell"><header className="topbar"><span>US EQUITIES <span className="slash">/</span> RESEARCH TERMINAL</span><span className="research-badge"><span className="tiny-dot"/> End-of-day research</span></header>
      <main>{children}</main>
      <footer className="disclaimer">Research tools only. Conditional setups and hypothetical targets are not predictions or trade executions. No returns are guaranteed.</footer>
    </div>
  </body></html>;
}
