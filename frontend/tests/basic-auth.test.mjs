import { test } from "node:test";
import assert from "node:assert/strict";
import { checkAccess } from "../lib/basic-auth.ts";

const settings = { required: true, username: "fixture-user", password: "fixture-only-not-a-secret" };
const header = `Basic ${Buffer.from(`${settings.username}:${settings.password}`).toString("base64")}`;
test("local development permits absent credentials only when auth is not required", () => {
  assert.equal(checkAccess(null, { required: false }), "allow");
  assert.equal(checkAccess(null, { required: true }), "unconfigured");
});
test("partial configuration cannot silently disable access protection", () => {
  assert.equal(checkAccess(null, { required: false, username: "fixture" }), "unconfigured");
  assert.equal(checkAccess(null, { required: false, password: "fixture" }), "unconfigured");
});
test("valid Basic credentials allow access", () => {
  assert.equal(checkAccess(header, settings), "allow");
  assert.equal(checkAccess(header.replace("Basic", "basic"), settings), "allow");
});
test("missing, malformed and wrong credentials require authentication", () => {
  for (const value of [null, "Bearer fixture", "Basic !!!", "Basic d3Jvbmc6d3Jvbmc=", header + "x"]) {
    assert.equal(checkAccess(value, settings), "challenge");
  }
});
test("provided credentials activate protection even without REQUIRE_AUTH", () => {
  assert.equal(checkAccess(null, { ...settings, required: false }), "challenge");
});
