export const dynamic = "force-dynamic";
type Check = { label: string; message: string; ok: boolean };
async function check(label: string, path: string): Promise<Check> {
  const base = process.env.BACKEND_URL || "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${base}${path}`, {
      cache: "no-store", signal: AbortSignal.timeout(12000),
    });
    const body: unknown = await response.json();
    const message = body && typeof body === "object" && "detail" in body
      ? String(body.detail) : response.ok ? "Available" : "Unavailable";
    return { label, message, ok: response.ok };
  } catch {
    return { label, message: "Backend could not be reached", ok: false };
  }
}
export default async function Page() {
  const checks = await Promise.all([
    check("API process", "/health/live"), check("Database and migration", "/health/ready"),
  ]);
  return <main className="mx-auto max-w-4xl px-6 py-16">
    <p className="text-sm font-semibold uppercase tracking-widest text-slate-500">Research platform · Day 1</p>
    <h1 className="mt-3 text-4xl font-semibold">BPDB Intelligence</h1>
    <p className="mt-4 max-w-2xl text-lg text-slate-600">Data acquisition, forecasting and decision support for Bangladesh’s power sector.</p>
    <section aria-label="System health" className="mt-10 grid gap-4 sm:grid-cols-2">
      {checks.map(item => <article key={item.label} className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="font-semibold">{item.label}</h2>
        <p className={`mt-3 text-sm ${item.ok ? "text-emerald-700" : "text-amber-800"}`}>
          {item.ok ? "Ready: " : "Pending: "}{item.message}
        </p>
      </article>)}
    </section>
    <section className="mt-8 rounded-xl bg-slate-900 p-6 text-white">
      <h2 className="text-xl font-semibold">Research data pending</h2>
      <p className="mt-3 text-slate-300">No measurements or forecasts are displayed until authentic reports have been parsed and validated. The collector schedule, analytics and forecasting modules are planned for subsequent phases.</p>
    </section>
    <p className="mt-8 text-sm text-slate-600">Refresh this page after starting the API or applying migrations to check the connection again.</p>
  </main>;
}
