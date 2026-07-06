# Agent Rules for AHP Master Project

To prevent hallucinations, incorrect imports, and broken routing logic in this Streamlit AHP Master Portal project, you (Gemini/Antigravity) MUST strictly adhere to the following rules during every step of the conversation:

## 1. Mandatory Context Synchronization
- **Read Project Context First**: Before executing any code modifications, creating new scripts, or running command-line tasks, you MUST read the root [PROJECT_CONTEXT.md](file:///f:/app/4.%20AHP%EB%A7%88%EC%8A%A4%ED%84%B0/PROJECT_CONTEXT.md) using the `view_file` tool to understand the application structure and module responsibilities.
- **Check Existing Definitions**: Never assume a function, class, or module exists. If you need to import or call a function from `ahp_utils_v3.py`, `survey_manager.py`, `survey_manager_v3.py`, or `standard_app.py`, you MUST use `grep_search` or `view_file` to confirm its signature and exact spelling first.

## 2. Coding and Modification Principles
- **No Large File Rewrites**: `standard_app.py` and `yeta_app.py` are very large (several hundred KB). NEVER attempt to overwrite them entirely. Use `replace_file_content` or `multi_replace_file_content` targeting precise line ranges to make surgical modifications.
- **Keep Streamlit Routing Intact**:
  - `app.py` acts as the router using the `mode` query parameter. Do not break this entrypoint logic.
  - Maintain the existing query parameter resolving and language detection rules.
- **Database Safety**:
  - Always verify connection closing for SQLite database operations.
  - Keep schema migrations backward-compatible. Do not drop existing tables or columns unless explicitly requested.

## 3. Command Execution Rule
- Before executing terminal/PowerShell commands:
  - Verify that the target paths are absolute and within the workspace.
  - Do not use wildcard `*` permissions when asking for tool permissions. Request narrow, specific paths.
