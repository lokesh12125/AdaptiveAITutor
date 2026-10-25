"""IBM Project CodeNet dataset importer and loader script.

Loads problem metadata, maps problem challenges to core concepts (If Else, Loops, Functions, Arrays, Strings, Recursion, OOP),
and seeds the authoritative SQLite tutoring database.
"""
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "backend" / "tutor.db"
CATALOG_PATH = BASE_DIR / "dataset" / "metadata" / "codenet_catalog.json"


def load_codenet_dataset() -> list[dict]:
    """Import IBM CodeNet metadata from JSON catalog file or return fallback list."""
    if CATALOG_PATH.exists():
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse CodeNet catalog JSON: {e}")
    return []


def sync_codenet_to_db():
    """Sync mapped CodeNet problems into the SQLite database."""
    problems = load_codenet_dataset()
    if not problems:
        print("No CodeNet dataset problems found to sync.")
        return 0

    conn = sqlite3.connect(DB_PATH)
    count = 0
    try:
        with conn:
            for p in problems:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO problems
                    (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                    """,
                    (
                        p["id"],
                        p["title"],
                        p["description"],
                        p["difficulty"],
                        p["topic"],
                        p["starter_code"],
                        p["expected_behavior"],
                        p.get("concept_id", p["topic"].lower().replace(" ", "-")),
                        json.dumps(p.get("test_cases", [])),
                        p.get("source", "IBM-Project-CodeNet"),
                    ),
                )
                count += 1
        print(f"Successfully synced {count} CodeNet problems to database.")
    except Exception as e:
        print(f"Error syncing CodeNet dataset to DB: {e}")
    finally:
        conn.close()

    return count


if __name__ == "__main__":
    sync_codenet_to_db()
