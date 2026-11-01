import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE = "bpdb_session";
export const SESSION_SECONDS = 8 * 60 * 60;
const digest = (value: string) => createHash("sha256").update(value).digest();

export function sameSecret(actual: string, expected: string): boolean {
  return timingSafeEqual(digest(actual), digest(expected));
}

export function createSession(secret: string, now = Date.now()): string {
  const payload = String(Math.floor(now / 1000) + SESSION_SECONDS);
  const signature = createHmac("sha256", secret).update(payload).digest("base64url");
  return `${payload}.${signature}`;
}

export function validSession(token: string | undefined, secret: string, now = Date.now()): boolean {
  if (!token || secret.length < 32) return false;
  const pieces = token.split(".");
  if (pieces.length !== 2 || !/^\d{10}$/.test(pieces[0])) return false;
  const expires = Number(pieces[0]);
  const current = Math.floor(now / 1000);
  if (expires <= current || expires > current + SESSION_SECONDS) return false;
  const expected = createHmac("sha256", secret).update(pieces[0]).digest("base64url");
  return sameSecret(pieces[1], expected);
}
