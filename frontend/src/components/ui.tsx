import Link from "next/link";
import { logout } from "../app/login/actions";
import { timestamp } from "../lib/format";

export function Icon({ name = "grid" }: { name?: string }) {
  const paths: Record<string, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    collection: <><path d="M4 7h16v13H4zM7 4h10M9 11h6M9 15h6"/></>,
    dataset: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/></>,
    quality: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/></>,
    bolt: <path d="m13 2-9 12h7l-1 8L21 9h-8z"/>,
    arrow: <path d="m9 5 7 7-7 7"/>,
  };
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.grid}</svg>;
}
const navigation = [
  ["/", "Overview", "grid"], ["/collection", "Collection history", "collection"],
  ["/dataset", "Master dataset", "dataset"], ["/quality", "Data quality", "quality"],
  ["/analytics", "Generation & demand", "bolt"],
  ["/analytics/comparisons", "Trends & comparisons", "grid"],
  ["/analytics/research", "Frozen research analysis", "grid"],
  ["/analytics/experiments", "Forecast experiments", "bolt"],
  ["/analytics/models", "Model comparison", "bolt"],
  ["/analytics/final-evaluation", "Final evaluation", "bolt"],
  ["/quality/review", "Measurement review", "quality"],
  ["/quality/missing", "Missing data", "dataset"],
  ["/quality/prepare", "Research preparation", "dataset"],
];
export function Shell({ active, children }: { active: string; children: React.ReactNode }) {
  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-mark"><Icon name="bolt"/></span><span>BPDB<span className="brand-sub">INTELLIGENCE</span></span></Link>
      <div className="workspace-label">RESEARCH WORKSPACE</div>
      <nav aria-label="Main navigation">{navigation.map(([href, label, icon]) => <Link href={href} key={href} className={`nav-item ${active === href ? "active" : ""}`} aria-current={active === href ? "page" : undefined}><Icon name={icon}/>{label}</Link>)}</nav>
      <div className="sidebar-bottom"><span className="tiny-label">DATA FOUNDATION</span><p>Official reports.<br/>Traceable observations.</p><span className="sidebar-tag">National · Page 1</span></div>
    </aside>
    <div className="main-wrap"><header className="topbar"><span className="breadcrumb">Workspace <span>/</span> <strong>{navigation.find(n => n[0] === active)?.[1]}</strong></span><div className="topbar-right"><span className="timezone">Asia/Dhaka · UTC+6</span><form action={logout}><button className="text-button">Sign out</button></form><span className="avatar" aria-hidden="true">BP</span></div></header>
      <main id="main" className="main-content">{children}</main>
      <footer className="footer"><span>BPDB Intelligence · Research data management</span><span>Official source values · Neon canonical records</span></footer>
    </div>
  </div>;
}
export function Heading({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: React.ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div><div className="heading-actions">{children}</div></div>;
}
export function Badge({ status }: { status: string }) {
  const kind = ["succeeded", "validated"].includes(status) ? "success" : status === "failed" ? "danger" : "warning";
  return <span className={`badge ${kind}`}><span className="dot"/>{status.replaceAll("_", " ")}</span>;
}
export function ErrorPanel({ message }: { message: string }) {
  return <section className="notice error-notice" role="alert"><strong>Data could not be loaded</strong><p>{message}</p><p>Refresh the page after checking the service. No cached or sample records are substituted.</p></section>;
}
export function Empty({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><Icon name="dataset"/><h3>{title}</h3><p>{text}</p></div>;
}
export function Stat({ label, value, detail, accent = false }: { label: string; value: string; detail: string; accent?: boolean }) {
  return <article className={`stat-card ${accent ? "stat-accent" : ""}`}><p className="stat-label">{label}</p><strong className="stat-value">{value}</strong><p className="stat-detail">{detail}</p></article>;
}
export function Updated({ at }: { at: string }) { return <span className="updated">Read at {timestamp(at)} BD</span>; }




