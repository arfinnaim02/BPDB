# Decisions

- 2026-10-25: Both supplied text files have identical normalized content, SHA-256
  1fe62d461b0f25b9c8e8ca3d72ae724270efb26049853523a529dbef7941efbe.
- Only master instructions were attached locally. The earlier shared Drive folder was
  then accessed: collector/parser, CSV and ML project were audited. Originals were not changed.
  See EXISTING_CODE_AUDIT.md for the targeted audit and reuse decisions.
- Follow the requested stack and build Day 1 first. The frontend is a status shell only.
- Keep sources, extraction versions and canonical pointers separate. Several source
  categories can support one daily version through version_sources.
- Give production costs a dedicated normalized observation table.
- Build only the 12 core tables currently used by foundation services. Document later
  tables now; implement them with their real modules rather than empty placeholders.
- Treat archive-row dates as hints. Confirm operational dates inside original PDFs.
- Preserve missing values and original units. Never invent measurements or experiment metrics.
- Use SQLite for local constraint/transaction unit tests and PostgreSQL dialect SQL compilation;
  neither proves an actual Neon connection or concurrency behavior.
- Fail discovery on no PDF links. Never report collection success for a maintenance page.
- Keep same-origin source requests and disable redirects until source changes are reviewed.
