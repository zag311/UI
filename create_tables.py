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
        
        # Batch table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Batch (
            batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operator_id) REFERENCES Operator(operator_id)
        )
        ''')
        
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
def start_new_batch(operator_id=1):
    """
    Creates a new batch and corresponding folder for images & receipts
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Batch (operator_id) VALUES (?)", (operator_id,))
        batch_id = cursor.lastrowid
        conn.commit()
    
    batch_image_folder = ensure_folder(os.path.join(IMAGES_ROOT, f"batch_{batch_id}"))
    batch_receipt_folder = ensure_folder(os.path.join(RECEIPTS_ROOT, f"batch_{batch_id}"))
    
    return batch_id, batch_image_folder, batch_receipt_folder

# -----------------------------
# IMAGE LOGIC
# -----------------------------
def save_image(batch_id, image_path, grade='GRADE 1'):
    """
    Records an already-saved image into the database
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ImageData (batch_id, image_path, grade) VALUES (?, ?, ?)",
            (batch_id, image_path, grade)
        )
        conn.commit()

    return image_path
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

# -----------------------------
# EXAMPLE USAGE
# -----------------------------
if __name__ == "__main__":
    init_db()
    
    batch_id, img_folder, receipt_folder = start_new_batch(operator_id=1)
    print(f"Batch {batch_id} created. Image folder: {img_folder}, Receipt folder: {receipt_folder}")
    
    # Example: save_image(batch_id, image_bytes, grade='GRADE 1')
    # Example: create_receipt(batch_id, "receipt_001.pdf")