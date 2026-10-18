import "server-only";

const base = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function api<T>(path: string): Promise<T> {
  const response = await fetch(`${base}/api/${path}`, { cache: "no-store", signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`Research API returned ${response.status}`);
  return response.json() as Promise<T>;
}
