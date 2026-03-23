#!/usr/bin/env python3
"""Initialize growth system database tables and check existing state."""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "memory.db"

def init_tables():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    c.executescript("""
        CREATE TABLE IF NOT EXISTS proven_nodes (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            type TEXT NOT NULL,
            source TEXT,
            collision_type TEXT,
            confidence REAL DEFAULT 0.8,
            domain TEXT,
            tags TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_by TEXT,
            verification_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            file_path TEXT,
            description TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            forged_by TEXT,
            source_node_id TEXT,
            meta_json TEXT,
            validation_score INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (source_node_id) REFERENCES proven_nodes(id)
        );

        CREATE TABLE IF NOT EXISTS skill_dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id TEXT NOT NULL,
            depends_on TEXT NOT NULL,
            dependency_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (skill_id) REFERENCES skills(id),
            FOREIGN KEY (depends_on) REFERENCES skills(id)
        );

        CREATE TABLE IF NOT EXISTS growth_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_number INTEGER NOT NULL,
            phase TEXT NOT NULL,
            event_type TEXT,
            entity_id TEXT,
            tokens_used INTEGER DEFAULT 0,
            elapsed_seconds REAL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS collision_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collision_type TEXT NOT NULL,
            input_nodes TEXT,
            output_nodes TEXT,
            glm5_prompt TEXT,
            glm5_response TEXT,
            tokens_used INTEGER,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pcm (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            concept TEXT NOT NULL,
            domain TEXT,
            confidence REAL DEFAULT 0.8,
            references_json TEXT,
            source_node_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_node_id) REFERENCES proven_nodes(id)
        );
    """)
    conn.commit()
    
    # Check existing state
    print(f"Database: {DB_PATH}")
    print(f"Database exists: {DB_PATH.exists()}")
    print(f"Database size: {DB_PATH.stat().st_size:,} bytes\n")
    
    tables = ["proven_nodes", "skills", "skill_dependencies", "growth_log", "collision_history", "pcm"]
    for t in tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM {t}")
            count = c.fetchone()[0]
            print(f"  {t}: {count} rows")
        except Exception as e:
            print(f"  {t}: ERROR - {e}")
    
    # Check existing skills files
    skills_dir = Path(__file__).parent.parent / "workspace" / "skills"
    skill_files = list(skills_dir.glob("*.meta.json"))
    print(f"\nExisting skill .meta.json files: {len(skill_files)}")
    for f in skill_files:
        print(f"  - {f.name}")
    
    # Check existing lattice tables
    print("\nAll tables in database:")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for row in c.fetchall():
        print(f"  - {row[0]}")
    
    conn.close()
    print("\n✅ All 6 growth tables initialized successfully.")

if __name__ == "__main__":
    init_tables()
