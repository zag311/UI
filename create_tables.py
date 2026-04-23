import os
import sqlite3
from datetime import datetime

# -----------------------------
# PATH CONFIGURATION
# -----------------------------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))  # folder where this script lives
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)              # project root
DB_PATH = os.path.join(PROJECT_ROOT, "database", "copra_data.db")
IMAGES_ROOT = os.path.join(PROJECT_ROOT, "images")
RECEIPTS_ROOT = os.path.join(PROJECT_ROOT, "receipts")

# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------
def ensure_folder(path):
    """Create folder if it doesn’t exist."""
    os.makedirs(path, exist_ok=True)
    return path

# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------
def init_db():
    # ensure folders exist
    ensure_folder(os.path.dirname(DB_PATH))
    ensure_folder(IMAGES_ROOT)
    ensure_folder(RECEIPTS_ROOT)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Operator table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Operator (
            operator_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
        ''')

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AppState (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Batch table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Batch (
            batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operator_id) REFERENCES Operator(operator_id)
        )
        ''')
        
        cursor.execute("""
            PRAGMA table_info(Batch)
        """)
        columns = [col[1] for col in cursor.fetchall()]

        if "status" not in columns:
            try:
                cursor.execute("ALTER TABLE Batch ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
            except sqlite3.OperationalError:
                pass

        # ImageData table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ImageData (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            grade TEXT CHECK(grade IN ('GRADE 1', 'GRADE 2', 'GRADE 3', 'REJECT')) DEFAULT 'REJECT',
            captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
        )
        ''')
        
        try:
            cursor.execute("ALTER TABLE ImageData ADD COLUMN moisture REAL")
        except sqlite3.OperationalError:
            pass  # already exists, ignore

        try:
            cursor.execute("ALTER TABLE ImageData ADD COLUMN confidence REAL")
        except sqlite3.OperationalError:
            pass

        # Receipt table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Receipt (
            receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER UNIQUE NOT NULL,
            receipt_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
        )
        ''')
        
        # Ensure at least one default operator exists
        cursor.execute("SELECT COUNT(*) FROM Operator")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO Operator (name) VALUES (?)", ("Default Operator",))
        
        conn.commit()

# -----------------------------
# BATCH LOGIC
# -----------------------------
def create_new_batch(operator_id=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Batch (operator_id, status, created_at)
        VALUES (?, 'ACTIVE', datetime('now'))
    """, (operator_id,))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    print("[BATCH] Created new batch:", new_id)
    return new_id

# -----------------------------
# IMAGE LOGIC
# -----------------------------
def save_image(batch_id, image_path, grade, moisture, confidence):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ImageData (batch_id, image_path, grade, moisture, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (batch_id, image_path, grade, moisture, confidence))

    conn.commit()
    conn.close()
# -----------------------------
# RECEIPT LOGIC
# -----------------------------
def create_receipt(batch_id, receipt_filename):
    """
    Creates a receipt entry in DB and saves path
    """
    batch_receipt_folder = ensure_folder(os.path.join(RECEIPTS_ROOT, f"batch_{batch_id}"))
    receipt_path = os.path.join(batch_receipt_folder, receipt_filename)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Receipt (batch_id, receipt_path) VALUES (?, ?)",
            (batch_id, receipt_path)
        )
        conn.commit()
    
    return receipt_path

def get_active_batch(operator_id=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT batch_id
        FROM Batch
        WHERE status = 'ACTIVE'
        ORDER BY batch_id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row:
        print("[BATCH] Reusing active batch:", row[0])
        return row[0]

    return create_new_batch(operator_id)

def close_batch(batch_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Batch
        SET status = 'CLOSED'
        WHERE batch_id = ?
    """, (batch_id,))

    conn.commit()
    conn.close()

    print("[BATCH] Closed batch:", batch_id)

def set_active_operator(operator_id):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO SystemState (id, active_operator_id)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET active_operator_id = excluded.active_operator_id
    """, (operator_id,))

    conn.commit()
    conn.close()

# -----------------------------
# EXAMPLE USAGE
# -----------------------------
