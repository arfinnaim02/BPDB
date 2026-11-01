"use server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { authConfigured } from "../../lib/auth";
import { createSession, sameSecret, SESSION_COOKIE, SESSION_SECONDS } from "../../lib/session";

export async function login(form: FormData): Promise<void> {
  if (!authConfigured()) redirect("/login?error=configuration");
  const password = form.get("password");
  if (typeof password !== "string" || password.length > 1024 ||
      !sameSecret(password, process.env.DASHBOARD_PASSWORD!)) {
    redirect("/login?error=invalid");
  }
  const jar = await cookies();
  jar.set(SESSION_COOKIE, createSession(process.env.SESSION_SECRET!), {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict",
    path: "/", maxAge: SESSION_SECONDS,
  });
  redirect("/");
}

export async function logout(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/login");
}
