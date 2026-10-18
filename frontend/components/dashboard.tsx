"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowDown, ArrowRight, ArrowUpRight, Check, ChevronDown, CircleHelp, RefreshCw, Search, SlidersHorizontal, TrendingUp } from "lucide-react";
import { num, pct } from "@/lib/format";
import type { Candidate, DashboardData } from "@/lib/types";

type SortKey = "symbol" | "rs" | "return63" | "adr" | "rvol" | "pivot" | "rr" | "score";
function metric(c: Candidate, key: SortKey): string | number | null | undefined {
  switch (key) {
    case "symbol": return c.symbol;
    case "rs": return c.indicators.rs_percentile;
    case "return63": return c.indicators.return_63;
    case "adr": return c.indicators.adr20_pct;
    case "rvol": return c.indicators.rvol;
    case "pivot": return c.pivot;
    case "rr": return c.plan.reward_risk;
    default: return c.score;
  }
}

export default function Dashboard({ data }: { data: DashboardData }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [minRs, setMinRs] = useState(0);
  const [sort, setSort] = useState<SortKey>("score");
  const [desc, setDesc] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [equity, setEquity] = useState(100000);
  const [riskPct, setRiskPct] = useState(0.5);
  const [minMomentum, setMinMomentum] = useState(30);
  const [minRank, setMinRank] = useState(70);
  const [minRvol, setMinRvol] = useState(1.5);
  const rows = useMemo(() => data.candidates.filter(c =>
    `${c.symbol} ${c.name}`.toLowerCase().includes(query.toLowerCase()) &&
    (status === "ALL" || c.status === status) && (minRs === 0 || (c.indicators.rs_percentile ?? -1) >= minRs)
  ).sort((a, b) => {
    const av = metric(a, sort), bv = metric(b, sort);
    if (av == null) return bv == null ? 0 : 1;
    if (bv == null) return -1;
    const value = typeof av === "string" ? av.localeCompare(String(bv)) : Number(av) - Number(bv);
    return desc ? -value : value;
  }), [data.candidates, query, status, minRs, sort, desc]);
  const active = data.candidates.filter(c => ["READY", "TRIGGERED"].includes(c.status));
  const triggered = data.candidates.filter(c => c.status === "TRIGGERED").length;
  async function refresh() {
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/scan", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ risk: { account_equity: equity, risk_fraction: riskPct / 100 },
          breakout: { min_return63: minMomentum / 100, min_rs_percentile: minRank, min_breakout_rvol: minRvol } }) });
      if (!res.ok) { const body = await res.json(); throw new Error(typeof body.detail === "string" ? body.detail : "Scan failed. Check parameters and backend logs."); }
      router.refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Scan failed"); }
    finally { setBusy(false); }
  }
  function changeSort(key: SortKey) { if (sort === key) setDesc(!desc); else { setSort(key); setDesc(key !== "symbol"); } }
  function th(label: string, key: SortKey) { return <th><button onClick={() => changeSort(key)} aria-label={`Sort by ${label}`}>{label}{sort === key ? <ArrowDown size={12} style={{ transform: desc ? undefined : "rotate(180deg)" }}/> : <ChevronDown size={11}/>}</button></th>; }
  return <>
    <div className="page-heading"><div><div className="eyebrow">YOUR EDGE STARTS WITH A SETUP</div><h1>Market dashboard<span className="heading-dot">.</span></h1><p>Strong momentum. Orderly bases. Clearly defined risk.</p></div>
      <button className="button" onClick={refresh} disabled={busy}><RefreshCw size={15} className={busy ? "spin" : ""}/>{busy ? "Scanning…" : "Run daily scan"}</button></div>
    <div className={`data-banner ${data.stale ? "warning" : ""}`}><span><span className="tiny-dot"/>{data.data_mode === "synthetic" ? "SYNTHETIC DEMO DATA" : data.data_mode === "empty" ? "NO MARKET DATA" : "MASSIVE · ADJUSTED DAILY DATA"}</span><span>{data.session ? `Session ${data.session}` : "Ingest history to get started"}{data.stale ? " · Refresh required" : " · Latest completed session"}</span></div>
    {error && <div className="error-box" role="alert">{error}</div>}
    <section className="overview-grid" aria-label="Market overview">
      <article className="regime-card"><div className="card-kicker">MARKET ENVIRONMENT <CircleHelp size={14}/></div><div className="regime-title"><span className={`regime-light ${data.regime.regime?.toLowerCase() || "unknown"}`}/><strong>{data.regime.regime || "UNAVAILABLE"}</strong><span className="tag">RULE BASED</span></div><p>{data.regime.regime === "GREEN" ? "Broad market conditions support new setups." : data.regime.regime === "YELLOW" ? "Mixed conditions. Position budgets reduced by half." : data.regime.regime === "RED" ? "Defensive conditions. New positions are ineligible." : data.regime.reason}</p><div className="benchmark-row">{["SPY", "QQQ", "IWM"].map(s => { const b = data.regime.evidence?.[s]; return <div key={s}><span>{s}</span><strong>{b ? num(b.close) : "—"}</strong><small className={b?.above_sma50 && b?.above_sma20 ? "positive" : "muted"}>{b?.sufficient_history ? (b.above_sma20 && b.above_sma50 ? "Above 20 / 50 MA" : "Below one or both MAs") : "History required"}</small></div>; })}</div></article>
      <article className="summary-card"><span className="card-kicker">ACTIONABLE SETUPS <TrendingUp size={16}/></span><strong className="big-number">{active.length.toString().padStart(2, "0")}<span>/ {data.universe_size}</span></strong><p><span className="positive">{triggered} triggered</span> · {active.length - triggered} ready</p><div className="mini-bars">{["BUILDING", "READY", "TRIGGERED", "EXTENDED", "FAILED"].map(s => <span title={s} key={s} style={{ height: `${Math.max(12, data.candidates.filter(c => c.status === s).length / Math.max(1, data.universe_size) * 65)}px` }}/>)}</div><small>Setup state; risk eligibility is assessed separately.</small></article>
      <article className="summary-card ep-card"><span className="card-kicker">EPISODIC PIVOTS <ArrowUpRight size={16}/></span><strong className="big-number">—<span className="tag">PHASE 2</span></strong><p>Confirmation comes first.</p><small>Intraday opening range, unusual volume, and a verified catalyst are required. EP scanning is not active yet.</small></article>
    </section>
    <section className="screener-panel"><div className="section-heading"><div><span className="eyebrow">THE WATCHLIST</span><h2>Momentum breakouts <span className="count">{data.candidates.length}</span></h2></div><button className="button secondary" onClick={() => setSettingsOpen(!settingsOpen)} aria-expanded={settingsOpen}><SlidersHorizontal size={15}/> Scan parameters</button></div>
    {settingsOpen && <div className="settings-grid"><label>Account equity ($)<input type="number" min="1" value={equity} onChange={e => setEquity(Number(e.target.value))}/></label><label>Risk per trade (%)<input type="number" min="0.01" max="5" step="0.1" value={riskPct} onChange={e => setRiskPct(Number(e.target.value))}/></label><label>Minimum 63d return (%)<input type="number" min="0" value={minMomentum} onChange={e => setMinMomentum(Number(e.target.value))}/></label><label>Minimum RS rank<input type="number" min="0" max="100" value={minRank} onChange={e => setMinRank(Number(e.target.value))}/></label><label>Breakout RVOL<input type="number" min="0.1" step="0.1" value={minRvol} onChange={e => setMinRvol(Number(e.target.value))}/></label><p>Apply with “Run daily scan”. A 126d return of 50% also satisfies momentum. Other defaults and all parameters are available through the API.</p></div>}
    <div className="toolbar"><label className="search"><Search size={16}/><input placeholder="Search symbol or company…" value={query} onChange={e => setQuery(e.target.value)} aria-label="Search stocks"/></label><div className="filters"><label>Status<select value={status} onChange={e => setStatus(e.target.value)}>{["ALL", "BUILDING", "READY", "TRIGGERED", "EXTENDED", "FAILED"].map(s => <option key={s} value={s}>{s === "ALL" ? "All setups" : s}</option>)}</select></label><label>RS rank<select value={minRs} onChange={e => setMinRs(Number(e.target.value))}><option value="0">Any rank</option><option value="70">70 and above</option><option value="80">80 and above</option><option value="90">90 and above</option></select></label></div></div>
    <div className="table-scroll"><table><thead><tr>{th("SYMBOL", "symbol")}{th("RS RANK", "rs")}{th("63D RETURN", "return63")}{th("ADR 20", "adr")}{th("RVOL", "rvol")}{th("PIVOT", "pivot")}<th>SETUP STATUS</th>{th("R / R", "rr")}<th>PLAN</th><th><span className="sr-only">Detail</span></th></tr></thead><tbody>{rows.map(c => <tr key={c.symbol}>
      <td><Link href={`/stocks/${c.symbol}`} className="symbol-link"><span className="ticker-icon">{c.symbol.slice(0, 2)}</span><span><strong>{c.symbol}</strong><small>{c.name}</small></span></Link></td>
      <td><span className="rs-number">{num(c.indicators.rs_percentile, 0)}</span><span className="rank-track"><span style={{ width: `${c.indicators.rs_percentile ?? 0}%` }}/></span></td><td className={(c.indicators.return_63 ?? 0) >= 0 ? "positive" : "negative"}>{pct(c.indicators.return_63)}</td><td>{c.indicators.adr20_pct == null ? "—" : `${num(c.indicators.adr20_pct)}%`}</td><td className={(c.indicators.rvol ?? 0) >= 1.5 ? "emphasis" : ""}>{num(c.indicators.rvol)}×</td><td>${num(c.pivot)}</td><td><span className={`status ${c.status.toLowerCase()}`}>{c.status === "TRIGGERED" && <Check size={11}/>}<span>{c.status}</span></span></td><td>{c.plan.reward_risk ? `${num(c.plan.reward_risk, 1)}R` : "—"}<small className="cell-note">hypothesis</small></td><td>{c.plan.eligible ? <span className="positive">{c.plan.shares} shares</span> : <span className="muted">Ineligible</span>}</td><td><Link className="row-arrow" aria-label={`View ${c.symbol}`} href={`/stocks/${c.symbol}`}><ArrowUpRight size={17}/></Link></td>
    </tr>)}</tbody></table>{rows.length === 0 && <div className="table-empty"><Search size={24}/><h3>{data.candidates.length ? "No setups match these filters" : "Your research starts here"}</h3><p>{data.candidates.length ? "Try another symbol, status, or RS threshold." : "Load historical data, then run a daily scan. The README includes a synthetic demo and provider ingestion commands."}</p></div>}</div>
    <div className="table-footer"><span>Showing {rows.length} of {data.candidates.length} stocks · RS ranks use {data.rs_observations ?? 0} observed common stocks</span><span>DAILY CLOSE CONFIRMATION <ArrowRight size={13}/></span></div></section>
    <div className="bottom-notes"><div><span className="tiny-dot"/> <strong>Ready is conditional.</strong> A pivot cross without sufficient volume is not confirmed.</div><div>Scan observed {data.as_of ? new Date(data.as_of).toLocaleString("en-AU", { timeZoneName: "short" }) : "—"}</div></div>
  </>;
}
