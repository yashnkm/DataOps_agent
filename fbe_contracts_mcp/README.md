# fbe-contracts-mcp

MCP server exposing the FBE contract analysis capability to any MCP-compatible agent (Claude Code, Cursor, Claude Desktop, GitHub Copilot, etc.).

## What it exposes

### Tools
| Tool | Purpose |
|---|---|
| `list_contracts()` | One-liner metadata for every contract in the DB |
| `query_contracts(sql, limit)` | Read-only SELECT against `contracts`, `fee_schedules`, `transactions` |
| `search_contract_documents(query, k)` | RAG search across contract PDFs |
| `check_fee_compliance(contract_id, date_from?, date_to?)` | Opinionated audit — returns transactions whose fee exceeds the contract fee schedule |

### Resources
- `contract://{contract_id}` — full PDF text + metadata header

## Install

```bash
pip install fbe-contracts-mcp
```

Requires a populated Postgres DB using the FBE schema (`database/schemas/contracts_schema.sql`) and the FAISS index from the Gradio POC. Set these env vars:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=financial_services_db
export DB_USER=postgres
export DB_PASSWORD=root
export GOOGLE_API_KEY_SOL_4=...      # for the RAG tool's synthesis step
export DOCS_DIR=/path/to/contract/pdfs
```

## Run

```bash
python -m fbe_contracts_mcp
```

Stays running over stdio until the client disconnects.

## Wire into an agent

### Claude Code
Add to `~/.claude/settings.json`:
```jsonc
{
  "mcpServers": {
    "fbe-contracts": {
      "command": "python",
      "args": ["-m", "fbe_contracts_mcp"],
      "env": {
        "DB_HOST": "localhost",
        "DB_NAME": "financial_services_db",
        "DB_USER": "postgres",
        "DB_PASSWORD": "root",
        "GOOGLE_API_KEY_SOL_4": "..."
      }
    }
  }
}
```

### Cursor
Add to `.cursor/mcp.json` in your project — same shape.

### Claude Desktop
Add to `claude_desktop_config.json` — same shape.

## Example questions once configured

- "What contracts are in the FBE database?"
- "Show me the fee schedule for the DBS MasterCard contract."
- "Find transactions where the fee charged was higher than what the contract specifies."
- "What fraud protection services does VISA provide in the DBS 2020 agreement?"
