# Dependency Audit Report — Render Deployment

This audit explains the root cause of the `MySQL-python` build failure on Render and validates database dependencies.

---

## 1. Root Cause Analysis

### The Error
```text
ModuleNotFoundError: No module named 'ConfigParser'
ERROR: Failed to build 'MySQL-python'
```

### Why Did This Occur?
1. **Unpinned Python Version:** Render defaults to the latest Python version (Python 3.12+ or 3.13+) unless configured otherwise.
2. **Pip Backtracking:** In modern Python versions, some unpinned library combinations in `requirements.txt` cause the `pip` resolver to fail to find a matching set of dependencies.
3. **Legacy Dependency Selection:** When `pip` backtracks, it begins trying older and older versions of packages (such as legacy versions of `SQLAlchemy` or other utility packages).
4. **Python 2 Package Fallback:** Some of these old legacy versions list `MySQL-python` (the Python 2 database adapter) as a hard dependency.
5. **ConfigParser Failure:** When pip tries to compile `MySQL-python` on Python 3, it fails immediately because `ConfigParser` (a Python 2 standard library) was renamed to `configparser` in Python 3.

---

## 2. MySQL Usage Verification

We performed a comprehensive search across the codebase:
- **`requirements.txt` & `streamlit_requirements.txt`:** No direct references to `mysql`, `MySQL-python`, or database drivers other than `chromadb`.
- **Source Code Imports (`*.py`):** Zero imports of `MySQLdb`, `mysql.connector`, or similar databases.
- **Database Architecture:** The system uses `ChromaDB` (local client backed by SQLite) for vector search. No relational database connections are configured or required.
- **Environment Variables:** No database URLs or MySQL configurations exist.

**Conclusion:** MySQL is **NOT** used or required by this project. The dependency is purely an artifact of pip backtracking.

---

## 3. Recommended Fixes

1. **Pin python-3.11.9:** Create a `runtime.txt` file to force Render to build with Python 3.11.9, which is fully compatible with our RAG packages (`chromadb`, `sentence-transformers`, `torch`, `langchain`).
2. **Clean dependencies:** Ensure `requirements.txt` lists clean, modern Python 3 packages without conflicting version constraints.
