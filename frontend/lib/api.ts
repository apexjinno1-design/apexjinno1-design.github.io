import "server-only";

export const apiBaseUrl = process.env.API_BASE_URL || (process.env.API_HOST
  ? `http://${process.env.API_HOST}:${process.env.API_PORT || "8000"}`
  : "http://127.0.0.1:8000");

export async function api<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}/api/${path}`, { cache: "no-store", signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`Research API returned ${response.status}`);
  return response.json() as Promise<T>;
}
