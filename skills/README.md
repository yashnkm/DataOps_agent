# fbe-skills

Three agent-skills that pair with the `fbe-contracts-mcp` server to turn any MCP-capable AI tool (Claude Code, Cursor, Claude Desktop, etc.) into an FBE domain expert.

## Skills

| Skill | Audience | Purpose |
|---|---|---|
| [`contract-compliance`](contract-compliance/SKILL.md) | Compliance analysts | SOP for auditing contract fees against transactions |
| [`fee-reconciliation`](fee-reconciliation/SKILL.md) | Data engineers | SQL recipes for recon queries, dashboards, batch audits |
| [`contract-onboarding`](contract-onboarding/SKILL.md) | Ops teams | Checklist + workflow for ingesting new contract PDFs |

## Why pair skills with MCP?

MCP gives an agent **access to data** (the `fbe-contracts` MCP server exposes Postgres + RAG). Skills give that agent **domain procedure**: which tool to use when, how to read the schema, where the subtle gotchas are. Without the skill, the agent has to rediscover the approach from scratch every session.

## Local install (for testing)

Copy the three skill folders into your global or project-scoped skills directory:

```bash
# project-scoped
mkdir -p .agents/skills/
cp -r skills/* .agents/skills/

# or global (user-level)
cp -r skills/* ~/.claude/skills/
```

Then restart your Claude Code / Cursor session — the skills should now be discoverable via the Skill tool.

## Publish to skills.sh (Phase 5)

```bash
npx skills publish contract-compliance
npx skills publish fee-reconciliation
npx skills publish contract-onboarding
```

Then anyone can install:
```bash
npx skills add your-org/fbe-skills@contract-compliance
```
