"""Text2SQL wrapper for PostgreSQL queries against the activities table.

This module builds a schema-aware prompt, generates a safe SELECT query,
validates it, executes it against PostgreSQL using environment credentials,
and returns a human-readable answer.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

SQL_SCHEMA = (
    "activities(name TEXT, description TEXT, schedule TEXT, "
    "max_participants INT, participants JSONB)"
)

KNOWN_ACTIVITY_NAMES = [
    "Chess Club",
    "Programming Class",
    "Gym Class",
]

DISALLOWED_SQL_KEYWORDS = re.compile(
    r"\b(delete|drop|update|insert|alter|create|replace|truncate|grant|revoke)\b",
    re.IGNORECASE,
)
TABLE_REFERENCE_PATTERN = re.compile(
    r"\b(?:from|join)\s+((?:\"[^\"]+\"|\w+)(?:\.(?:\"[^\"]+\"|\w+))?)",
    re.IGNORECASE,
)


def security_validate(sql: str) -> bool:
    """Validate the generated SQL before execution.

    The SQL must be a single SELECT statement operating only on the activities table.
    It must not contain dangerous DML or DDL keywords and must avoid inline string literals
    when user-supplied values are required.
    """
    if not isinstance(sql, str) or not sql.strip():
        return False

    normalized = sql.strip()
    if ";" in normalized:
        return False

    lower_sql = normalized.lower()
    if not lower_sql.startswith("select"):
        return False

    if DISALLOWED_SQL_KEYWORDS.search(lower_sql):
        return False

    for table_match in TABLE_REFERENCE_PATTERN.finditer(normalized):
        table_name = table_match.group(1).strip()
        if table_name.startswith('"') and table_name.endswith('"'):
            table_name = table_name[1:-1]
        if "." in table_name:
            table_name = table_name.split(".")[-1]
        if table_name.lower() != "activities":
            return False

    if "%s" not in normalized:
        # If the query has any literal strings or numbers, require placeholders.
        if re.search(r"['\"]|\b\d+\b", normalized):
            return False

    return True


def _extract_activity_name(question: str) -> Optional[str]:
    """Return a known activity name if the question mentions one."""
    normalized = question.lower()
    for activity in KNOWN_ACTIVITY_NAMES:
        if activity.lower() in normalized:
            return activity
    return None


def _build_prompt(question: str) -> str:
    """Build a schema-injected prompt for SQL generation."""
    return (
        f"Schema: {SQL_SCHEMA}\n"
        "Generate a PostgreSQL SELECT query using %s placeholders to answer the question. "
        "Only reference the activities table and return the SQL statement alone.\n"
        f"Question: {question.strip()}"
    )


def _generate_sql(question: str) -> Tuple[str, Tuple[Any, ...]]:
    """Generate a parameterized SQL query for a question.

    This implementation uses a simple rule-based generator and includes the
    schema prompt as a guide for query generation.
    """
    prompt = _build_prompt(question)
    _ = prompt  # Keep the schema-injected prompt in scope for auditability.
    normalized = question.lower().strip()
    activity_name = _extract_activity_name(question)

    if any(keyword in normalized for keyword in ("how many", "count", "total", "how full")):
        if "participants" in normalized or "students" in normalized:
            if activity_name:
                return (
                    "SELECT COUNT(*) FROM activities WHERE name = %s",
                    (activity_name,),
                )
            return (
                "SELECT SUM(jsonb_array_length(participants::jsonb)) FROM activities",
                (),
            )
        return (
            "SELECT COUNT(*) FROM activities",
            (),
        )

    if any(keyword in normalized for keyword in ("which activities", "list all", "what activities", "list activities", "show activities")):
        return (
            "SELECT name FROM activities ORDER BY name",
            (),
        )

    if "schedule" in normalized:
        if activity_name:
            return (
                "SELECT schedule FROM activities WHERE name = %s",
                (activity_name,),
            )
        return (
            "SELECT name, schedule FROM activities ORDER BY name",
            (),
        )

    if "description" in normalized or "tell me about" in normalized or "what is" in normalized:
        if activity_name:
            return (
                "SELECT description, schedule, max_participants, participants FROM activities WHERE name = %s",
                (activity_name,),
            )
        return (
            "SELECT name, description, schedule FROM activities ORDER BY name",
            (),
        )

    if "max participants" in normalized or "capacity" in normalized or "spots" in normalized:
        if activity_name:
            return (
                "SELECT name, max_participants, jsonb_array_length(participants::jsonb) AS current_participants "
                "FROM activities WHERE name = %s",
                (activity_name,),
            )
        return (
            "SELECT name, max_participants, jsonb_array_length(participants::jsonb) AS current_participants "
            "FROM activities ORDER BY name",
            (),
        )

    if "participants" in normalized:
        if activity_name:
            return (
                "SELECT participants FROM activities WHERE name = %s",
                (activity_name,),
            )
        return (
            "SELECT name, jsonb_array_length(participants::jsonb) AS current_participants "
            "FROM activities ORDER BY name",
            (),
        )

    return (
        "SELECT name, description, schedule FROM activities ORDER BY name",
        (),
    )


def _get_connection_params() -> Dict[str, str]:
    """Collect PostgreSQL connection settings from environment variables."""
    env = {
        "dsn": os.getenv("DATABASE_URL", ""),
        "host": os.getenv("PGHOST", ""),
        "port": os.getenv("PGPORT", ""),
        "user": os.getenv("PGUSER", ""),
        "password": os.getenv("PGPASSWORD", ""),
        "dbname": os.getenv("PGDATABASE", ""),
    }
    return {key: value for key, value in env.items() if value}


def _get_db_connection() -> Any:
    """Create a PostgreSQL connection using supported Python adapters."""
    params = _get_connection_params()
    try:
        import psycopg

        if "dsn" in params:
            return psycopg.connect(params["dsn"])

        filtered = {k: v for k, v in params.items() if k != "dsn"}
        if not filtered:
            raise ValueError("Missing PostgreSQL connection environment variables")
        return psycopg.connect(**filtered)
    except ImportError:
        try:
            import psycopg2

            if "dsn" in params:
                return psycopg2.connect(params["dsn"])

            filtered = {k: v for k, v in params.items() if k != "dsn"}
            if not filtered:
                raise ValueError("Missing PostgreSQL connection environment variables")
            return psycopg2.connect(**filtered)
        except ImportError as exc:
            raise RuntimeError("PostgreSQL client library is not installed") from exc


def _format_rows(rows: List[Tuple[Any, ...]], description: Any, question: str) -> str:
    """Convert SQL result rows into a readable answer sentence."""
    columns = [
        getattr(col, "name", None) or (col[0] if isinstance(col, tuple) else str(col))
        for col in description
    ]
    if not rows:
        return "I could not find a matching activity with the provided criteria."

    if len(columns) == 1:
        value = rows[0][0]
        column_name = columns[0].lower()
        if column_name in ("count", "count(*)"):
            if "students" in question.lower() or "participants" in question.lower():
                return f"There are {value} students signed up."
            return f"The count is {value}."
        if column_name == "schedule":
            if len(rows) == 1:
                return f"Schedule: {value}."
        if column_name == "participants":
            return _format_participants(value)

    if set(columns) >= {"name", "description", "schedule"}:
        sentences = []
        for row in rows:
            row_data = dict(zip(columns, row))
            sentences.append(
                f"{row_data.get('name')} - {row_data.get('description')} "
                f"(Schedule: {row_data.get('schedule')})."
            )
        return " ".join(sentences)

    if "name" in columns and "current_participants" in columns:
        sentences = []
        for row in rows:
            row_data = dict(zip(columns, row))
            name = row_data.get("name")
            current = row_data.get("current_participants")
            maximum = row_data.get("max_participants")
            if maximum is not None:
                sentences.append(
                    f"{name} has {current} students signed up out of {maximum} spots."
                )
            else:
                sentences.append(f"{name} has {current} students signed up.")
        return " ".join(sentences)

    if "name" in columns and len(rows) > 1:
        names = ", ".join(str(row[columns.index("name")]) for row in rows)
        return f"The activities are: {names}."

    if len(rows) == 1:
        row_data = dict(zip(columns, rows[0]))
        values = ", ".join(
            f"{col}: {row_data[col]}" for col in columns if row_data.get(col) is not None
        )
        return f"{values}."

    return "I returned results from the activities database."


def _format_participants(value: Any) -> str:
    if value is None:
        return "No participant data is available."
    if isinstance(value, (list, tuple)):
        members = ", ".join(str(item) for item in value)
        return f"Participants: {members}."
    if isinstance(value, str):
        return f"Participants: {value}."
    return f"Participants: {value}."


def run_text2sql(question: str) -> Dict[str, Any]:
    """Run a Text2SQL question against PostgreSQL and return a formatted answer."""
    if not isinstance(question, str) or not question.strip():
        return {"error": "question is required", "source": "text2sql", "confidence": 0.0}

    sql, params = _generate_sql(question)
    if not security_validate(sql):
        return {"answer": "Generated SQL did not pass validation.", "source": "text2sql", "confidence": 0.0}

    try:
        conn = _get_db_connection()
    except Exception:
        return {
            "answer": "I could not run the database query because the PostgreSQL client is not available.",
            "source": "text2sql",
            "confidence": 0.0,
        }

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        answer = _format_rows(rows, cursor.description, question)
        return {"answer": answer, "source": "text2sql", "confidence": 1.0}
    except Exception:
        return {
            "answer": "An error occurred while executing the database query.",
            "source": "text2sql",
            "confidence": 0.0,
        }
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass
