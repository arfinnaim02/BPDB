import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { preparationFilters } from "../../../lib/preparation";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({ error: "Sign in required" }, { status: 401 });
  const url = new URL(request.url);
  const f = preparationFilters(Object.fromEntries(url.searchParams));
  const expected = url.searchParams.get("expected_id");
  if (!f.entered || f.error || !expected || !/^[a-f0-9]{64}$/.test(expected)) {
    return Response.json({ error: f.error || "Preview the snapshot before downloading." }, { status: 422 });
  }
  const q = new URLSearchParams(f.query); q.set("download", "true"); q.set("expected_id", expected);
  try {
    const upstream = await backendResponse(`/api/v1/dataset/preparation?${q}`);
    if (!upstream?.ok) return Response.json({ error: upstream?.status === 409
      ? "Canonical inputs changed. Refresh the preparation preview before downloading."
      : "Preparation unavailable. Check dates against known history and API availability." },
    { status: upstream?.status === 409 ? 409 : upstream?.status === 422 ? 422 : 503 });
    return new Response(upstream.body, { headers: { "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="bpdb-research-${expected.slice(0, 12)}.zip"`,
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
  } catch { return Response.json({ error: "Preparation timed out. Retry with a smaller window." }, { status: 503 }); }
}
