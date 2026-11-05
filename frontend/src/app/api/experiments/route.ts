import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { experimentExports } from "../../../lib/experiment";
export const dynamic = "force-dynamic";
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({ error: "Sign in required" }, { status: 401 });
  const kind = new URL(request.url).searchParams.get("download") || "test_report";
  if (!(experimentExports as readonly string[]).includes(kind)) return Response.json({ error: "Unknown export" }, { status: 422 });
  try {
    const response = await backendResponse(`/api/v1/research/release1?download=${kind}`);
    if (!response?.ok) return Response.json({ error: "Experiment unavailable" }, { status: 503 });
    const extension = kind === "test_report" ? "md" : ["predictions", "selection"].includes(kind) ? "csv" : "json";
    return new Response(response.body, { headers: { "Content-Type": extension === "md" ? "text/markdown; charset=utf-8" : extension === "csv" ? "text/csv; charset=utf-8" : "application/json",
      "Content-Disposition": `attachment; filename="bpdb-release1-${kind}.${extension}"`,
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
  } catch { return Response.json({ error: "Experiment export unavailable" }, { status: 503 }); }
}
