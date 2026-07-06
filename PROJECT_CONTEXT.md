# Project Context & Technical Specification (PROJECT_CONTEXT.md)

This document serves as the **Single Source of Truth (SSOT)** for this repository. It defines the application architecture, tech stack, codebase structure, and strict guidelines for AI agents to prevent hallucinations and errors.

---

## 1. Project Overview
**AHP Master Portal** is a web application designed for creating, distributing, and analyzing **Analytic Hierarchy Process (AHP)** surveys. It automates AHP calculations (Consistency Ratio, weights, ANOVA, Fuzzy AHP) and visualizes results, as well as providing downloadable Excel reports.

- **Frontend/Backend Framework**: Streamlit
- **Google Integration**: Google Sheets API (via `gspread` and `google-api-python-client`)
- **Core Libraries**: pandas, numpy, scipy, statsmodels, XlsxWriter, sqlite3

---

## 2. Core Architecture & File Mapping

### A. Entrypoint & Routing
*   **[app.py](file:///f:/app/4.%20AHP%EB%A7%88%EC%8A%A4%ED%84%B0/app.py)**: The main entry point of the Streamlit application.
    *   It reads the `mode` parameter from the URL query params (`st.query_params.get("mode")`).
    *   If `mode == "yeta"`, it imports and runs `yeta_app.py` (Yeta analysis mode).
    *   Otherwise, it routes to `standard_app.py`.
    *   It also runs initialization logic for language settings (`st.session_state.lang`) and database migrations.

### B. Portal Applications
*   **[standard_app.py](file:///f:/app/4.%20AHP%EB%A7%88%EC%8A%A4%ED%84%B0/standard_app.py)** (Crucial: ~600KB):
    *   Contains the complete dashboard interface for users to build surveys, view AHP analysis reports, and manage settings.
    *   Handles complex UI states via Streamlit's `st.session_state`.
*   **[yeta_app.py](file:///f:/app/4.%20AHP%EB%A7%88%EC%8A%A4%ED%84%B0/yeta_app.py)**:
    *   Dedicated application for 예타 (Pre-feasibility study) analysis workflows.

### C. Survey & Sheet Integration
*   **[survey_manager.py](file:///f:/app/4.%20AHP%EB%A7%88%EC%8A%A4%ED%84%B0/survey_manager.py)**:
    *   Provides Google Sheets OAuth flow, sheet synchronization, and metadata fetching.
    *   Manages 2-tier AHP sheet generation and response logging.
    *   Key functions: `get_survey_gspread_client()`, `run_gspread_with_retry()`, `save_response_to_sheet()`.
*   **[survey_manager_v3.py](file:///f:/app/4.%20AHP%EB%A7%88%EC%8A%A4%ED%84%B0/survey_manager_v3.py)**:
    *   V3 survey sheet engine specifically optimized for **3-Tier AHP model templates** (Category -> Mid -> Sub-category headers).
    *   Key functions: `create_survey_sheet_v3()`.

### D. Computational & Report Utilities
*   **[ahp_utils_v3.py](file:///f:/app/4.%20AHP%EB%A7%88%EC%8A%A4%ED%84%B0/ahp_utils_v3.py)**:
    *   Handles all core mathematical implementations: Geometric mean weights, consistency index, random index (RI) lookup.
    *   Calculates statistical tests like ANOVA and post-hoc tests.
    *   Generates detailed multi-sheet Excel reports with custom styles using `XlsxWriter`.
    *   Key functions: `calculate_weights()`, `calculate_consistency()`, `run_ahp_analysis_v3()`, `write_custom_ahp_table_v3()`.

---

## 3. Database Schema Information

### A. users.db
Used for user credentials, roles, and plan limits.
*   **`users` Table**:
    *   `id` (TEXT, PRIMARY KEY): Username or email.
    *   `role` (TEXT): admin, user, etc.
    *   `pw` (TEXT): Password hash.
    *   `signup_date` (TEXT), `expiry_date` (TEXT).
    *   `survey_count` (INTEGER): Total created survey count.
    *   `last_survey_link` (TEXT), `plan_type` (TEXT).
    *   `thesis_title` (TEXT), `university` (TEXT), `customer_type` (TEXT).

### B. Other Databases
*   `ahp_surveys.db` & `survey_data.db`: Contain application-specific survey mappings and offline logs.

---

## 4. Hallucination Prevention Checklist (MUST READ)

1.  **Scratch Scripts vs Production Code**:
    *   Files prefixed with `scratch_` (e.g., `scratch_patch_process.py`, `scratch_tab1_v3.py`) are temporary helper scripts or testing files.
    *   **NEVER** modify or use scratch scripts as target production files. All permanent changes must go into the primary codebase (`standard_app.py`, `survey_manager.py`, etc.).
2.  **Handling Huge Files**:
    *   `standard_app.py` is extremely large. Overwriting it will fail or cause memory truncation. Use specific line targets in `replace_file_content`.
3.  **API Function Signatures**:
    *   When utilizing functions in `survey_manager.py` or `ahp_utils_v3.py`, do not guess their parameters. Always view their definition header line using `view_file` or search via `grep_search` beforehand.
4.  **Localization / Translation**:
    *   UI components use the `_(ko_text, en_text)` wrapper function for multilingual support (Korean vs English). Always match this pattern when modifying user-facing text.
