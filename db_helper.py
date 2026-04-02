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
        return [{"image": p, "grade": g} for p, g in cursor.fetchall()]