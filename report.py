from PyQt5.QtCore import Qt, QTimer, QEventLoop, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QWidget, QFrame, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QSizePolicy,
    QGraphicsDropShadowEffect, QGraphicsBlurEffect,
    QTextEdit, QScrollArea, QGridLayout, QApplication
)
from datetime import datetime
from printer import generate_receipt, print_to_usb 
from db_helper import get_last_operator, get_operator_id
from create_tables import create_new_batch, DB_PATH

RECEIPT_SCHEMA = {
    "grade": 0,
    "avg_confidence": 0,
    "operator": "",
    "operator_id": None,
    "batch": "",
    "batch_id": None,
    "g1": 0,
    "g2": 0,
    "g3": 0,
    "reject": 0,
    "date": "",
    "time": ""
}

class OnScreenKeyboard(QWidget):
    def __init__(self, target_input, parent=None):
        super().__init__(parent)
        self.target_input = target_input

        self.caps_on = True
        self.letter_buttons = []
        self.caps_button = None

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        self.rows = []

        keys = [
            ['1','2','3','4','5','6','7','8','9','0'],
            ['Q','W','E','R','T','Y','U','I','O','P'],
            ['A','S','D','F','G','H','J','K','L'],
            ['CAPS','Z','X','C','V','B','N','M','BACK'],
            ['SPACE']
        ]

        for row in keys:
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            row_layout.setContentsMargins(0, 0, 0, 0)

            for key in row:
                btn = QPushButton(key)

                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setMinimumHeight(55)

                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 20px;
                        font-weight: bold;
                        background: #e8ded3;
                        border: 1px solid #cbb9a6;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background: #ddd0c2;
                    }
                """)

                if key.isalpha():
                    self.letter_buttons.append(btn)

                if key == "CAPS":
                    self.caps_button = btn

                btn.clicked.connect(lambda _, k=key: self.handle_key(k))

                # flexible space behavior
                if key == "SPACE":
                    btn.setMinimumWidth(200)

                if key == "BACK":
                    btn.setMinimumWidth(120)

                row_layout.addWidget(btn)

            row_widget.setLayout(row_layout)
            main_layout.addWidget(row_widget)

            self.rows.append(row_widget)

        self.setLayout(main_layout)

        self.update_keys()
        
    def set_target(self, target_input):
        self.target_input = target_input

    def update_keys(self):
        # Update letter case visually
        for btn in self.letter_buttons:
            text = btn.text()
            btn.setText(text.upper() if self.caps_on else text.lower())

        # Highlight CAPS when active
        if self.caps_button:
            if self.caps_on:
                self.caps_button.setStyleSheet("""
                    QPushButton {
                        font-size: 20px;
                        font-weight: bold;
                        background: #b88445;
                        color: white;
                        border-radius: 8px;
                    }
                """)
            else:
                self.caps_button.setStyleSheet("""
                    QPushButton {
                        font-size: 20px;
                        font-weight: bold;
                        background: #e8ded3;
                        border: 1px solid #cbb9a6;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background: #ddd0c2;
                    }
                """)

    def handle_key(self, key):
        target = self.target_input
        if not target:
            return

        # 🔥 CAPS toggle
        if key == "CAPS":
            self.caps_on = not self.caps_on
            self.update_keys()
            return

        # 🔥 Determine actual character
        if key.isalpha():
            char = key.upper() if self.caps_on else key.lower()
        else:
            char = key

        # QTextEdit
        if isinstance(target, QTextEdit):
            if key == "SPACE":
                target.insertPlainText(" ")
            elif key == "BACK":
                cursor = target.textCursor()
                cursor.deletePreviousChar()
            else:
                target.insertPlainText(char)

        # QLineEdit
        else:
            try:
                if key == "SPACE":
                    target.insert(" ")
                elif key == "BACK":
                    text = target.text()
                    target.setText(text[:-1])
                else:
                    target.insert(char)
            except:
                pass

class OperatorInputDialog(QDialog):
    def __init__(self, parent=None, current_name=""):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)

        # 🔥 Let it scale instead of forcing small size
        self.setMinimumSize(900, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 🏷️ Title
        title = QLabel("Enter Operator Name:")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
        """)

        # 📝 Input field
        self.input = QTextEdit()
        self.input.setFixedHeight(70)
        self.input.setText(current_name)
        self.input.setFocus()

        self.input.setStyleSheet("""
            QTextEdit {
                font-size: 20px;
                padding: 6px;
                border: 2px solid #cbb9a6;
                border-radius: 6px;
                background: #ffffff;
            }
        """)

        # ⌨️ Keyboard
        self.keyboard = OnScreenKeyboard(self.input)

        # 🔘 Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        for btn in (ok_btn, cancel_btn):
            btn.setMinimumHeight(45)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    font-weight: bold;
                    background: #7a522d;
                    color: white;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #694422;
                }
            """)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)

        # 🧩 Layout assembly
        layout.addWidget(title)
        layout.addWidget(self.input)
        layout.addWidget(self.keyboard, 1)  # 🔥 THIS makes keyboard take space
        layout.addLayout(btn_row)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_value(self):
        return self.input.toPlainText().strip()

class ReportDialog(QDialog):
    operator_changed = pyqtSignal(int, str)
    request_new_batch = pyqtSignal()

    def __init__(self, parent=None, batch_id=None):
        super().__init__(parent)
        self.batch_id = batch_id
        self.main_parent = parent
        self.blur_effect = None

        self.grade_counts = {
            "g1": 20,
            "g2": 30,
            "g3": 20,
            "reject": 10
        }
        self.current_operator_id = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1360, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        self.panel = QFrame()
        self.panel.setObjectName("OuterCard")
        panelLay = QVBoxLayout(self.panel)
        panelLay.setContentsMargins(0, 0, 0, 10)
        panelLay.setSpacing(0)

        # HEADER
        headerWrap = QFrame()
        headerWrap.setObjectName("HeaderWrap")
        headerLay = QHBoxLayout(headerWrap)
        headerLay.setContentsMargins(18, 0, 10, 0)
        headerLay.setSpacing(8)

        self.header = QLabel("COPRA GRADING MACHINE")
        self.header.setObjectName("HeaderBar")
        self.header.setAlignment(Qt.AlignCenter)

        self.closeBtn = QPushButton("×")
        self.closeBtn.setObjectName("TopCloseBtn")
        self.closeBtn.setFixedSize(34, 34)
        self.closeBtn.clicked.connect(self.close)

        headerLay.addStretch(1)
        headerLay.addWidget(self.header, 0, Qt.AlignCenter)
        headerLay.addStretch(1)
        headerLay.addWidget(self.closeBtn, 0, Qt.AlignRight | Qt.AlignVCenter)

        panelLay.addWidget(headerWrap)

        # INFO ROW
        infoWrap = QFrame()
        infoWrap.setObjectName("InfoWrap")
        infoLay = QHBoxLayout(infoWrap)
        infoLay.setContentsMargins(14, 8, 14, 8)
        infoLay.setSpacing(10)

        self.dateLabel = QLabel("Date: Mar 14, 2026")
        self.timeLabel = QLabel("Time: 10:42 AM")
        self.operatorLabel = QLabel("Operator: John D.")
        

        self.dateLabel.setObjectName("TopInfo")
        self.timeLabel.setObjectName("TopInfo")
        self.operatorLabel.setObjectName("TopInfo")

        self.editOperatorBtn = QPushButton("✎")
        self.editOperatorBtn.setObjectName("TopEditBtn")
        self.editOperatorBtn.setFixedSize(26, 26)
        self.editOperatorBtn.setCursor(Qt.PointingHandCursor)
        
        sep = QLabel("|")
        sep.setObjectName("TopSep")

        infoLay.addWidget(self.dateLabel)
        infoLay.addWidget(sep)
        infoLay.addWidget(self.timeLabel)
        infoLay.addStretch(1)

        opWrap = QHBoxLayout()
        opWrap.setSpacing(6)
        opWrap.addWidget(self.operatorLabel)
        opWrap.addWidget(self.editOperatorBtn)

        opContainer = QWidget()
        opContainer.setLayout(opWrap)

        infoLay.addWidget(opContainer, 0, Qt.AlignRight | Qt.AlignVCenter)

        panelLay.addWidget(infoWrap)

        # MAIN CONTENT AREA
        mainWrap = QFrame()
        mainWrap.setObjectName("MainWrap")
        mainLay = QHBoxLayout(mainWrap)
        mainLay.setContentsMargins(10, 0, 10, 0)
        mainLay.setSpacing(8)
        panelLay.addWidget(mainWrap, 1)

        # LEFT SIDE
        leftPanel = QFrame()
        leftPanel.setObjectName("LeftPanel")
        leftLay = QVBoxLayout(leftPanel)
        leftLay.setContentsMargins(0, 0, 0, 0)
        leftLay.setSpacing(10)
        mainLay.addWidget(leftPanel, 5)

        self.resultCard = QFrame()
        self.resultCard.setObjectName("ResultCard")
        self.resultCard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card = QVBoxLayout(self.resultCard)
        card.setContentsMargins(14, 10, 14, 14)
        card.setSpacing(10)
        leftLay.addWidget(self.resultCard, 1)

        # TITLE
        titleRow = QHBoxLayout()
        titleRow.setSpacing(14)

        leftLine = QFrame()
        leftLine.setObjectName("TitleLine")
        leftLine.setFixedHeight(1)

        rightLine = QFrame()
        rightLine.setObjectName("TitleLine")
        rightLine.setFixedHeight(1)

        self.title = QLabel("GRADING RESULT")
        self.title.setObjectName("ResultTitle")
        self.title.setAlignment(Qt.AlignCenter)

        titleRow.addWidget(leftLine, 1)
        titleRow.addWidget(self.title, 0)
        titleRow.addWidget(rightLine, 1)
        card.addLayout(titleRow)

        # BODY
        contentRow = QHBoxLayout()
        contentRow.setSpacing(18)
        card.addLayout(contentRow, 1)

        # LEFT TEXT CONTENT
        leftCol = QVBoxLayout()
        leftCol.setContentsMargins(10, 18, 0, 10)
        leftCol.setSpacing(8)
        contentRow.addLayout(leftCol, 5)

        leftCol.addStretch(1)

        self.batchLabel = QLabel("Batch: BCH-2026-001")
        self.batchLabel.setObjectName("MainText")
        leftCol.addWidget(self.batchLabel)

        self.gradeLabel = QLabel("Grade:")
        self.gradeLabel.setObjectName("MainTextSoft")
        leftCol.addWidget(self.gradeLabel)

        # GRADE GRID
        self.gradeGridWrap = QFrame()
        self.gradeGridWrap.setObjectName("GradeGridWrap")
        gradeGrid = QGridLayout(self.gradeGridWrap)
        gradeGrid.setContentsMargins(0, 0, 0, 0)
        gradeGrid.setHorizontalSpacing(26)
        gradeGrid.setVerticalSpacing(4)

        self.g1Label = QLabel("1 = 20pcs")
        self.g1Label.setObjectName("MainTextSoft")

        self.g3Label = QLabel("3 = 20pcs")
        self.g3Label.setObjectName("MainTextSoft")

        self.g2Label = QLabel("2 = 30pcs")
        self.g2Label.setObjectName("MainTextSoft")

        self.rejectLabel = QLabel("Rejects = 10pcs")
        self.rejectLabel.setObjectName("MainTextSoft")

        gradeGrid.addWidget(self.g1Label, 0, 0)
        gradeGrid.addWidget(self.g3Label, 0, 1)
        gradeGrid.addWidget(self.g2Label, 1, 0)
        gradeGrid.addWidget(self.rejectLabel, 1, 1)

        leftCol.addWidget(self.gradeGridWrap)

        self.recommendationLabel = QLabel("Recommendation: Ready for storage and\nselling")
        self.recommendationLabel.setObjectName("MainText")
        self.recommendationLabel.setWordWrap(True)
        leftCol.addWidget(self.recommendationLabel)

        leftCol.addStretch(1)

        # RIGHT GRADE CARD
        rightCol = QVBoxLayout()
        rightCol.setContentsMargins(0, 8, 8, 8)
        rightCol.setSpacing(0)
        contentRow.addLayout(rightCol, 4)

        rightCol.addStretch(1)

        self.gradeCard = QFrame()
        self.gradeCard.setObjectName("GradeCard")
        self.gradeCard.setMinimumSize(250, 165)
        self.gradeCard.setMaximumSize(300, 190)
        self.gradeCard.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        gradeLay = QVBoxLayout(self.gradeCard)
        gradeLay.setContentsMargins(18, 14, 18, 14)
        gradeLay.setSpacing(8)

        self.gradeTag = QLabel("GRADE")
        self.gradeTag.setObjectName("GradeTag")
        self.gradeTag.setAlignment(Qt.AlignCenter)
        self.gradeTag.setFixedHeight(40)

        self.gradeNumber = QLabel("1")
        self.gradeNumber.setObjectName("GradeNumber")
        self.gradeNumber.setAlignment(Qt.AlignCenter)

        gradeLay.addWidget(self.gradeTag, 0, Qt.AlignHCenter)
        gradeLay.addStretch(1)
        gradeLay.addWidget(self.gradeNumber, 0, Qt.AlignCenter)
        gradeLay.addStretch(1)

        rightCol.addWidget(self.gradeCard, 0, Qt.AlignCenter)
        rightCol.addStretch(1)

        # BUTTONS
        btnRow = QHBoxLayout()
        btnRow.setSpacing(10)
        btnRow.setContentsMargins(0, 0, 0, 0)
        leftLay.addLayout(btnRow)

        self.printBtn = QPushButton("Print Receipt")
        self.scanBtn = QPushButton("New Scan")
        self.historyBtn = QPushButton("View History")

        for btn in (self.printBtn, self.scanBtn, self.historyBtn):
            btn.setObjectName("ActionBtn")
            btn.setMinimumHeight(38)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btnRow.addWidget(btn)

        # RIGHT SIDE - RECEIPT PANEL
        self.receiptPanel = QFrame()
        self.receiptPanel.setObjectName("ReceiptPanel")
        receiptPanelLay = QVBoxLayout(self.receiptPanel)
        receiptPanelLay.setContentsMargins(10, 10, 10, 10)
        receiptPanelLay.setSpacing(8)
        mainLay.addWidget(self.receiptPanel, 1)

        self.receiptLogo = QLabel("🧾")
        self.receiptLogo.setObjectName("ReceiptLogo")
        self.receiptLogo.setAlignment(Qt.AlignCenter)

        self.receiptHeader = QLabel("COPRA QUALITY ANALYSIS")
        self.receiptHeader.setObjectName("ReceiptHeader")
        self.receiptHeader.setAlignment(Qt.AlignCenter)

        self.receiptSubHeader = QLabel("SYSTEM RECEIPT")
        self.receiptSubHeader.setObjectName("ReceiptSubHeader")
        self.receiptSubHeader.setAlignment(Qt.AlignCenter)

        self.receiptLine = QFrame()
        self.receiptLine.setObjectName("ReceiptLine")
        self.receiptLine.setFrameShape(QFrame.HLine)

        receiptPanelLay.addWidget(self.receiptLogo)
        receiptPanelLay.addWidget(self.receiptHeader)
        receiptPanelLay.addWidget(self.receiptSubHeader)
        receiptPanelLay.addWidget(self.receiptLine)

        self.receiptScroll = QScrollArea()
        self.receiptScroll.setWidgetResizable(True)
        self.receiptScroll.setFrameShape(QFrame.NoFrame)
        self.receiptScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.receiptContent = QWidget()
        self.receiptContentLay = QVBoxLayout(self.receiptContent)
        self.receiptContentLay.setContentsMargins(0, 0, 0, 0)
        self.receiptContentLay.setSpacing(0)

        self.receiptText = QTextEdit()
        self.receiptText.setReadOnly(True)
        self.receiptText.setObjectName("ReceiptText")
        self.receiptText.setFont(QFont("Courier New", 9))
        self.receiptText.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.receiptText.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.receiptContentLay.addWidget(self.receiptText)
        self.receiptScroll.setWidget(self.receiptContent)
        receiptPanelLay.addWidget(self.receiptScroll, 1)

        root.addWidget(self.panel)

        self.apply_styles()
        self.add_shadow()
        self.setup_connections()
        self.refresh_grade_summary()

        # 🔥 delay receipt rendering until UI is fully ready
        QTimer.singleShot(0, self.refresh_receipt_preview)
        self.set_operator(get_last_operator())

        self.operator_name = get_last_operator()
        self.current_operator_id = get_operator_id(self.operator_name)

        self.current_grade_number = 1

    def setup_connections(self):
        self.scanBtn.clicked.connect(self.close)
        self.historyBtn.clicked.connect(self.open_history)
        self.printBtn.clicked.connect(self.print_report)
        self.editOperatorBtn.clicked.connect(self.modify_operator)

    def modify_operator(self):
        dialog = OperatorInputDialog(
            self,
            current_name=self.operatorLabel.text().replace("Operator: ", "")
        )

        if dialog.exec_():
            new_name = dialog.get_value()

            if new_name:
                self.set_operator(new_name)

    def open_history(self):
        from history import HistoryDialog
        self.close()
        QTimer.singleShot(100, lambda: HistoryDialog(self.main_parent).exec_())

    def refresh_grade_summary(self):
        self.g1Label.setText(f"1 = {self.grade_counts['g1']}pcs")
        self.g2Label.setText(f"2 = {self.grade_counts['g2']}pcs")
        self.g3Label.setText(f"3 = {self.grade_counts['g3']}pcs")
        self.rejectLabel.setText(f"Rejects = {self.grade_counts['reject']}pcs")

        # 👇 NEW: update dominant grade
        dominant_grade = self.compute_dominant_grade()
        self.set_grade(dominant_grade)

    def set_batch(self, batch_text):
        self.batchLabel.setText(f"Batch: {batch_text}")
        self.refresh_receipt_preview()

    def set_recommendation(self, recommendation_text):
        if not recommendation_text.startswith("Recommendation:"):
            recommendation_text = f"Recommendation: {recommendation_text}"
        self.recommendationLabel.setText(recommendation_text)
        self.refresh_receipt_preview()

    def set_grade(self, grade_number, grade_tag=None):
        try:
            grade_number = int(grade_number)
        except:
            grade_number = 0

        # 🔥 Only allow 1,2,3 — everything else = REJECT
        if grade_number in (1, 2, 3):
            self.current_grade_number = grade_number

            if grade_tag is None:
                grade_tag = f"GRADE {chr(64 + grade_number)}"  # 1→A, 2→B, 3→C

            self.gradeNumber.setText(str(grade_number))
            self.gradeTag.setText(grade_tag)

        else:
            self.current_grade_number = 0  # or 4 if you prefer a reject code

            self.gradeNumber.setText("REJ")
            self.gradeTag.setText("REJECTED")

        self.refresh_receipt_preview()

    def set_operator(self, operator_name):
        from db_helper import ensure_operator_exists, get_operator_id, set_active_operator

        ensure_operator_exists(operator_name)
        operator_id = get_operator_id(operator_name)

        self.operatorLabel.setText(f"Operator: {operator_name}")
        self.current_operator_id = operator_id

        # 🔥 PERSIST ACTIVE OPERATOR
        set_active_operator(operator_id)

        # notify system
        self.operator_changed.emit(operator_id, operator_name)

    def set_date_time(self, date_text=None, time_text=None):
        if date_text:
            self.dateLabel.setText(f"Date: {date_text}")
        if time_text:
            self.timeLabel.setText(f"Time: {time_text}")
        self.refresh_receipt_preview()

    def set_grade_counts(self, g1=0, g2=0, g3=0, reject=0):
        self.grade_counts["g1"] = g1
        self.grade_counts["g2"] = g2
        self.grade_counts["g3"] = g3
        self.grade_counts["reject"] = reject
        self.refresh_grade_summary()
        self.refresh_receipt_preview()

    def get_current_operator_id(self):
        return self.current_operator_id

    def update_report_data(
        self,
        batch=None,
        recommendation=None,
        grade_number=None,
        grade_tag=None,
        operator=None,
        date_text=None,
        time_text=None,
        g1=None,
        g2=None,
        g3=None,
        reject=None
    ):
        if batch is not None:
            self.batchLabel.setText(f"Batch: {batch}")

        if recommendation is not None:
            recommendation_str = str(recommendation)
            if not recommendation_str.startswith("Recommendation:"):
                recommendation_str = f"Recommendation: {recommendation_str}"
            self.recommendationLabel.setText(recommendation_str)

        if grade_number is not None:
            self.gradeNumber.setText(str(grade_number))

        if grade_tag is not None:
            self.gradeTag.setText(str(grade_tag))

        if operator is not None:
            self.operatorLabel.setText(f"Operator: {operator}")

        if date_text is not None:
            self.dateLabel.setText(f"Date: {date_text}")

        if time_text is not None:
            self.timeLabel.setText(f"Time: {time_text}")

        if g1 is not None:
            self.grade_counts["g1"] = g1
        if g2 is not None:
            self.grade_counts["g2"] = g2
        if g3 is not None:
            self.grade_counts["g3"] = g3
        if reject is not None:
            self.grade_counts["reject"] = reject

        self.refresh_grade_summary()
        self.refresh_receipt_preview()

    def build_receipt_text(self):
        data = self.build_receipt_data()
        return generate_receipt(data)

    def normalize_receipt_data(self, raw: dict) -> dict:
        data = RECEIPT_SCHEMA.copy()

        if raw:
            data.update(raw)

        # 🔥 force-safe conversions
        try:
            data["grade"] = int(data.get("grade", 0))
        except:
            data["grade"] = 0

        try:
            data["avg_confidence"] = float(data.get("avg_confidence", 0))
        except:
            data["avg_confidence"] = 0

        return data

    def build_receipt_data(self):
            return self.normalize_receipt_data({
            "grade": getattr(self, "current_grade_number", 0),

            "avg_confidence": self.compute_avg_confidence(),

            "operator": self.operatorLabel.text().replace("Operator: ", "").strip() if hasattr(self, "operatorLabel") else "",

            "operator_id": getattr(self, "current_operator_id", None),

            "batch": self.batchLabel.text().replace("Batch: ", "").strip() if hasattr(self, "batchLabel") else "",

            "batch_id": getattr(self, "batch_id", None),

            "g1": self.grade_counts.get("g1", 0),
            "g2": self.grade_counts.get("g2", 0),
            "g3": self.grade_counts.get("g3", 0),
            "reject": self.grade_counts.get("reject", 0),

            "recommendation": self.recommendationLabel.text().replace("Recommendation:", "").strip()
            if hasattr(self, "recommendationLabel") else "",
        })

    def compute_avg_confidence(self):
        import sqlite3

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT AVG(confidence)
            FROM ImageData
            WHERE batch_id = ?
        """, (self.batch_id,))

        result = cursor.fetchone()[0]
        conn.close()

        return round(result or 0, 2)

    def refresh_receipt_preview(self):
        self.receiptText.setPlainText(self.build_receipt_text())

    def print_report(self):
        from db_helper import get_operator_id

        dlg = ConfirmOverlay("Do you want to print the receipt?", self)
        if not dlg.exec_():
            return

        # 🔥 SNAPSHOT EVERYTHING FIRST
        data = self.build_receipt_data()

        # lock operator id properly
        data["operator_id"] = get_operator_id(data["operator"])

        # print
        receipt_text = generate_receipt(data)
        print_to_usb(receipt_text)

        # 🔥 AFTER SUCCESS → rotate batch
        try:
            create_new_batch(data["operator_id"])
            from create_tables import get_active_batch
            self.batch_id = get_active_batch()
        except Exception as e:
            print("[PRINT ERROR] batch update failed:", e)

    def add_shadow(self):
        outer_shadow = QGraphicsDropShadowEffect(self)
        outer_shadow.setBlurRadius(28)
        outer_shadow.setOffset(0, 8)
        outer_shadow.setColor(QColor(65, 40, 18, 55))
        self.panel.setGraphicsEffect(outer_shadow)

    def apply_blur(self):
        if self.main_parent and self.main_parent.centralWidget():
            self.blur_effect = QGraphicsBlurEffect()
            self.blur_effect.setBlurRadius(14)
            self.main_parent.centralWidget().setGraphicsEffect(self.blur_effect)

    def remove_blur(self):
        if self.main_parent and self.main_parent.centralWidget():
            self.main_parent.centralWidget().setGraphicsEffect(None)
        self.blur_effect = None

    def showEvent(self, event):
        self.apply_blur()
        self.refresh_grade_summary()
        self.refresh_receipt_preview()
        super().showEvent(event)

    def closeEvent(self, event):
        self.remove_blur()
        super().closeEvent(event)

    def reject(self):
        self.remove_blur()
        super().reject()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: rgba(242, 235, 227, 120);
            }

            #OuterCard {
                background: #ece7e0;
                border: 1px solid #d4c6b6;
                border-radius: 18px;
            }

            #HeaderWrap {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7a552f,
                    stop:1 #6b4724
                );
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
                min-height: 38px;
                max-height: 38px;
            }

            #HeaderBar {
                color: #f8efdf;
                font-family: Georgia;
                font-size: 18px;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
            }

            #TopCloseBtn {
                color: #fff4e3;
                font-size: 22px;
                font-weight: 900;
                background: rgba(255,255,255,20);
                border: none;
                border-radius: 6px;
            }

            #TopCloseBtn:hover {
                background: rgba(255,255,255,35);
            }

            #InfoWrap {
                background: transparent;
                border-bottom: 1px solid #d8cdbf;
            }

            #TopInfo {
                color: #53341c;
                font-family: Georgia;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
            }

            #TopSep {
                color: #9c856c;
                font-size: 13px;
                background: transparent;
            }

            #MainWrap {
                background: transparent;
            }

            #LeftPanel {
                background: transparent;
            }

            #ResultCard {
                background: #f6f2ed;
                border: 2px solid #d6c8bb;
                border-radius: 10px;
            }

            #ResultTitle {
                color: #744925;
                font-family: Georgia;
                font-size: 24px;
                font-weight: 700;
                background: transparent;
                padding-left: 10px;
                padding-right: 10px;
            }

            #TitleLine {
                background: #d7cbc0;
                border: none;
            }

            #MainText {
                color: #55331b;
                font-family: Georgia;
                font-size: 22px;
                font-weight: 700;
                background: transparent;
            }

            #MainTextSoft {
                color: #55331b;
                font-family: Georgia;
                font-size: 19px;
                font-weight: 500;
                background: transparent;
            }

            #GradeGridWrap {
                background: transparent;
                border: none;
            }

            #GradeCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #9f6f39,
                    stop:1 #b88445
                );
                border: 2px solid #ad7f49;
                border-radius: 18px;
            }

            #GradeTag {
                color: #f9edd9;
                font-family: Georgia;
                font-size: 20px;
                font-weight: 700;
                background: rgba(115, 74, 32, 140);
                border: 2px solid #c69a61;
                border-radius: 10px;
                padding: 2px 12px;
                min-width: 120px;
                max-width: 145px;
            }

            #GradeNumber {
                color: #fff2dd;
                font-family: Georgia;
                font-size: 78px;
                font-weight: 700;
                background: transparent;
            }

            #ActionBtn {
                color: #f8ecd9;
                font-family: Georgia;
                font-size: 14px;
                font-weight: 700;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #815733,
                    stop:1 #694422
                );
                border: 1px solid #5d3918;
                border-radius: 6px;
                padding: 8px 14px;
            }

            #ActionBtn:hover {
                background: #7a522d;
            }

            #ActionBtn:pressed {
                background: #5e3c1f;
            }

            #ReceiptPanel {
                background: #f2f2f2;
                border: 1px solid #d4d4d4;
                border-radius: 12px;
            }

            #ReceiptLogo {
                font-size: 18px;
                color: #444444;
                background: transparent;
            }

            #ReceiptHeader {
                font-size: 13px;
                font-weight: 800;
                color: #333333;
                background: transparent;
            }

            #ReceiptSubHeader {
                font-size: 11px;
                font-weight: 700;
                color: #555555;
                background: transparent;
            }

            #ReceiptLine {
                color: #d0d0d0;
                background: #d0d0d0;
                min-height: 1px;
                max-height: 1px;
                border: none;
            }

            #ReceiptText {
                background: #f2f2f2;
                border: none;
                color: #222222;
                padding: 4px;
            }

            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #c6c6c6;
                border-radius: 4px;
                min-height: 20px;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QMessageBox {
                background-color: #f6f2ed;
            }

            QMessageBox QLabel {
                color: #55331b;
                font-size: 13px;
                font-weight: 700;
            }

            QMessageBox QPushButton {
                min-width: 80px;
                min-height: 30px;
                border-radius: 6px;
                background: #7a522d;
                color: white;
                border: none;
                padding: 4px 10px;
            }

            QMessageBox QPushButton:hover {
                background: #694422;
            }
            
            #TopEditBtn {
                background: rgba(120, 80, 40, 30);
                border: 1px solid #b89a7a;
                border-radius: 6px;
                color: #5a3820;
                font-weight: bold;
            }

            #TopEditBtn:hover {
                background: rgba(120, 80, 40, 50);
            }
        """)

    def set_receipt_data(self, data: dict):
        self.receipt_data = data

        self.update_report_data(
            batch=data.get("batch"),
            recommendation=data.get("recommendation"),
            grade_number=data.get("grade"),
            grade_tag=f"GRADE {chr(64 + data.get('grade', 0))}" if data.get("grade", 0) in (1,2,3) else "REJECT",
            operator=data.get("operator"),
            date_text=data.get("date"),
            time_text=data.get("time"),
            g1=data.get("g1"),
            g2=data.get("g2"),
            g3=data.get("g3"),
            reject=data.get("reject")
        )

    def compute_dominant_grade(self):
        counts = self.grade_counts

        grade_map = {
            "g1": counts["g1"],
            "g2": counts["g2"],
            "g3": counts["g3"],
            "reject": counts["reject"]  # 🔥 include rejects
        }

        dominant = max(grade_map, key=grade_map.get)

        # 🔥 Handle reject separately
        if dominant == "reject":
            return 0  # or 4, depending on your system

        return int(dominant[1])  # "g1" → 1

class ConfirmOverlay(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)

        self.result = False
        self.loop = QEventLoop()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setGeometry(parent.geometry())

        # 🔥 Dark glass background
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 140);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # 📦 Main card
        box = QWidget()
        box.setFixedWidth(320)
        box.setStyleSheet("""
            QWidget {
                background: #f6f2ed;
                border: 2px solid #d4c6b6;
                border-radius: 16px;
            }
        """)

        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(20, 18, 20, 18)
        box_layout.setSpacing(14)

        # 🏷️ Title
        title = QLabel("Confirm Action")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #6b4724;
            font-family: Georgia;
            font-size: 16px;
            font-weight: 700;
        """)

        # 💬 Message
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("""
            color: #55331b;
            font-family: Georgia;
            font-size: 13px;
            font-weight: 600;
        """)

        # 🔘 Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_yes = QPushButton("Yes")
        btn_yes.setCursor(Qt.PointingHandCursor)
        btn_yes.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #815733,
                    stop:1 #694422
                );
                color: #f8ecd9;
                border: 1px solid #5d3918;
                border-radius: 8px;
                padding: 6px 14px;
                font-family: Georgia;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #7a522d;
            }
            QPushButton:pressed {
                background: #5e3c1f;
            }
        """)

        btn_no = QPushButton("No")
        btn_no.setCursor(Qt.PointingHandCursor)
        btn_no.setStyleSheet("""
            QPushButton {
                background: #e8ded3;
                color: #55331b;
                border: 1px solid #cbb9a6;
                border-radius: 8px;
                padding: 6px 14px;
                font-family: Georgia;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #ddd0c2;
            }
        """)

        btn_row.addWidget(btn_no)
        btn_row.addWidget(btn_yes)

        # 🧩 Assemble
        box_layout.addWidget(title)
        box_layout.addWidget(label)
        box_layout.addLayout(btn_row)

        layout.addWidget(box)

        # 🎯 Actions (unchanged logic)
        btn_yes.clicked.connect(lambda: self.finish(True))
        btn_no.clicked.connect(lambda: self.finish(False))
    def finish(self, value):
        self.result = value
        self.loop.quit()
        self.close()

    def mousePressEvent(self, event):
        self.finish(False)

    def exec_(self):
        self.show()
        self.loop.exec_()
        return self.result


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = ReportDialog()
    w.update_report_data(
        batch="BCH-2026-001",
        recommendation="Ready for storage and selling",
        grade_number=1,
        grade_tag="GRADE",
        operator="John D.",
        date_text="Mar 14, 2026",
        time_text="10:42 AM",
        g1=20,
        g2=30,
        g3=20,
        reject=10
    )
    w.show()
    sys.exit(app.exec_())