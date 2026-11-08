import {isAuthenticated} from '../../../lib/auth';
import {backendResponse} from '../../../lib/backend';
import {treatmentExports} from '../../../lib/treatment';
export const dynamic='force-dynamic';
export async function GET(request:Request):Promise<Response>{
 if(!await isAuthenticated())return Response.json({error:'Sign in required'},{status:401});
 const kind=new URL(request.url).searchParams.get('download')||'methods';
 if(!(treatmentExports as readonly string[]).includes(kind))return Response.json({error:'Unknown export'},{status:422});
 try{
  const response=await backendResponse(`/api/v1/research/treatment-study?download=${kind}`);
  if(!response?.ok)return Response.json({error:'Treatment evidence unavailable'},{status:503});
  const ext=kind==='report'?'json':kind==='methods'?'md':'csv';
  return new Response(response.body,{headers:{
   'Content-Type':ext==='csv'?'text/csv; charset=utf-8':ext==='md'?'text/markdown; charset=utf-8':'application/json',
   'Content-Disposition':`attachment; filename="bpdb-treatment-${kind}.${ext}"`,
   'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
  }});
 }catch{return Response.json({error:'Treatment export unavailable'},{status:503});}
}
