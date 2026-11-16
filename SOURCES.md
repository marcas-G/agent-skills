# Origins, provenance and portability

This repository consolidates **general-purpose** skills and Claude Code plugins originally developed in separate repositories. Original project repositories are left untouched. Sources were copied from their default branches on 2026-11-16, and project-specific artifacts, examples containing user project state, generated binary caches, and engineering process documents were deliberately excluded.

| Bundled directory | Original source | Mode |
|---|---|---|
| `plugins/plainkit/` | https://github.com/marcas-G/plainkit (main) | Source plugin, 3 original skills |
| `plugins/req-collector/` | https://github.com/marcas-G/req-collector (main) | Runtime and instruction files only |
| `plugins/fractal/` | https://github.com/marcas-G/fractal (main) | Runtime, 10 stage skills, hooks, tests; no cached bytecode |
| `plugins/refactor-agent/` | https://github.com/marcas-G/refactor-agent (main; original `refactor-agent/` subfolder) | Runtime and internal skills only |
| `plugins/test-enforcer/` | https://github.com/marcas-G/test-enforcer (main) | Full plugin runtime |
| `plugins/optloop/` | https://github.com/marcas-G/optloop (master; original `plugins/optloop/` subfolder) | Full plugin runtime |

Portable `skills/plain`, `skills/termcard`, `skills/cross-domain-exploration`, and `skills/req-collect` are direct skill copies (including references/examples). Other top-level skill entrypoints are cross-agent adapters and **must not be confused with full enforcement or hooks**.

The private original repositories `req-collector`, `refactor-agent`, and `test-enforcer` were selectively copied into this **public** consolidated distribution at the repository owner's request. No engineering notes or project-specific state from those repositories were copied.

The original `plainkit` and `fractal` license files are kept beside their code. Do not assume all components share the same license; check origin and ownership before external redistribution.

## Capability differences

- **Claude Code Marketplace**: original hooks, command files, scripts and agents distributed as 6 complete native plugins.
- **Codex, Cursor, OpenCode, Gemini CLI, GitHub Copilot**: 8 standard Agent Skills with optional bundled runtime files. The `SKILL.md` frontmatter and folder conventions are portable; Claude-specific hook/command registration is *not* portable.
- An individual skill being discovered does not prove every corresponding runtime dependency or CLI is available.
