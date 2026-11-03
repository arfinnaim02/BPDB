import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { auditFilters } from "../../../lib/audit-filters";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({error:"Sign in required"},{status:401});
  const f = auditFilters(Object.fromEntries(new URL(request.url).searchParams));
  if(f.error) return Response.json({error:f.error},{status:422});
  try {
    const upstream = await backendResponse(`/api/v1/dataset/recovery-worklist?${f.dates}`);
    if (!upstream?.ok) return Response.json({error:upstream?.status===422
      ? "Select at most 3,660 calendar days within known history."
      : "Recovery worklist unavailable. Check API availability."},{status:upstream?.status===422?422:503});
    return new Response(upstream.body,{headers:{"Content-Type":"application/json; charset=utf-8",
      "Content-Disposition":'attachment; filename="bpdb-recovery-worklist.json"',
      "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
  } catch { return Response.json({error:"Worklist timed out. Narrow the date range and retry."},{status:503}); }
}
