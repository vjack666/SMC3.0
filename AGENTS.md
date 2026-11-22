## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- Run Graphify from this project using `.venv/Scripts/graphify.exe`. Start codebase questions with `query "<question>" --budget 500` when the local graph is available. Use `path`, `explain` and `section` to narrow results before checking the source.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying source or project documentation, run `.venv/Scripts/graphify.exe update .` for a local refresh. Keep graph output local and retain the source allowlist in `.graphifyignore`.
