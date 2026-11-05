import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { finalExports } from "../../../lib/final-evaluation";
export const dynamic = "force-dynamic";
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({ error: "Sign in required" }, { status: 401 });
  const kind = new URL(request.url).searchParams.get("download") || "test_report";
  if (!(finalExports as readonly string[]).includes(kind)) return Response.json({ error: "Unknown export" }, { status: 422 });
  try {
    const response = await backendResponse(`/api/v1/research/release3?download=${kind}`);
    if (!response?.ok) return Response.json({ error: "Final evaluation unavailable" }, { status: 503 });
    const ext = kind === "test_report" ? "md" : ["models", "report"].includes(kind) ? "json" : "csv";
    return new Response(response.body, { headers: {
      "Content-Type": ext === "md" ? "text/markdown; charset=utf-8" : ext === "csv" ? "text/csv; charset=utf-8" : "application/json",
      "Content-Disposition": `attachment; filename="bpdb-release3-${kind}.${ext}"`,
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    } });
  } catch { return Response.json({ error: "Final evaluation export unavailable" }, { status: 503 }); }
}
