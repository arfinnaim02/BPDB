# Historical recovery batch: 30 January–25 May 2024

Reviewed 4 November 2026. [Hosted investigation](https://github.com/arfinnaim02/BPDB/actions/runs/41786772769)
at commit `f1329d18b2ab623e02da08a611a5f52f0cb413a7` succeeded.

## Bounded coverage

The fresh Neon worklist contains five canonical gaps in this window. All ten
candidate URLs were investigated; they represent nine distinct PDF byte revisions.
Every saved PDF matches its journal SHA-256 and its independently downloaded
artifact copy. Original PDFs, diagnostic text, worklist, candidate plan and reports
were preserved in Drive. No sources or measurements were written to Neon and no
canonical records were promoted.

Plan SHA-256: `2f471458c78a4745c5399f29461d4428508e108898d3ec36bbaa242764767617`.
Artifact SHA-256: `4444ad4f81a8c88f48e62b977a2bff703d37bde424d55f4e294afd807b81be63`.
All candidates in this window were attempted; next_offset is null.

## Findings

The date column below is the parser's operational date, not an archive hint.
A clean parse alone does not approve recovery.

| PDF | Candidate gap | Parsed operational date | Outcome |
| --- | --- | --- | --- |
| 7450page1.pdf | 2024-01-30 | 2024-01-21 | Date mismatch held |
| 7452page1.pdf | 2024-01-30 | 2024-01-21 | Same bytes as 7450; date mismatch held |
| 7554page1.pdf | 2024-03-22 | 2024-03-21 | Date mismatch held |
| 7556page1.pdf | 2024-03-22 | Unparsed | Parser identifies station-table first page |
| 7586page1.pdf | 2024-04-07 | 2024-04-06 | Date mismatch held |
| 7588page1.pdf | 2024-04-07 | 2024-04-07 | Maximum generation and energy labels not extracted |
| 7610page1.pdf | 2024-04-20 | 2024-04-19 | Date mismatch held |
| 7614page1.pdf | 2024-04-20 | 2024-04-20 | Five observations pass; original PDF visually verified |
| 7682page1.pdf | 2024-05-25 | 2024-05-24 | Date mismatch held |
| 7684page1.pdf | 2024-05-25 | 2024-05-25 | Energy token rejected; original PDF reviewed |

Overall: six date mismatches, two matching-date parser holds, one unsupported
first page, and one clean matching-date candidate. All ten saved checksums match.
Archive hints must never be used to reassign the mismatched PDF values to gaps.

## Original-source review

For 7614, the rendered original shows operational date 20 April and reporting date
21 April 2024. All five labeled source values agree with extraction. The pinned
review manifest is `recovery_reviews/2024-04-20.json`. This is approved evidence
for the next staging gate, not a claim that Neon already contains the repair.

For 7684, the rendered original has clear metric labels and energy 337.880 MKWH
for 25 May 2024. The text extraction places a separate load-factor percentage
immediately after the energy number. The existing conservative numeric guard
rejects that arrangement. A future parser fix must establish the column/label
boundary using source evidence and regression tests, while retaining protection
against genuinely split or malformed numeric tokens. No estimate is needed.

For 7588, the rendered page visibly clips left-side metric labels, including the
maximum-generation and total-energy rows. Their numeric positions are insufficient
to approve an unlabeled metric under the current policy. Keep held; seek a complete
source revision or independently supported alternate report. Do not infer labels
from neighboring dates.

## Acceptance and next action

Hosted parser/review regression gate: 27 passed. Both backend and foundation
checks passed; both Vercel deployment checks passed. No local office runtime or
secrets transfer was required.

Next: stage/readback/promote only the reviewed 20 April record using the existing
gap-only safeguards, then fix and independently verify the supported 25 May parser
case. The January/March gaps remain unresolved by these particular source files.
After recovery, regenerate a research snapshot before comparing analysis outputs.
