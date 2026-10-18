export type Plan = {
  eligible: boolean; shares: number; entry?: number; stop?: number; target?: number;
  stop_pct?: number; reward_risk?: number; risk_per_share?: number; upside_pct?: number;
  max_shares_risk?: number; max_shares_allocation?: number; reasons?: string[];
};
export type Candidate = {
  symbol: string; name: string; sector: string | null; session: string; provider: string;
  status: string; qualified: boolean; score: number; base_sessions?: number;
  pivot?: number; base_low?: number; entry_trigger?: number; price_confirmed?: boolean; volume_confirmed?: boolean;
  checks: Record<string, boolean>; indicators: Record<string, number | null>; plan: Plan;
};
export type Regime = { regime: string | null; reason: string; evidence?: Record<string,
  { close: number; above_sma20: boolean; above_sma50: boolean; sufficient_history: boolean }> };
export type DashboardData = {
  as_of: string | null; session: string | null; expected_session: string; stale: boolean;
  regime: Regime; candidates: Candidate[]; universe_size: number; rs_observations?: number;
  data_mode: string; ep: { available: boolean; reason: string };
};
export type Bar = { time: string; open: number; high: number; low: number; close: number;
  volume: number; sma10: number | null; sma20: number | null; sma50: number | null };
export type StockDetail = {
  symbol: string; name: string; sector: string | null; provider: string; adjusted: boolean;
  bars: Bar[]; last_session: string; expected_session: string; catalyst_note: string;
  snapshot: { as_of: string; session: string; indicators: Record<string, number | null>; status: string;
    plan: Plan; explanation: Candidate; provenance: { parameters: Record<string, unknown> } } | null;
};
