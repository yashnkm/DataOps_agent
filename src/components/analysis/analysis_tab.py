"""
Analysis tab — LangGraph agent UI with MCP Postgres tools and RAG tool.
Exposes a chatbot-style surface and a collapsible reasoning log.
"""

import json
import os
from typing import Any, Dict, List, Tuple

import gradio as gr
import psycopg2
from psycopg2.extras import RealDictCursor

from components.agent.langgraph_agent import AnalysisAgent


SCHEMA_SQL = """
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, ordinal_position
"""


def _render_schema_overview() -> str:
    try:
        with psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "financial_services_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        ) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SCHEMA_SQL)
                rows = cur.fetchall()
    except Exception as e:
        return f"❌ Could not read schema: {e}"

    if not rows:
        return "📭 No tables found outside system schemas."

    by_table: Dict[str, List[Tuple[str, str]]] = {}
    for r in rows:
        key = f"{r['table_schema']}.{r['table_name']}"
        by_table.setdefault(key, []).append((r["column_name"], r["data_type"]))

    lines = [f"📊 **{len(by_table)} tables**\n"]
    for table, cols in by_table.items():
        lines.append(f"### `{table}`")
        for name, dtype in cols:
            lines.append(f"- `{name}` — {dtype}")
        lines.append("")
    return "\n".join(lines)


def _format_tool_calls(tool_calls_log: List[Dict[str, Any]]) -> str:
    if not tool_calls_log:
        return "_(no tool calls)_"
    parts = []
    for i, call in enumerate(tool_calls_log, 1):
        args_preview = json.dumps(call.get("args", {}), indent=2)[:400]
        parts.append(f"**{i}. `{call['tool']}`**\n```json\n{args_preview}\n```")
    return "\n\n".join(parts)


class AnalysisTab:
    def __init__(self, rag_processor: Any, session_manager: Any):
        self.agent = AnalysisAgent(rag_processor, session_manager)
        self.session_manager = session_manager

    async def _on_send(self, message, history):
        import traceback

        if not message or not message.strip():
            return "", history or [], "_(no tool calls)_"

        history = history or []
        session_id = "analysis-default"
        try:
            result = await self.agent.run(message, session_id)
            reply = result["response"]
            log_md = _format_tool_calls(result["tool_calls_log"])
            model_note = f"\n\n_model: `{result['model']}`_"
            reply = reply + model_note
        except Exception as e:
            tb = traceback.format_exc()
            print("=" * 80)
            print("AGENT ERROR TRACEBACK:")
            print(tb)
            print("=" * 80)
            reply = f"❌ Agent error: {e}"
            log_md = f"```\n{tb[-1500:]}\n```"

        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        return "", history, log_md

    def render(self) -> None:
        gr.Markdown("### 🔬 Cross-Source Analysis")
        gr.Markdown(
            "*LangGraph agent with Postgres MCP tools and document RAG. "
            "Ask questions that span the database, uploaded contracts, or both.*"
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 📊 Database Schema")
                schema_md = gr.Markdown(value="_Click **Load schema** to fetch from Postgres._")
                refresh_schema_btn = gr.Button("🔄 Load schema", variant="secondary")

            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="Analysis Chat",
                    height=500,
                    type="messages",
                )
                with gr.Row():
                    msg = gr.Textbox(
                        label="Ask a cross-source question",
                        placeholder="e.g. 'What tables are in the database?'",
                        lines=2,
                        scale=5,
                    )
                    send_btn = gr.Button("📤 Send", scale=1, variant="primary")

                with gr.Accordion("🔍 Agent reasoning (tool calls)", open=False):
                    reasoning_md = gr.Markdown(value="_(no tool calls yet)_")

        send_btn.click(
            fn=self._on_send,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot, reasoning_md],
        )
        msg.submit(
            fn=self._on_send,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot, reasoning_md],
        )
        refresh_schema_btn.click(fn=_render_schema_overview, outputs=[schema_md])
