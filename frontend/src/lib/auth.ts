import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE, validSession } from "./session";

export function authConfigured(): boolean {
  return (process.env.DASHBOARD_PASSWORD?.length ?? 0) >= 12 &&
    (process.env.SESSION_SECRET?.length ?? 0) >= 32;
}

export async function isAuthenticated(): Promise<boolean> {
  if (!authConfigured()) return false;
  const jar = await cookies();
  return validSession(jar.get(SESSION_COOKIE)?.value, process.env.SESSION_SECRET!);
}

export async function requireSession(): Promise<void> {
  if (!await isAuthenticated()) redirect("/login");
}
