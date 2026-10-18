export function num(value: number | null | undefined, decimals = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : value.toLocaleString("en-US", { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
}
export function pct(value: number | null | undefined): string {
  return value == null ? "—" : `${num(value * 100)}%`;
}
