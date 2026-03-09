"""
Shared blocklists for code/expression validation.

Both ``safe_expression`` (single-expression DSL) and ``safe_custom_code``
(multi-statement custom chart code) reuse these sets so that dangerous
attribute names are defined in exactly one place.
"""

# ── Blocked pandas / numpy attribute names ────────────────────────
# Callable or attribute names that must never be accessed in user code.
# This is the *common* set shared by both validators.

BLOCKED_PANDAS_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "agg",
        "aggregate",
        "apply",
        "eval",
        "exec",
        "map",
        "pipe",
        "query",
        # ── Read I/O ──
        "read_csv",
        "read_excel",
        "read_feather",
        "read_fwf",
        "read_hdf",
        "read_html",
        "read_json",
        "read_orc",
        "read_parquet",
        "read_pickle",
        "read_sql",
        "read_sql_query",
        "read_sql_table",
        "read_table",
        "read_xml",
        # ── Write I/O ──
        "to_clipboard",
        "to_csv",
        "to_excel",
        "to_feather",
        "to_hdf",
        "to_html",
        "to_json",
        "to_latex",
        "to_markdown",
        "to_parquet",
        "to_pickle",
        "to_sql",
        "to_string",
        "to_xml",
    }
)

# Additional system-level attributes blocked in custom chart code
# (multi-statement exec context) but NOT in simple expression eval.
BLOCKED_SYSTEM_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "builtins",
        "compile",
        "ctypes",
        "delattr",
        "dir",
        "getattr",
        "globals",
        "import_module",
        "importlib",
        "input",
        "io",
        "locals",
        "open",
        "os",
        "pathlib",
        "setattr",
        "shutil",
        "socket",
        "subprocess",
        "sys",
        "urllib",
        "util",
        "vars",
    }
)
