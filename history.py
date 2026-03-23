from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget
)


GOLD = "#b8832a"
TEXT_GOLD = "#b8832a"
TITLE_BROWN = "#6a3600"
BLACK = "#000000"
TEXT_BLACK = "#000000"


class ActionButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn = QPushButton("▾ View")
        self.btn.setObjectName("ActionBtn")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setFixedSize(130, 44)

        layout.addWidget(self.btn)
        layout.setAlignment(Qt.AlignCenter)


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(1400, 850)
        self.setObjectName("HistoryDialog")
        self.filter_is_on = False

        root = QVBoxLayout(self)

        title = QLabel("History")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        top = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search batch number...")
        self.search.setObjectName("Search")

        self.filterBtn = QPushButton("Filter")
        self.filterBtn.setObjectName("TopBtn")

        self.exportBtn = QPushButton("Export")
        self.exportBtn.setObjectName("TopBtn")

        top.addWidget(self.search)
        top.addWidget(self.filterBtn)
        top.addWidget(self.exportBtn)

        root.addLayout(top)

        self.table = QTableWidget(6, 7)
        self.table.setHorizontalHeaderLabels([
            "Date", "Batch Number", "Grade", "Score",
            "Moisture", "Recommendation", "Actions"
        ])

        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        header.setFixedHeight(55)

        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 260)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 360)
        self.table.setColumnWidth(6, 160)

        data = [
            ["03/14/2026", "BCH-2026-001", "A", "89", "12.4%", "Ready for storage"],
            ["03/14/2026", "BCH-2026-002", "B", "75", "13.8%", "Monitor moisture"],
            ["03/13/2026", "BCH-2026-003", "C", "62", "15.2%", "Needs further drying"],
            ["03/13/2026", "BCH-2026-004", "Reject", "—", "18.5%", "Separate & discard"],
        ]

        text_color = QColor(TEXT_BLACK)

        for r, row in enumerate(data):
            self.table.setRowHeight(r, 80)

            for c, val in enumerate(row):
                item = QTableWidgetItem(val)

                if c in [0, 3, 4]:
                    item.setTextAlignment(Qt.AlignCenter)
                elif c == 2:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                if c == 2:
                    font = QFont("Segoe UI", 16, QFont.Bold)
                else:
                    font = QFont("Segoe UI", 13, QFont.Bold)

                item.setFont(font)
                item.setForeground(QBrush(text_color))
                self.table.setItem(r, c, item)

            self.table.setCellWidget(r, 6, ActionButton())

        root.addWidget(self.table)

        self.search.textChanged.connect(self.search_batch)
        self.filterBtn.clicked.connect(self.filter_today)

        self.setStyleSheet(f"""
        #HistoryDialog {{
            background: #efe9e2;
        }}

        #Title {{
            font-size: 40px;
            font-weight: 900;
            color: {TITLE_BROWN};
            margin: 20px;
        }}

        #Search {{
            background: white;
            border: 2px solid #d8cab9;
            border-radius: 10px;
            padding: 12px;
            font-size: 18px;
            font-weight: 700;
            color: {TEXT_GOLD};
        }}

        #TopBtn {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #9c6a22,
                stop:1 #be8a2f
            );
            color: white;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 800;
            padding: 14px 28px;
        }}

        #HistoryDialog QTableWidget {{
            background: #efe9e2;
            border-radius: 12px;
            border: 1px solid #e4d8ca;
        }}

        QHeaderView::section {{
            background: #9c6a22;
            color: white;
            font-weight: 800;
            font-size: 14px;
            border: none;
            padding: 10px;
        }}

        QTableWidget::item {{
            border-bottom: 1px solid #e7dbcf;
        }}

        #ActionBtn {{
            background: #efe5db;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 800;
            color: #6a3d10;
        }}

        #ActionBtn:hover {{
            background: #e6d8c5;
        }}
        """)

    def apply_filters(self):
        search_text = self.search.text().strip().lower()
        today = QDate.currentDate().toString("MM/dd/yyyy")

        for row in range(self.table.rowCount()):
            batch_item = self.table.item(row, 1)
            date_item = self.table.item(row, 0)

            if batch_item is None or date_item is None:
                self.table.setRowHidden(row, True)
                continue

            matches_search = search_text in batch_item.text().lower()

            if self.filter_is_on:
                matches_filter = date_item.text() == today
            else:
                matches_filter = True

            self.table.setRowHidden(row, not (matches_search and matches_filter))

    def search_batch(self):
        self.apply_filters()

    def filter_today(self):
        self.filter_is_on = not self.filter_is_on
        self.apply_filters()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = HistoryDialog()
    w.show()
    sys.exit(app.exec_())