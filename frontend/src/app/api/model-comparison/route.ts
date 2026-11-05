import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { comparisonExports } from "../../../lib/model-comparison";
export const dynamic = "force-dynamic";
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({ error: "Sign in required" }, { status: 401 });
  const kind = new URL(request.url).searchParams.get("download") || "test_report";
  if (!(comparisonExports as readonly string[]).includes(kind)) return Response.json({ error: "Unknown export" }, { status: 422 });
  try {
    const response = await backendResponse(`/api/v1/research/release2?download=${kind}`);
    if (!response?.ok) return Response.json({ error: "Comparison unavailable" }, { status: 503 });
    const ext = kind === "test_report" ? "md" : ["predictions", "selection"].includes(kind) ? "csv" : "json";
    return new Response(response.body, { headers: {
      "Content-Type": ext === "md" ? "text/markdown; charset=utf-8" : ext === "csv" ? "text/csv; charset=utf-8" : "application/json",
      "Content-Disposition": `attachment; filename="bpdb-release2-${kind}.${ext}"`,
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    } });
  } catch { return Response.json({ error: "Comparison export unavailable" }, { status: 503 }); }
}
