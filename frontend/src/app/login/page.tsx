import { redirect } from "next/navigation";
import { authConfigured, isAuthenticated } from "../../lib/auth";
import { Icon } from "../../components/ui";
import { login } from "./actions";
export const dynamic = "force-dynamic";
export default async function Login({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  if (await isAuthenticated()) redirect("/");
  const { error } = await searchParams;
  const configured = authConfigured();
  return <main className="login-page"><section className="login-story"><span className="brand"><span className="brand-mark"><Icon name="bolt"/></span>BPDB Intelligence</span><div><p className="eyebrow">BANGLADESH POWER SECTOR</p><h1>Every observation.<br/>Backed by a source.</h1><p>A research workspace for national records, trend analysis and forecasting results.</p></div><span className="login-foot">Official PDFs → validated records → research</span></section><section className="login-panel"><div className="login-card"><span className="tiny-label">RESEARCH WORKSPACE</span><h2>Welcome back.</h2><p>Sign in to manage your BPDB dataset.</p>
    {!configured ? <div className="notice"><strong>Setup required</strong><p>Configure DASHBOARD_PASSWORD (at least 12 characters) and SESSION_SECRET (at least 32 characters) on the frontend server.</p></div> : <form action={login} className="login-form"><label htmlFor="password">Workspace password</label><input id="password" name="password" type="password" autoComplete="current-password" required maxLength={1024}/>{error && <p role="alert" className="form-error">Sign-in failed. Check your password and try again.</p>}<button className="button primary" type="submit">Open workspace <Icon name="arrow"/></button></form>}
    <p className="login-note">Your session expires after 8 hours. Database and API credentials stay on the server.</p></div></section></main>;
}
