import { createHash, timingSafeEqual } from "node:crypto";

type AccessSettings = { required: boolean; username?: string; password?: string };
export type AccessDecision = "allow" | "challenge" | "unconfigured";

export function checkAccess(authorization: string | null, settings: AccessSettings): AccessDecision {
  const { username, password, required } = settings;
  if (!username || !password) {
    return required || username || password ? "unconfigured" : "allow";
  }
  const supplied = authorization?.match(/^Basic\s+([A-Za-z0-9+/]+=*)$/i)?.[1];
  if (!supplied) return "challenge";
  const expected = Buffer.from(`${username}:${password}`, "utf8").toString("base64");
  const digest = (value: string) => createHash("sha256").update(value).digest();
  return timingSafeEqual(digest(supplied), digest(expected)) ? "allow" : "challenge";
}
