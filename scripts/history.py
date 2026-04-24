import os
os.environ["QT_QPA_PLATFORM"] = "wayland"
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_VIRTUALKEYBOARD_LAYOUT_PATH"] = "/usr/share/qt5/qml/QtQuick/VirtualKeyboard/content/layouts"
os.environ["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"
from PyQt5.QtCore import Qt, QDate, QEvent, QLibraryInfo, QTimer
print(QLibraryInfo.location(QLibraryInfo.PluginsPath))
from PyQt5.QtGui import QColor, QPixmap, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QWidget,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy, QAbstractScrollArea,
    QScrollArea, QGridLayout, QComboBox, QCheckBox, QDateEdit
)
import sqlite3
from create_tables import DB_PATH
from db_helper import get_batches, get_grade_counts, get_batch_images
import logging
from PyQt5.QtCore import QCoreApplication
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
from report import OnScreenKeyboard

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
# FILTER DIALOG
# -----------------------------
class FilterDialog(QDialog):
    def __init__(self, operators=None, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(430, 420)

        if operators is None:
            operators = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        self.card = QFrame()
        self.card.setObjectName("FilterCard")
        outer.addWidget(self.card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(44, 28, 16, 55))
        self.card.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(14)

        top = QHBoxLayout()
        title = QLabel("Filter History")
        title.setObjectName("FilterTitle")

        self.closeBtn = QPushButton("✕")
        self.closeBtn.setObjectName("CloseBtn")
        self.closeBtn.setFixedSize(42, 42)
        self.closeBtn.clicked.connect(self.reject)

        top.addWidget(title, 1)
        top.addWidget(self.closeBtn, 0, Qt.AlignTop)
        root.addLayout(top)

        # Operator
        root.addWidget(QLabel("Operator"))
        self.operatorCombo = QComboBox()
        self.operatorCombo.setObjectName("FilterInput")
        self.operatorCombo.addItem("All Operators")
        self.operatorCombo.addItems(operators)
        root.addWidget(self.operatorCombo)

        # Grade
        root.addWidget(QLabel("Grade"))
        self.gradeCombo = QComboBox()
        self.gradeCombo.setObjectName("FilterInput")
        self.gradeCombo.addItems(["All Grades", "G1", "G2", "G3", "Rejected"])
        root.addWidget(self.gradeCombo)

        # Today only
        self.todayCheck = QCheckBox("Today Only")
        self.todayCheck.setObjectName("FilterCheck")
        root.addWidget(self.todayCheck)

        # Date range
        root.addWidget(QLabel("Date Range"))
        dateRow = QHBoxLayout()

        self.fromDate = QDateEdit()
        self.fromDate.setObjectName("FilterInput")
        self.fromDate.setCalendarPopup(True)
        self.fromDate.setDisplayFormat("yyyy-MM-dd")
        self.fromDate.setDate(QDate.currentDate().addDays(-30))

        self.toDate = QDateEdit()
        self.toDate.setObjectName("FilterInput")
        self.toDate.setCalendarPopup(True)
        self.toDate.setDisplayFormat("yyyy-MM-dd")
        self.toDate.setDate(QDate.currentDate())

        dateRow.addWidget(QLabel("From"))
        dateRow.addWidget(self.fromDate, 1)
        dateRow.addWidget(QLabel("To"))
        dateRow.addWidget(self.toDate, 1)
        root.addLayout(dateRow)

        self.useDateRangeCheck = QCheckBox("Use Date Range")
        self.useDateRangeCheck.setObjectName("FilterCheck")
        root.addWidget(self.useDateRangeCheck)

        btnRow = QHBoxLayout()

        self.resetBtn = QPushButton("Reset")
        self.resetBtn.setObjectName("SecondaryBtn")
        self.resetBtn.setMinimumHeight(46)

        self.applyBtn = QPushButton("Apply")
        self.applyBtn.setObjectName("PrimaryBtn")
        self.applyBtn.setMinimumHeight(46)

        btnRow.addWidget(self.resetBtn)
        btnRow.addWidget(self.applyBtn)
        root.addLayout(btnRow)

        self.resetBtn.clicked.connect(self.reset_filters)
        self.applyBtn.clicked.connect(self.accept)

        self.setStyleSheet("""
        QDialog { background: rgba(36, 24, 14, 70); }
        #FilterCard {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #fbf7f2, stop:1 #f6efe7);
            border-radius: 24px;
            border: 1px solid #eadccc;
        }
        #FilterTitle {
            font-size: 28px;
            font-weight: 900;
            color: #6f3d0c;
        }
        QLabel {
            font-size: 14px;
            font-weight: 700;
            color: #7a4a1d;
        }
        #FilterInput, QDateEdit#FilterInput, QComboBox#FilterInput {
            background: #ffffff;
            border: 1.5px solid #dfd0c0;
            border-radius: 12px;
            padding: 10px 14px;
            font-size: 14px;
            font-weight: 700;
            color: #55331b;
            min-height: 24px;
        }
        #FilterInput:focus {
            border: 1.5px solid #be8a2f;
        }
        #FilterCheck {
            font-size: 14px;
            font-weight: 700;
            color: #55331b;
            padding: 4px 0;
        }
        #PrimaryBtn {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #9c6a22, stop:1 #be8a2f);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 800;
            padding: 0 20px;
        }
        #PrimaryBtn:hover { background: #a87428; }
        #SecondaryBtn {
            background: #f1e8de;
            color: #7a4a1d;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 800;
            padding: 0 20px;
        }
        #SecondaryBtn:hover { background: #e9ddd0; }
        #CloseBtn {
            background: #f1e8de;
            color: #7a4a1d;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 900;
        }
        #CloseBtn:hover { background: #e9ddd0; }
        """)

    def reset_filters(self):
        self.operatorCombo.setCurrentIndex(0)
        self.gradeCombo.setCurrentIndex(0)
        self.todayCheck.setChecked(False)
        self.useDateRangeCheck.setChecked(False)
        self.fromDate.setDate(QDate.currentDate().addDays(-30))
        self.toDate.setDate(QDate.currentDate())


# -----------------------------
# BATCH DETAILS DIALOG
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

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scrollContent = QWidget()
        self.vbox = QVBoxLayout(scrollContent)
        self.vbox.setContentsMargins(4, 4, 4, 4)
        self.vbox.setSpacing(24)

        grades = ["G1", "G2", "G3", "Rejected"]
        images_by_grade = {g: [] for g in grades}

        for idx, item in enumerate(images_data, start=1):
            raw_grade = item.get("grade", "").upper()

            # ✅ Proper normalization
            if raw_grade == "GRADE 1":
                ui_grade = "G1"
            elif raw_grade == "GRADE 2":
                ui_grade = "G2"
            elif raw_grade == "GRADE 3":
                ui_grade = "G3"
            else:
                ui_grade = "Rejected"

            images_by_grade[ui_grade].append((idx, item.get("image_path", "")))

        for grade in grades:
            group_images = images_by_grade.get(grade, [])
            if not group_images:
                continue

            grade_label = QLabel(grade)
            grade_label.setAlignment(Qt.AlignCenter)  # center horizontally
            grade_label.setStyleSheet("""
                font-size: 24px;
                font-weight: 900;
                color: white;
                background-color: #be8a2f;  /* golden/brown shade */
                padding: 4px 16px;
                border-radius: 12px;
                margin: 12px 0 12px 0;
            """)
            self.vbox.addWidget(grade_label)

            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(16)
            grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # ← align images to top-left

            for i, (idx, img_path) in enumerate(group_images):
                card = ImageOnlyCard(img_path)  # use the clean image card
                row = i // 3
                col = i % 3
                grid.addWidget(card, row, col)

            self.vbox.addLayout(grid)

        self.scroll.setWidget(scrollContent)
        root.addWidget(self.scroll)

        self.setStyleSheet("""
        QDialog { background: rgba(36, 24, 14, 70); }
        #DetailsCard {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #fbf7f2, stop:1 #f6efe7);
            border-radius:28px;
            border:1px solid #eadccc;
        }
        #DetailsTitle { font-size:40px; font-weight:900; color:#6f3d0c; margin:2px 0 2px 0; letter-spacing:0.5px; }
        #DetailsBatch { font-size:16px; font-weight:700; color:#9a6a2a; }
        #CloseBtn {
            background:#f1e8de;
            color:#7a4a1d;
            border:none;
            border-radius:14px;
            font-size:18px;
            font-weight:900;
        }
        #CloseBtn:hover { background:#e9ddd0; }
        #ScanCard { background:white; border:1px solid #eadccc; border-radius:18px; }
        #ScanTitle { font-size:16px; font-weight:800; color:#55331b; }
        #ScanImage {
            background:#f7f1ea;
            border:1px dashed #d8c8b9;
            border-radius:14px;
            color:#aa8d70;
            font-size:14px;
            font-weight:700;
            padding:10px;
        }
        #GradeBadge {
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #9c6a22, stop:1 #be8a2f);
            color:white;
            border-radius:12px;
            padding:10px 12px;
            font-size:15px;
            font-weight:900;
        }
        QScrollArea { background: transparent; }
        """)

class ImageOnlyCard(QWidget):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setMinimumSize(220, 160)
        self.imageLabel.setMaximumHeight(180)

        if image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                self.imageLabel.setPixmap(
                    pix.scaled(220, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self.imageLabel.setText("No scan image")
        else:
            self.imageLabel.setText("No scan image")

        layout.addWidget(self.imageLabel)
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

        self.active_filters = {
            "operator": "",
            "grade": "",
            "today_only": False,
            "use_date_range": False,
            "from_date": QDate.currentDate().addDays(-30),
            "to_date": QDate.currentDate()
        }

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

        self.search.setFocusPolicy(Qt.StrongFocus)
        self.search.setAttribute(Qt.WA_InputMethodEnabled, True)
        QTimer.singleShot(50, self.search.setFocus)

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
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        header = self.table.horizontalHeader()
        header.setFixedHeight(54)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # --- STACKED AREA (TABLE + KEYBOARD) ---
        self.stackContainer = QWidget()
        self.stackLayout = QVBoxLayout(self.stackContainer)
        self.stackLayout.setContentsMargins(0, 0, 0, 0)
        self.stackLayout.setSpacing(0)

        # Table (main view)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Keyboard (hidden by default)
        self.keyboard = OnScreenKeyboard(self.search)
        self.keyboard.setVisible(False)
        self.keyboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.keyboard.setMinimumHeight(320)
        self.keyboard.setMaximumHeight(350)

        # Add both into stack
        self.stackLayout.addWidget(self.table, 1)
        self.stackLayout.addWidget(self.keyboard, 0)

        # Add stack to main layout
        root.addWidget(self.stackContainer, 1)

        self.search.installEventFilter(self)
        self.table.installEventFilter(self)
        self.card.installEventFilter(self)

        self.load_history_data()
        self.pad_table()

        self.search.textChanged.connect(self.apply_all_filters)
        self.filterBtn.clicked.connect(self.open_filter_dialog)
        self.closeBtn.clicked.connect(self.close)

        self.search.installEventFilter(self)

        QTimer.singleShot(200, self.force_keyboard)

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

    def pad_table(self, min_rows=8):
        current = self.table.rowCount()

        for i in range(current, min_rows):
            self.table.insertRow(i)
            for c in range(self.table.columnCount()):
                item = QTableWidgetItem("")
                item.setFlags(Qt.NoItemFlags)
                self.table.setItem(i, c, item)

    def show_keyboard(self):
        self.keyboard.setVisible(True)

    def hide_keyboard(self):
        self.keyboard.setVisible(False)

    def eventFilter(self, obj, event):
        if obj == self.search:
            if event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress):
                self.keyboard.set_target(self.search)
                self.show_keyboard()
                QGuiApplication.inputMethod().show()
                return False

        if event.type() == QEvent.MouseButtonPress:
            if obj != self.search:
                self.hide_keyboard()
                self.search.clearFocus()

        return super().eventFilter(obj, event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.hide_keyboard()
        QGuiApplication.inputMethod().hide()

    def trigger_keyboard(self):
        self.search.setFocus()
        QGuiApplication.inputMethod().show()

    def force_keyboard(self):
        self.search.setFocus()
        QGuiApplication.inputMethod().show()
        QGuiApplication.inputMethod().update(Qt.ImQueryAll)

    def on_search_focus(self, event):
        QLineEdit.focusInEvent(self.search, event)
        self.keyboard.set_target(self.search)
        self.show_keyboard()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.trigger_keyboard()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self.search.setFocus)
            
    def open_search_keyboard(self, event):
        self.search.setFocus()
        QLineEdit.mousePressEvent(self.search, event)

    def wrap_click(self, event):
        self.search.setFocus()
        QLineEdit.mousePressEvent(self.search, event)

    def get_unique_operators(self):
        operators = set()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 3)
            if item and item.text().strip():
                operators.add(item.text().strip())
        return sorted(list(operators))

    def load_history_data(self):
        self.table.setRowCount(0)

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

                mapped_counts = {}
                for grade, count in grade_counts.items():
                    if grade.upper() in ["REJECT", "REJECTED"]:
                        ui_grade = "Rejected"
                    else:
                        ui_grade = grade.replace("GRADE ", "G")
                    mapped_counts[ui_grade] = count

                ordered_grades = ["G1", "G2", "G3", "Rejected"]

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

    def open_filter_dialog(self):
        dialog = FilterDialog(self.get_unique_operators(), self)

        if self.active_filters["operator"]:
            index = dialog.operatorCombo.findText(self.active_filters["operator"])
            if index >= 0:
                dialog.operatorCombo.setCurrentIndex(index)

        if self.active_filters["grade"]:
            index = dialog.gradeCombo.findText(self.active_filters["grade"])
            if index >= 0:
                dialog.gradeCombo.setCurrentIndex(index)

        dialog.todayCheck.setChecked(self.active_filters["today_only"])
        dialog.useDateRangeCheck.setChecked(self.active_filters["use_date_range"])
        dialog.fromDate.setDate(self.active_filters["from_date"])
        dialog.toDate.setDate(self.active_filters["to_date"])

        if dialog.exec_():
            self.active_filters["operator"] = (
                "" if dialog.operatorCombo.currentText() == "All Operators"
                else dialog.operatorCombo.currentText()
            )
            self.active_filters["grade"] = (
                "" if dialog.gradeCombo.currentText() == "All Grades"
                else dialog.gradeCombo.currentText()
            )
            self.active_filters["today_only"] = dialog.todayCheck.isChecked()
            self.active_filters["use_date_range"] = dialog.useDateRangeCheck.isChecked()
            self.active_filters["from_date"] = dialog.fromDate.date()
            self.active_filters["to_date"] = dialog.toDate.date()

            self.apply_all_filters()

    def apply_all_filters(self):
        search_text = self.search.text().strip().lower()
        today = QDate.currentDate().toString("yyyy-MM-dd")

        for r in range(self.table.rowCount()):
            match = True

            batch_item = self.table.item(r, 1)
            date_item = self.table.item(r, 0)
            grade_item = self.table.item(r, 2)
            operator_item = self.table.item(r, 3)

            batch_text = batch_item.text().lower() if batch_item else ""
            date_text = date_item.text() if date_item else ""
            grade_text = grade_item.text() if grade_item else ""
            operator_text = operator_item.text() if operator_item else ""

            # Search batch number
            if search_text and search_text not in batch_text:
                match = False

            # Operator filter
            if self.active_filters["operator"]:
                if operator_text != self.active_filters["operator"]:
                    match = False

            # Grade filter
            if self.active_filters["grade"]:
                selected_grade = self.active_filters["grade"]
                if f"{selected_grade}:" not in grade_text:
                    match = False

            # Today only
            if self.active_filters["today_only"]:
                if date_text != today:
                    match = False

            # Date range
            if self.active_filters["use_date_range"] and not self.active_filters["today_only"]:
                row_date = QDate.fromString(date_text, "yyyy-MM-dd")
                if row_date.isValid():
                    if row_date < self.active_filters["from_date"] or row_date > self.active_filters["to_date"]:
                        match = False
                else:
                    match = False

            self.table.setRowHidden(r, not match)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    app.setAttribute(Qt.AA_InputMethodEnabled, True)    

    w = HistoryDialog()
    w.show()
    sys.exit(app.exec_())