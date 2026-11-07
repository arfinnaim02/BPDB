import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { reportExport } from "../../../lib/reports";
export const dynamic="force-dynamic";
export async function GET(request:Request):Promise<Response> {
 if(!await isAuthenticated()) return Response.json({error:"Sign in required"},{status:401});
 const q=new URL(request.url).searchParams;
 const params=reportExport(q.get("download")||"",q.get("expected_id")||"",q.get("figure")||undefined);
 if(!params) return Response.json({error:"Invalid report export"},{status:422});
 try {
 const r=await backendResponse(`/api/v1/research/report?${params}`);
 if(r?.status===409) return Response.redirect(new URL("/reports?changed=1",request.url),303);
 if(!r?.ok) return Response.json({error:"Report export unavailable; refresh and retry"},{status:503});
 const headers=new Headers({"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"});
 for(const h of ["Content-Type","Content-Disposition","X-Report-ID","X-Content-SHA256"]) {const v=r.headers.get(h);if(v)headers.set(h,v);}
 return new Response(r.body,{headers});
 }catch{return Response.json({error:"Report service unavailable; retry after checking API readiness"},{status:503});}
}
