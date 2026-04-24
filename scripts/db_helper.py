# db_helper.py
import sqlite3
from create_tables import DB_PATH

def get_batches():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.batch_id, b.created_at, o.name
            FROM Batch b
            JOIN Operator o ON b.operator_id = o.operator_id
            ORDER BY b.created_at DESC
        """)
        return cursor.fetchall()


def get_grade_counts(batch_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT grade, COUNT(*)
            FROM ImageData
            WHERE batch_id = ?
            GROUP BY grade
        """, (batch_id,))
        return dict(cursor.fetchall())


def get_batch_images(batch_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT image_path, grade
            FROM ImageData
            WHERE batch_id = ?
            ORDER BY captured_at ASC
        """, (batch_id,))
        # Use key "image_path" so the UI finds it
        return [{"image_path": p, "grade": g} for p, g in cursor.fetchall()]

def ensure_operator_exists(operator_name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Operator (name)
            SELECT ?
            WHERE NOT EXISTS (
                SELECT 1 FROM Operator WHERE name = ?
            )
        """, (operator_name, operator_name))

        conn.commit()

def set_current_operator(operator_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM AppState WHERE key='current_operator'")
        cur.execute("INSERT INTO AppState (key, value) VALUES ('current_operator', ?)", (operator_id,))
        conn.commit()

def get_operator_id(name):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("SELECT operator_id FROM Operator WHERE name = ?", (name,))
        row = cur.fetchone()

        if row:
            return row[0]

        cur.execute("INSERT INTO Operator (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid

def get_operator_name(operator_id):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM Operator
        WHERE operator_id = ?
    """, (operator_id,))

    row = cur.fetchone()
    conn.close()

    return row[0] if row else "Default Operator"

def get_last_operator():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM Operator
            ORDER BY operator_id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        return row[0] if row else "Default Operator"    

def update_batch_operator(batch_id, operator_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Batch
        SET operator_id = ?
        WHERE batch_id = ? AND status = 'ACTIVE'
    """, (operator_id, batch_id))

    conn.commit()
    conn.close()

def get_active_operator():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS SystemState (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active_operator_id INTEGER
        )
    """)

    # ensure default row exists
    cur.execute("""
        INSERT OR IGNORE INTO SystemState (id, active_operator_id)
        VALUES (1, 1)
    """)

    cur.execute("SELECT active_operator_id FROM SystemState WHERE id = 1")
    row = cur.fetchone()

    conn.close()
    return row[0] if row else 1

def update_operator(operator_id, new_name):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # update identity
    cur.execute("""
        UPDATE Operator
        SET name = ?
        WHERE operator_id = ?
    """, (new_name, operator_id))

    conn.commit()
    conn.close()

def set_active_operator(operator_id):
    import sqlite3
    from create_tables import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS SystemState (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active_operator_id INTEGER
        )
    """)

    cur.execute("""
        INSERT INTO SystemState (id, active_operator_id)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET active_operator_id = excluded.active_operator_id
    """, (operator_id,))

    conn.commit()
    conn.close()