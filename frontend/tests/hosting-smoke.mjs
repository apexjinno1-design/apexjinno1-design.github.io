// Requires a production build and a running local research API. No real passwords are printed.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { cpSync } from "node:fs";
import { once } from "node:events";

cpSync(".next/static", ".next/standalone/.next/static", { recursive: true });
const password = randomBytes(24).toString("hex");
const childEnv = { ...process.env, HOSTNAME: "127.0.0.1", PORT: "3100", REQUIRE_AUTH: "true",
  SCREENER_USER: "fixture-user", SCREENER_PASSWORD: password, API_HOST: "127.0.0.1", API_PORT: "8000" };
delete childEnv.API_BASE_URL;
delete childEnv.MASSIVE_API_KEY;
const server = spawn(process.execPath, [".next/standalone/server.js"], { env: childEnv, stdio: "ignore" });
const origin = "http://127.0.0.1:3100";
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { if ((await fetch(`${origin}/api/web-health`)).ok) { ready = true; break; } } catch {}
    await new Promise(resolve => setTimeout(resolve, 150));
  }
  assert.ok(ready, "Production server must become ready");
  for (const path of ["/", "/stocks/DEMOA", "/backtests"]) {
    const response = await fetch(origin + path);
    assert.equal(response.status, 401, `${path} must require authentication`);
    assert.match(response.headers.get("www-authenticate"), /Basic/);
  }
  assert.equal((await fetch(`${origin}/api/scan`, { method: "POST", body: "{}" })).status, 401);
  assert.equal((await fetch(origin, { headers: { Authorization: "Basic d3Jvbmc6d3Jvbmc=" } })).status, 401);
  const headers = { Authorization: `Basic ${Buffer.from(`fixture-user:${password}`).toString("base64")}` };
  const response = await fetch(origin, { headers });
  assert.equal(response.status, 200);
  assert.match(response.headers.get("cache-control"), /private.*no-store/);
  assert.match(await response.text(), /SYNTHETIC DEMO DATA/);
  const scan = await fetch(`${origin}/api/scan`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: "{}" });
  assert.equal(scan.status, 200);
  assert.ok((await scan.json()).candidates.length > 0);
  console.log("Hosting smoke passed: public health, protected pages/scan, rejected wrong password, authenticated dashboard/scan, private caching and API_HOST routing");
} finally {
  server.kill("SIGTERM");
  await once(server, "exit");
}
