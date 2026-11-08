import { isAuthenticated } from "../../../lib/auth";
import { monthlyCost, predictionsCsv } from "../../../lib/monthly-cost";
export const dynamic = "force-dynamic";
export async function GET(request: Request): Promise<Response> {
 if (!await isAuthenticated()) return Response.json({error:"Sign in required"},{status:401});
 const kind=new URL(request.url).searchParams.get("download")||"predictions";
 if (!["predictions","report"].includes(kind)) return Response.json({error:"Unknown export"},{status:422});
 return new Response(kind==="predictions"?predictionsCsv():JSON.stringify(monthlyCost,null,2),{headers:{"Content-Type":kind==="predictions"?"text/csv; charset=utf-8":"application/json","Content-Disposition":`attachment; filename="bpdb-monthly-cost-20261108.${kind==="predictions"?"csv":"json"}"`,"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
}
