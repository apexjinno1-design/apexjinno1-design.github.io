import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Check, Minus } from "lucide-react";
import { api } from "@/lib/api";
import { num, pct } from "@/lib/format";
import type { StockDetail } from "@/lib/types";
import PriceChart from "@/components/price-chart";

export const dynamic = "force-dynamic";
export default async function Page({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  let stock: StockDetail;
  try { stock = await api<StockDetail>(`stocks/${encodeURIComponent(symbol)}`); }
  catch { return <div className="empty-state"><h1>Stock data unavailable</h1><p>The symbol may be unknown, or the API is offline.</p><Link className="button" href="/">Back to dashboard</Link></div>; }
  const snap = stock.snapshot, plan = snap?.plan, setup = snap?.explanation;
  const last = stock.bars[stock.bars.length - 1];
  return <><Link href="/" className="back-link"><ArrowLeft size={14}/> Market dashboard</Link><div className="page-heading"><div><span className="eyebrow">{stock.provider === "demo" ? "SYNTHETIC RESEARCH FIXTURE" : "US EQUITY RESEARCH"}</span><h1>{stock.symbol} <span className="stock-name">{stock.name}</span></h1><p>{stock.sector || "Sector unavailable"} · Session {stock.last_session || "unavailable"} · {stock.last_session === stock.expected_session ? "Latest completed session" : "STALE DATA"}</p></div><div className="detail-price">${num(last?.close)}<small>{pct(snap?.indicators.return_1)} daily</small></div></div>
    <div className="detail-grid"><div>{stock.bars.length ? <PriceChart bars={stock.bars} plan={plan} pivot={setup?.pivot} baseLow={setup?.base_low}/> : <div className="empty-state">No completed daily bars available.</div>}
    <section className="white-panel"><span className="eyebrow">SETUP QUALIFICATION</span><h2>The evidence behind the setup</h2>{setup ? <><div className="check-grid">{Object.entries(setup.checks).map(([key, pass]) => <div className={pass ? "check-pass" : "check-fail"} key={key}>{pass ? <Check size={16}/> : <Minus size={16}/>}<span>{key.replaceAll("_", " ")}</span><small>{pass ? "MET" : "UNMET"}</small></div>)}</div><p className="muted">{setup.base_sessions ?? "—"} session base · Price confirmed: {setup.price_confirmed ? "yes" : "no"} · Volume confirmed: {setup.volume_confirmed ? "yes" : "no"}. Quality thresholds use prior-session information. Only a completed close with volume confirmation can trigger a daily setup.</p></> : <p>Run a daily scan to produce an indicator and setup snapshot.</p>}</section>
    <section className="white-panel"><span className="eyebrow">CATALYSTS</span><h2>Verification required <ArrowUpRight size={16}/></h2><p className="muted">{stock.catalyst_note}</p></section></div>
    <aside className="plan-panel"><div className="card-kicker">CONDITIONAL TRADING PLAN</div><h2>{snap ? <span className={`status ${snap.status.toLowerCase()}`}>{snap.status}</span> : "No snapshot"}</h2><p className="muted">1–5 session horizon. Research plan only; no order is placed.</p><dl>{[["Breakout pivot", setup?.pivot], ["Entry trigger", setup?.entry_trigger], ["Planning entry", plan?.entry], ["Technical stop", plan?.stop], ["Hypothetical target", plan?.target]].map(([label, v]) => <div key={String(label)}><dt>{label}</dt><dd>${num(v as number | undefined)}</dd></div>)}</dl><div className="plan-divider"/><dl><div><dt>Stop distance</dt><dd>{num(plan?.stop_pct)}%</dd></div><div><dt>Reward / risk</dt><dd>{num(plan?.reward_risk, 1)}R</dd></div><div><dt>Risk per share</dt><dd>${num(plan?.risk_per_share)}</dd></div><div><dt>Risk-limited shares</dt><dd>{num(plan?.max_shares_risk, 0)}</dd></div><div><dt>Allocation-limited shares</dt><dd>{num(plan?.max_shares_allocation, 0)}</dd></div></dl><div className={`position-box ${plan?.eligible ? "eligible" : ""}`}><span>{plan?.eligible ? "SUGGESTED SIZE" : "INELIGIBLE"}</span><strong>{plan?.shares ?? 0} <small>shares</small></strong></div>{plan?.reasons?.map(r => <p className="plan-reason" key={r}>{r}</p>)}<p className="fine-print">Target is a planning multiple of technical risk, not an expected price or a probability estimate. A stop order can fill below its level.</p><div className="plan-divider"/><span className="eyebrow">SNAPSHOT OBSERVED</span><p className="fine-print">{snap?.as_of || "No scan yet"} · {stock.provider} · {stock.adjusted ? "Adjusted" : "Unadjusted"}</p></aside></div>
  </>;
}
