from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush, QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget, QFrame, QGraphicsBlurEffect,
    QGraphicsDropShadowEffect, QSizePolicy, QAbstractScrollArea,
    QScrollArea, QGridLayout
)


# SAMPLE DATA
# Replace image paths with your real saved scan images later
BATCH_SCAN_DATA = {
    "BCH-2026-001": [
        {"image": "", "grade": "Grade 1"},
        {"image": "", "grade": "Grade 1"},
        {"image": "", "grade": "Grade 2"},
        {"image": "", "grade": "Grade 1"},
    ],
    "BCH-2026-002": [
        {"image": "", "grade": "Grade 2"},
        {"image": "", "grade": "Grade 2"},
        {"image": "", "grade": "Grade 3"},
    ],
    "BCH-2026-003": [
        {"image": "", "grade": "Grade 3"},
        {"image": "", "grade": "Reject"},
        {"image": "", "grade": "Grade 3"},
    ],
    "BCH-2026-004": [
        {"image": "", "grade": "Reject"},
        {"image": "", "grade": "Reject"},
    ],
}


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

        pixmap_loaded = False
        if image_path:
            pix = QPixmap(image_path)
            if not pix.isNull():
                self.imageLabel.setPixmap(
                    pix.scaled(
                        220, 160,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                )
                pixmap_loaded = True

        if not pixmap_loaded:
            self.imageLabel.setText("No scan image available")

        root.addWidget(self.imageLabel)

        gradeLabel = QLabel(grade)
        gradeLabel.setObjectName("GradeBadge")
        gradeLabel.setAlignment(Qt.AlignCenter)
        root.addWidget(gradeLabel)


class BatchDetailsDialog(QDialog):
    def __init__(self, batch_number, scan_data, parent=None):
        super().__init__(parent)
        self.parent_blur = None
        self.batch_number = batch_number

        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1120, 760)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 36, 36, 36)
        outer.setSpacing(0)

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

        top = QHBoxLayout()
        top.setSpacing(12)

        titleWrap = QVBoxLayout()
        titleWrap.setSpacing(4)

        title = QLabel("Batch Scan Details")
        title.setObjectName("DetailsTitle")

        batch = QLabel(batch_number)
        batch.setObjectName("DetailsBatch")

        titleWrap.addWidget(title)
        titleWrap.addWidget(batch)

        self.closeBtn = QPushButton("✕")
        self.closeBtn.setObjectName("CloseBtn")
        self.closeBtn.setFixedSize(46, 46)
        self.closeBtn.clicked.connect(self.close)

        top.addLayout(titleWrap, 1)
        top.addWidget(self.closeBtn, 0, Qt.AlignTop)
        root.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scrollContent = QWidget()
        self.grid = QGridLayout(scrollContent)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(16)

        for i, item in enumerate(scan_data, start=1):
            card = ScanCard(i, item.get("image", ""), item.get("grade", "Unknown"))
            row = (i - 1) // 3
            col = (i - 1) % 3
            self.grid.addWidget(card, row, col)

        self.scroll.setWidget(scrollContent)
        root.addWidget(self.scroll, 1)

        self.setStyleSheet("""
        QDialog {
            background: rgba(36, 24, 14, 82);
        }

        #DetailsCard {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #fbf7f2,
                stop:1 #f6efe7
            );
            border-radius: 28px;
            border: 1px solid #eadccc;
        }

        #DetailsTitle {
            font-size: 30px;
            font-weight: 900;
            color: #6f3d0c;
        }

        #DetailsBatch {
            font-size: 16px;
            font-weight: 700;
            color: #9a6a2a;
        }

        #CloseBtn {
            background: #f1e8de;
            color: #7a4a1d;
            border: none;
            border-radius: 14px;
            font-size: 18px;
            font-weight: 900;
        }

        #CloseBtn:hover {
            background: #e9ddd0;
        }

        #ScanCard {
            background: white;
            border: 1px solid #eadccc;
            border-radius: 18px;
        }

        #ScanTitle {
            font-size: 16px;
            font-weight: 800;
            color: #55331b;
        }

        #ScanImage {
            background: #f7f1ea;
            border: 1px dashed #d8c8b9;
            border-radius: 14px;
            color: #aa8d70;
            font-size: 14px;
            font-weight: 700;
            padding: 10px;
        }

        #GradeBadge {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #9c6a22,
                stop:1 #be8a2f
            );
            color: white;
            border-radius: 12px;
            padding: 10px 12px;
            font-size: 15px;
            font-weight: 900;
        }

        QScrollArea {
            background: transparent;
        }

        QScrollBar:horizontal {
            height: 0px;
        }

        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 4px 0 4px 0;
        }

        QScrollBar::handle:vertical {
            background: #d8c3a8;
            border-radius: 5px;
            min-height: 24px;
        }

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            self.parent_blur = QGraphicsBlurEffect()
            self.parent_blur.setBlurRadius(8)
            self.parent().setGraphicsEffect(self.parent_blur)

    def closeEvent(self, event):
        if self.parent():
            self.parent().setGraphicsEffect(None)
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if not self.card.geometry().contains(event.pos()):
            self.close()
        else:
            super().mousePressEvent(event)


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.filter_is_on = False
        self.parent_blur = None

        self.setModal(True)
        self.setWindowTitle("History")
        self.resize(1240, 760)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 36, 36, 36)
        outer.setSpacing(0)

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

        self.table = QTableWidget(4, 7)
        self.table.setObjectName("HistoryTable")
        self.table.setHorizontalHeaderLabels([
            "Date", "Batch Number", "Amount", "Operator",
            "Average", "Recommendation", "Actions"
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
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header = self.table.horizontalHeader()
        header.setFixedHeight(54)
        header.setDefaultAlignment(Qt.AlignCenter)

        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(6, 120)

        self.data = [
            ["03/14/2026", "BCH-2026-001", "200", "Aidan89", "12.4%", "Ready for storage"],
            ["03/14/2026", "BCH-2026-002", "340", "Aidan", "13.8%", "Monitor moisture"],
            ["03/13/2026", "BCH-2026-003", "432", "Sherwin", "15.2%", "Needs further drying"],
            ["03/13/2026", "BCH-2026-004", "341", "Sherwin", "18.5%", "Separate & discard"],
        ]

        text_color = QColor("#2e2218")

        for r, row in enumerate(self.data):
            self.table.setRowHeight(r, 68)

            for c, val in enumerate(row):
                item = QTableWidgetItem(val)

                if c in [0, 2, 3, 4]:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                font = QFont("Segoe UI", 11, QFont.DemiBold if c == 5 else QFont.Bold)
                item.setFont(font)
                item.setForeground(QBrush(text_color))
                self.table.setItem(r, c, item)

            batch_number = row[1]
            widget = ClickableActionButton(
                callback=lambda checked=False, bn=batch_number: self.open_batch_details(bn)
            )
            self.table.setCellWidget(r, 6, widget)

        root.addWidget(self.table, 1)

        self.search.textChanged.connect(self.search_batch)
        self.filterBtn.clicked.connect(self.filter_today)
        self.closeBtn.clicked.connect(self.close)

        self.setStyleSheet("""
        QDialog {
            background: rgba(36, 24, 14, 70);
        }

        #Card {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #fbf7f2,
                stop:1 #f6efe7
            );
            border-radius: 28px;
            border: 1px solid #eadccc;
        }

        #Title {
            font-size: 40px;
            font-weight: 900;
            color: #6f3d0c;
            margin: 2px 0 2px 0;
            letter-spacing: 0.5px;
        }

        #Search {
            background: #ffffff;
            border: 1.5px solid #dfd0c0;
            border-radius: 14px;
            padding: 0 18px;
            font-size: 16px;
            font-weight: 700;
            color: #55331b;
            selection-background-color: #d6b17a;
        }

        #Search:focus {
            border: 1.5px solid #be8a2f;
        }

        #Search::placeholder {
            color: #b39474;
        }

        #TopBtn {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #9c6a22,
                stop:1 #be8a2f
            );
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 800;
            padding: 0 24px;
        }

        #TopBtn:hover {
            background: #a87428;
        }

        #TopBtn:pressed {
            background: #8a5d1f;
        }

        #CloseBtn {
            background: #f1e8de;
            color: #7a4a1d;
            border: none;
            border-radius: 14px;
            font-size: 18px;
            font-weight: 900;
        }

        #CloseBtn:hover {
            background: #e9ddd0;
        }

        #HistoryTable {
            background: transparent;
            border: none;
            gridline-color: transparent;
        }

        QHeaderView::section {
            background: #f4eee7;
            color: #7a4a1d;
            font-weight: 800;
            font-size: 13px;
            border: none;
            border-bottom: 1px solid #e3d5c6;
            padding: 10px 8px;
        }

        QTableCornerButton::section {
            background: transparent;
            border: none;
        }

        QTableWidget::item {
            background-color: #ffffff;
            border-top: 8px solid #f6efe7;
            border-bottom: 8px solid #f6efe7;
            padding-left: 12px;
            padding-right: 12px;
        }

        QScrollBar:horizontal {
            height: 0px;
        }

        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 4px 0 4px 0;
        }

        QScrollBar::handle:vertical {
            background: #d8c3a8;
            border-radius: 5px;
            min-height: 24px;
        }

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }

        #ActionBtn {
            background: #f6efe7;
            border: 1px solid #e2d2c2;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 800;
            color: #7a4a1d;
            padding: 0 14px;
        }

        #ActionBtn:hover {
            background: #efe4d7;
        }

        #ActionBtn:pressed {
            background: #e7d8c6;
        }
        """)

    def open_batch_details(self, batch_number):
        scan_data = BATCH_SCAN_DATA.get(batch_number, [])
        dialog = BatchDetailsDialog(batch_number, scan_data, self)
        dialog.exec_()

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            self.parent_blur = QGraphicsBlurEffect()
            self.parent_blur.setBlurRadius(8)
            self.parent().setGraphicsEffect(self.parent_blur)

    def closeEvent(self, event):
        if self.parent():
            self.parent().setGraphicsEffect(None)
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if not self.card.geometry().contains(event.pos()):
            self.close()
        else:
            super().mousePressEvent(event)

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
            matches_filter = (date_item.text() == today) if self.filter_is_on else True

            self.table.setRowHidden(row, not (matches_search and matches_filter))

    def search_batch(self):
        self.apply_filters()

    def filter_today(self):
        self.filter_is_on = not self.filter_is_on
        self.filterBtn.setText("Today" if self.filter_is_on else "Filter")
        self.apply_filters()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = HistoryDialog()
    w.show()
    sys.exit(app.exec_())