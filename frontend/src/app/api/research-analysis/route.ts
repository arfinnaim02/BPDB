import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { researchExports } from "../../../lib/research";
export const dynamic = "force-dynamic";
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({ error: "Sign in required" }, { status: 401 });
  const kind = new URL(request.url).searchParams.get("table") || "report";
  if (!(researchExports as readonly string[]).includes(kind)) return Response.json({ error: "Unknown analysis export" }, { status: 422 });
  try {
    const response = await backendResponse(`/api/v1/analytics/frozen-2024?download=${kind}`);
    if (!response?.ok) return Response.json({ error: "Verified analysis unavailable" }, { status: 503 });
    const extension = kind === "report" ? "json" : "csv";
    return new Response(response.body, { headers: {
      "Content-Type": extension === "json" ? "application/json" : "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="bpdb-frozen-2024-${kind}.${extension}"`,
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    } });
  } catch { return Response.json({ error: "Analysis export unavailable" }, { status: 503 }); }
}
