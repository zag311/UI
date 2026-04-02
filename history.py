from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QWidget,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy, QAbstractScrollArea,
    QScrollArea, QGridLayout
)
import sqlite3
from create_tables import DB_PATH
from db_helper import get_batches, get_grade_counts, get_batch_images
import os
# -----------------------------
# UTILITY CLASSES
# -----------------------------
class ClickableActionButton(QWidget):
    def __init__(self, callback=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self.btn = QPushButton("View")
        self.btn.setObjectName("ActionBtn")
        self.btn.setFixedSize(96, 36)
        layout.addWidget(self.btn)

        if callback:
            self.btn.clicked.connect(callback)


class ScanCard(QFrame):
    def __init__(self, index, image_path, grade, parent=None):
        super().__init__(parent)
        self.setObjectName("ScanCard")

        print("IMAGE:", image_path, "EXISTS:", os.path.exists(image_path))
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel(f"Copra #{index}")
        title.setObjectName("ScanTitle")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        self.imageLabel = QLabel()
        self.imageLabel.setObjectName("ScanImage")
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setMinimumSize(220, 160)
        self.imageLabel.setMaximumHeight(180)

        if image_path:
            pix = QPixmap(image_path)
            if not pix.isNull():
                self.imageLabel.setPixmap(
                    pix.scaled(220, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self.imageLabel.setText("No scan image available")
        else:
            self.imageLabel.setText("No scan image available")

        root.addWidget(self.imageLabel)

        gradeLabel = QLabel(grade)
        gradeLabel.setObjectName("GradeBadge")
        gradeLabel.setAlignment(Qt.AlignCenter)
        root.addWidget(gradeLabel)


# -----------------------------
# BATCH DETAILS DIALOG
# -----------------------------
# -----------------------------
# BATCH DETAILS DIALOG (grouped by grade)
# -----------------------------
class BatchDetailsDialog(QDialog):
    def __init__(self, batch_number, images_data, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1120, 760)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 36, 36, 36)

        self.card = QFrame()
        self.card.setObjectName("DetailsCard")
        outer.addWidget(self.card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(44, 28, 16, 60))
        self.card.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(18)

        # Header
        top = QHBoxLayout()
        top.setSpacing(12)
        titleWrap = QVBoxLayout()
        titleWrap.setSpacing(4)

        title = QLabel("Batch Scan Details")
        title.setObjectName("DetailsTitle")
        batch_label = QLabel(batch_number)
        batch_label.setObjectName("DetailsBatch")
        titleWrap.addWidget(title)
        titleWrap.addWidget(batch_label)

        self.closeBtn = QPushButton("✕")
        self.closeBtn.setObjectName("CloseBtn")
        self.closeBtn.setFixedSize(46, 46)
        self.closeBtn.clicked.connect(self.close)

        top.addLayout(titleWrap, 1)
        top.addWidget(self.closeBtn, 0, Qt.AlignTop)
        root.addLayout(top)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scrollContent = QWidget()
        self.vbox = QVBoxLayout(scrollContent)
        self.vbox.setContentsMargins(4, 4, 4, 4)
        self.vbox.setSpacing(24)

        # Group images by grade first
        grades = ["G1", "G2", "G3", "Rejected"]
        images_by_grade = {g: [] for g in grades}

        for idx, item in enumerate(images_data, start=1):
            ui_grade = item.get("grade", "Unknown").replace("GRADE ", "G")
            if ui_grade not in grades:
                ui_grade = "Rejected"
            images_by_grade[ui_grade].append((idx, item.get("image", "")))

        # Now add each grade section AFTER grouping
        for grade in grades:
            group_images = images_by_grade.get(grade, [])
            if not group_images:
                continue

            grade_label = QLabel(ui_grade)
            grade_label.setObjectName("GradeGroupHeader")
            grade_label.setAlignment(Qt.AlignLeft)
            self.vbox.addWidget(grade_label)

            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(16)

            for i, (idx, img_path) in enumerate(group_images):
                card = ScanCard(idx, img_path, grade)
                row = i // 3
                col = i % 3
                grid.addWidget(card, row, col)

            self.vbox.addLayout(grid)

            # Inside the BatchDetailsDialog __init__ after adding headers
            self.setStyleSheet("""
            QLabel#GradeGroupHeader { 
                font-size:20px; 
                font-weight:900; 
                color:#6f3d0c; 
                margin:12px 0 6px 0; 
                padding:6px 12px;
                background-color: rgba(252, 243, 228, 0.5); 
                border-left: 4px solid #be8a2f; 
                border-radius:6px;
            }

            QLabel#GradeGroupHeader:contains("Rejected") {
                background-color: rgba(255, 205, 200, 0.6);  /* soft red/pink */
                border-left-color: #d9534f;                  /* red accent line */
            }
            """)

        # # Style
        # self.setStyleSheet(""" 
        # QDialog { background: rgba(36, 24, 14, 70); }
        # #DetailsCard { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #fbf7f2, stop:1 #f6efe7); border-radius:28px; border:1px solid #eadccc; }
        # #DetailsTitle { font-size:40px; font-weight:900; color:#6f3d0c; margin:2px 0 2px 0; letter-spacing:0.5px; }
        # #DetailsBatch { font-size:16px; font-weight:700; color:#9a6a2a; }
        # #CloseBtn { background:#f1e8de; color:#7a4a1d; border:none; border-radius:14px; font-size:18px; font-weight:900; }
        # #CloseBtn:hover { background:#e9ddd0; }
        # #ScanCard { background:white; border:1px solid #eadccc; border-radius:18px; }
        # #ScanTitle { font-size:16px; font-weight:800; color:#55331b; }
        # #ScanImage { background:#f7f1ea; border:1px dashed #d8c8b9; border-radius:14px; color:#aa8d70; font-size:14px; font-weight:700; padding:10px; }
        # #GradeBadge { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #9c6a22, stop:1 #be8a2f); color:white; border-radius:12px; padding:10px 12px; font-size:15px; font-weight:900; }
        # QScrollArea { background: transparent; }
        # """)


# -----------------------------
# HISTORY DIALOG
# -----------------------------
class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.resize(1240, 760)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 36, 36, 36)

        self.card = QFrame()
        self.card.setObjectName("Card")
        outer.addWidget(self.card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(44, 28, 16, 55))
        self.card.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(18)

        # Header
        title = QLabel("History")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        top = QHBoxLayout()
        top.setSpacing(14)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search batch number...")
        self.search.setObjectName("Search")
        self.search.setMinimumHeight(50)
        self.filterBtn = QPushButton("Filter")
        self.filterBtn.setObjectName("TopBtn")
        self.filterBtn.setFixedWidth(170)
        self.filterBtn.setMinimumHeight(50)
        self.closeBtn = QPushButton("✕")
        self.closeBtn.setObjectName("CloseBtn")
        self.closeBtn.setFixedSize(46, 46)
        top.addWidget(self.search, 1)
        top.addWidget(self.filterBtn, 0)
        top.addWidget(self.closeBtn, 0)
        root.addLayout(top)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setObjectName("HistoryTable")
        self.table.setHorizontalHeaderLabels([
            "Date", "Batch Number", "No. of Copra per Grade", "Operator", "View"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(True)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header = self.table.horizontalHeader()
        header.setFixedHeight(54)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        root.addWidget(self.table, 1)

        self.load_history_data()

        self.search.textChanged.connect(self.search_batch)
        self.filterBtn.clicked.connect(self.filter_today)
        self.closeBtn.clicked.connect(self.close)

        # Styles
        self.setStyleSheet("""
        QDialog { background: rgba(36, 24, 14, 70); }
        #Card { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #fbf7f2, stop:1 #f6efe7); border-radius:28px; border:1px solid #eadccc; }
        #Title { font-size:40px; font-weight:900; color:#6f3d0c; margin:2px 0 2px 0; letter-spacing:0.5px; }
        #Search { background:#ffffff; border:1.5px solid #dfd0c0; border-radius:14px; padding:0 18px; font-size:16px; font-weight:700; color:#55331b; }
        #Search:focus { border:1.5px solid #be8a2f; }
        #Search::placeholder { color:#b39474; }
        #TopBtn { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #9c6a22, stop:1 #be8a2f); color:white; border:none; border-radius:14px; font-size:16px; font-weight:800; padding:0 24px; }
        #TopBtn:hover { background:#a87428; }
        #TopBtn:pressed { background:#8a5d1f; }
        #CloseBtn { background:#f1e8de; color:#7a4a1d; border:none; border-radius:14px; font-size:18px; font-weight:900; }
        #CloseBtn:hover { background:#e9ddd0; }
        #HistoryTable { background:transparent; border:none; gridline-color:transparent; }
        QHeaderView::section { background:#f4eee7; color:#7a4a1d; font-weight:800; font-size:13px; border:none; border-bottom:1px solid #e3d5c6; padding:10px 8px; }
        QTableCornerButton::section { background:transparent; border:none; }
        QTableWidget::item { background-color:#ffffff; border-top:8px solid #f6efe7; border-bottom:8px solid #f6efe7; padding-left:12px; padding-right:12px; }
        QScrollBar:horizontal { height:0px; }
        QScrollBar:vertical { background:transparent; width:10px; margin:4px 0 4px 0; }
        QScrollBar::handle:vertical { background:#d8c3a8; border-radius:5px; min-height:24px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
        #ActionBtn { background:#f6efe7; border:1px solid #e2d2c2; border-radius:10px; font-size:13px; font-weight:800; color:#7a4a1d; padding:0 14px; }
        #ActionBtn:hover { background:#efe4d7; }
        #ActionBtn:pressed { background:#e7d8c6; }
        #ScanCard { background:white; border:1px solid #eadccc; border-radius:18px; }
        #ScanTitle { font-size:16px; font-weight:800; color:#55331b; }
        #ScanImage { background:#f7f1ea; border:1px dashed #d8c8b9; border-radius:14px; color:#aa8d70; font-size:14px; font-weight:700; padding:10px; }
        #GradeBadge { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #9c6a22, stop:1 #be8a2f); color:white; border-radius:12px; padding:10px 12px; font-size:15px; font-weight:900; }
        QScrollArea { background: transparent; }
        """)

    def load_history_data(self):
        self.table.setRowCount(0)  # 🔥 clear table first

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT b.batch_id, b.created_at, o.name
                FROM Batch b
                JOIN Operator o ON b.operator_id = o.operator_id
                ORDER BY b.created_at DESC
            """)
            batches = get_batches()

            for r, (batch_id, created_at, operator_name) in enumerate(batches):
                grade_counts = get_grade_counts(batch_id)

# Convert DB grades → UI format
                mapped_counts = {}
                for grade, count in grade_counts.items():
                    ui_grade = grade.replace("GRADE ", "G")
                    mapped_counts[ui_grade] = count

                ordered_grades = ["G1", "G2", "G3"]

                amount_str = ", ".join(
                    f"{g}: {mapped_counts.get(g, 0)}" for g in ordered_grades
                )

                self.table.insertRow(r)

                self.table.setItem(r, 0, QTableWidgetItem(created_at.split(" ")[0]))
                self.table.setItem(r, 1, QTableWidgetItem(f"BCH-{batch_id:03}"))
                self.table.setItem(r, 2, QTableWidgetItem(amount_str))
                self.table.setItem(r, 3, QTableWidgetItem(operator_name))

                for c in [0, 2, 3]:
                    self.table.item(r, c).setTextAlignment(Qt.AlignCenter)

                widget = ClickableActionButton(
                    callback=lambda _, bid=batch_id: self.open_batch_details(bid)
                )
                self.table.setCellWidget(r, 4, widget)

    def open_batch_details(self, batch_id):
        images = get_batch_images(batch_id)
        dialog = BatchDetailsDialog(f"BCH-{batch_id:03}", images, self)
        dialog.exec_()

    def search_batch(self):
        text = self.search.text().strip().lower()
        for r in range(self.table.rowCount()):
            batch_item = self.table.item(r, 1)
            self.table.setRowHidden(r, text not in batch_item.text().lower())

    def filter_today(self):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        for r in range(self.table.rowCount()):
            date_item = self.table.item(r, 0)
            self.table.setRowHidden(r, date_item.text() != today)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = HistoryDialog()
    w.show()
    sys.exit(app.exec_())