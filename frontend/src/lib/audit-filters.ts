import { single, validDate, type Params } from "./filters.ts";
const page = (raw: string | undefined) => raw && /^\d+$/.test(raw) && Number(raw) >= 1 && Number(raw) <= 100000 ? Number(raw) : 1;
export function auditFilters(params: Params) {
  const start = single(params.start_date) || "";
  const end = single(params.end_date) || "";
  const gapPage = page(single(params.gap_page));
  const sourcePage = page(single(params.source_page));
  const rawSize = Number(single(params.gap_page_size));
  const pageSize = [10,20,50].includes(rawSize) ? rawSize : 20;
  const error = (start && !validDate(start)) || (end && !validDate(end))
    ? "Use valid dates in YYYY-MM-DD format." : start && end && start > end
      ? "From date must be on or before to date." : null;
  const dates = new URLSearchParams();
  if(start) dates.set("start_date",start); if(end) dates.set("end_date",end);
  const query = new URLSearchParams(dates);
  query.set("gap_page",String(gapPage)); query.set("source_page",String(sourcePage));
  query.set("gap_page_size",String(pageSize));
  return {start,end,gapPage,sourcePage,pageSize,error,dates,query};
}
export function auditHref(f: ReturnType<typeof auditFilters>, gap: number, source: number, section: string) {
  const q = new URLSearchParams(f.query); q.set("gap_page",String(gap)); q.set("source_page",String(source));
  return `/quality/audit?${q}#${section}`;
}
