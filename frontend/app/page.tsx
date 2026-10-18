import { api } from "@/lib/api";
import type { DashboardData } from "@/lib/types";
import Dashboard from "@/components/dashboard";

export const dynamic = "force-dynamic";
export default async function Page() {
  try {
    const data = await api<DashboardData>("dashboard");
    return <Dashboard data={data} />;
  } catch {
    return <section className="empty-state"><span className="eyebrow">CONNECTION REQUIRED</span><h1>The research API is unavailable.</h1><p>Start the backend and apply database migrations. See the README for local and Docker instructions.</p><a className="button" href="/">Retry connection</a></section>;
  }
}
