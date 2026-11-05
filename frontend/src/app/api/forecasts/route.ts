import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { forecastLimit, validIssue } from "../../../lib/forecasts";
export const dynamic = "force-dynamic";
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({ error: "Sign in required" }, { status: 401 });
  const q = new URL(request.url).searchParams;
  const issue = q.get("issue");
  if (issue && !validIssue(issue)) return Response.json({ error: "Invalid forecast" }, { status: 422 });
  try {
    const response = await backendResponse(issue ? `/api/v1/forecasts/${issue}` : `/api/v1/forecasts?limit=${forecastLimit(q.get("limit"))}&download=csv`);
    if (!response?.ok) return Response.json({ error: "Forecast export unavailable" }, { status: response?.status === 404 ? 404 : 503 });
    return new Response(response.body, { headers: { "Content-Type": issue ? "application/json" : "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="bpdb-research-forecast-${issue ? issue.slice(0,12)+'.json' : 'history.csv'}"`,
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
  } catch { return Response.json({ error: "Forecast export unavailable" }, { status: 503 }); }
}
