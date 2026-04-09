from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QTextDocument, QFont
from PyQt5.QtWidgets import (
    QDialog, QWidget, QFrame, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QSizePolicy,
    QGraphicsDropShadowEffect, QGraphicsBlurEffect,
    QTextEdit
)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from datetime import datetime


class MoistureBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(170, 16)
        self.setMaximumHeight(16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0.00 #95a34a,
                    stop:0.18 #b3bc59,
                    stop:0.36 #cdbf62,
                    stop:0.58 #d4a54f,
                    stop:0.78 #bf7835,
                    stop:1.00 #8e4f21
                );
                border: 1px solid #6f4b2a;
                border-radius: 4px;
            }
        """)


class ReceiptDialog(QDialog):
    def __init__(self, receipt_text, parent=None):
        super().__init__(parent)
        self.receipt_text = receipt_text
        self.main_parent = parent
        self.blur_effect = None

        self.setModal(True)
        self.setFixedSize(300, 650)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self.card = QFrame()
        self.card.setObjectName("ReceiptCard")
        outer.addWidget(self.card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.card.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.logoLabel = QLabel("🧾")
        self.logoLabel.setAlignment(Qt.AlignCenter)
        self.logoLabel.setObjectName("ReceiptLogo")
        root.addWidget(self.logoLabel)

        self.headerLabel = QLabel("COPRA QUALITY ANALYSIS")
        self.headerLabel.setAlignment(Qt.AlignCenter)
        self.headerLabel.setObjectName("ReceiptHeader")
        root.addWidget(self.headerLabel)

        self.subHeaderLabel = QLabel("SYSTEM RECEIPT")
        self.subHeaderLabel.setAlignment(Qt.AlignCenter)
        self.subHeaderLabel.setObjectName("ReceiptSubHeader")
        root.addWidget(self.subHeaderLabel)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("ReceiptLine")
        root.addWidget(line)

        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName("ReceiptText")
        self.textEdit.setPlainText(receipt_text)
        self.textEdit.setFont(QFont("Courier New", 9))
        root.addWidget(self.textEdit, 1)

        btnRow = QHBoxLayout()
        btnRow.setSpacing(8)

        self.printBtn = QPushButton("Print")
        self.printBtn.setObjectName("ReceiptBtn")
        self.printBtn.clicked.connect(self.handle_print)

        self.closeBtn = QPushButton("Close")
        self.closeBtn.setObjectName("ReceiptBtn")
        self.closeBtn.clicked.connect(self.close)

        btnRow.addWidget(self.printBtn)
        btnRow.addWidget(self.closeBtn)
        root.addLayout(btnRow)

        self.setStyleSheet("""
            QDialog {
                background: rgba(0, 0, 0, 150);
            }

            #ReceiptCard {
                background: #ffffff;
                border-radius: 10px;
                border: 1px solid #d8d8d8;
            }

            #ReceiptLogo {
                font-size: 20px;
                color: #111111;
                background: transparent;
            }

            #ReceiptHeader {
                font-size: 13px;
                font-weight: 800;
                color: #111111;
                background: transparent;
            }

            #ReceiptSubHeader {
                font-size: 11px;
                font-weight: 700;
                color: #333333;
                background: transparent;
            }

            #ReceiptLine {
                color: #cfcfcf;
                background: #cfcfcf;
                min-height: 1px;
                max-height: 1px;
                border: none;
            }

            #ReceiptText {
                background: #ffffff;
                border: none;
                color: #111111;
                padding: 4px;
            }

            #ReceiptBtn {
                background: #f3f3f3;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 7px;
                font-size: 11px;
                font-weight: 600;
                color: #111111;
            }

            #ReceiptBtn:hover {
                background: #e8e8e8;
            }

            #ReceiptBtn:pressed {
                background: #dddddd;
            }
        """)

    def apply_blur(self):
        if self.main_parent and hasattr(self.main_parent, "panel") and self.main_parent.panel:
            self.blur_effect = QGraphicsBlurEffect()
            self.blur_effect.setBlurRadius(12)
            self.main_parent.panel.setGraphicsEffect(self.blur_effect)

    def remove_blur(self):
        if self.main_parent and hasattr(self.main_parent, "panel") and self.main_parent.panel:
            self.main_parent.panel.setGraphicsEffect(None)
        self.blur_effect = None

    def showEvent(self, event):
        self.apply_blur()
        super().showEvent(event)

    def closeEvent(self, event):
        self.remove_blur()
        super().closeEvent(event)

    def reject(self):
        self.remove_blur()
        super().reject()

    def mousePressEvent(self, event):
        if not self.card.geometry().contains(event.pos()):
            self.close()
        super().mousePressEvent(event)

    def handle_print(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageMargins(2, 2, 2, 2, QPrinter.Millimeter)

        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QDialog.Accepted:
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Courier New", 9))
            html = f"""
            <html>
                <body style="
                    font-family: 'Courier New', monospace;
                    font-size: 9pt;
                    white-space: pre;
                    margin: 2px;
                    color: black;
                ">{self.receipt_text}</body>
            </html>
            """
            doc.setHtml(html)
            doc.print_(printer)


class ReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_parent = parent
        self.blur_effect = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1280, 820)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.panel = QFrame()
        self.panel.setObjectName("OuterCard")
        panelLay = QVBoxLayout(self.panel)
        panelLay.setContentsMargins(0, 0, 0, 14)
        panelLay.setSpacing(0)

        # HEADER
        headerWrap = QFrame()
        headerWrap.setObjectName("HeaderWrap")
        headerLay = QHBoxLayout(headerWrap)
        headerLay.setContentsMargins(18, 0, 12, 0)
        headerLay.setSpacing(10)

        self.header = QLabel("COPRA GRADING MACHINE")
        self.header.setObjectName("HeaderBar")
        self.header.setAlignment(Qt.AlignCenter)

        self.closeBtn = QPushButton("×")
        self.closeBtn.setObjectName("TopCloseBtn")
        self.closeBtn.setFixedSize(40, 40)
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
        infoLay.setContentsMargins(18, 10, 18, 8)
        infoLay.setSpacing(10)

        self.dateLabel = QLabel("Date: Mar 14, 2026")
        self.timeLabel = QLabel("Time: 10:42 AM")
        self.operatorLabel = QLabel("Operator: John D.")

        for lbl in (self.dateLabel, self.timeLabel, self.operatorLabel):
            lbl.setObjectName("TopInfo")

        sep = QLabel("|")
        sep.setObjectName("TopSep")

        infoLay.addWidget(self.dateLabel)
        infoLay.addWidget(sep)
        infoLay.addWidget(self.timeLabel)
        infoLay.addStretch(1)
        infoLay.addWidget(self.operatorLabel)

        panelLay.addWidget(infoWrap)

        # BODY
        bodyWrap = QFrame()
        bodyWrap.setObjectName("BodyArea")
        bodyLay = QVBoxLayout(bodyWrap)
        bodyLay.setContentsMargins(14, 8, 14, 0)
        bodyLay.setSpacing(12)
        panelLay.addWidget(bodyWrap, 1)

        # RESULT CARD
        self.resultCard = QFrame()
        self.resultCard.setObjectName("ResultCard")
        self.resultCard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card = QVBoxLayout(self.resultCard)
        card.setContentsMargins(24, 16, 24, 20)
        card.setSpacing(16)
        bodyLay.addWidget(self.resultCard, 1)

        # TITLE
        titleRow = QHBoxLayout()
        titleRow.setSpacing(16)

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

        # MAIN CONTENT
        contentRow = QHBoxLayout()
        contentRow.setSpacing(40)
        card.addLayout(contentRow, 1)

        # LEFT SIDE
        leftCol = QVBoxLayout()
        leftCol.setSpacing(16)
        contentRow.addLayout(leftCol, 5)

        leftCol.addStretch(1)

        self.batchLabel = QLabel("Batch: BCH-2026-001")
        self.batchLabel.setObjectName("MainText")
        leftCol.addWidget(self.batchLabel)

        scoreRow = QHBoxLayout()
        scoreRow.setSpacing(8)
        scoreText = QLabel("Quality Score:")
        scoreText.setObjectName("MainText")
        self.scoreValue = QLabel("89 / 100")
        self.scoreValue.setObjectName("BoldValue")
        scoreRow.addWidget(scoreText)
        scoreRow.addWidget(self.scoreValue)
        scoreRow.addStretch(1)
        leftCol.addLayout(scoreRow)

        moistureRow = QHBoxLayout()
        moistureRow.setSpacing(10)
        moistureText = QLabel("Moisture Level:")
        moistureText.setObjectName("MainText")
        self.moistureValue = QLabel("12.4%")
        self.moistureValue.setObjectName("MainText")
        self.moistureBar = MoistureBar()
        moistureRow.addWidget(moistureText, 0)
        moistureRow.addWidget(self.moistureValue, 0)
        moistureRow.addWidget(self.moistureBar, 1)
        leftCol.addLayout(moistureRow)

        statusRow = QHBoxLayout()
        statusRow.setSpacing(8)
        statusText = QLabel("Status:")
        statusText.setObjectName("MainText")
        self.statusValue = QLabel("✔ PASSED")
        self.statusValue.setObjectName("StatusPass")
        statusRow.addWidget(statusText)
        statusRow.addWidget(self.statusValue)
        statusRow.addStretch(1)
        leftCol.addLayout(statusRow)

        self.recommendationLabel = QLabel("Recommendation: Ready for storage and selling")
        self.recommendationLabel.setObjectName("MainText")
        self.recommendationLabel.setWordWrap(True)
        leftCol.addWidget(self.recommendationLabel)

        leftCol.addStretch(1)

        # RIGHT SIDE
        rightCol = QVBoxLayout()
        rightCol.setSpacing(0)
        contentRow.addLayout(rightCol, 4)

        rightCol.addStretch(1)

        self.gradeCard = QFrame()
        self.gradeCard.setObjectName("GradeCard")
        self.gradeCard.setMinimumSize(280, 185)
        self.gradeCard.setMaximumSize(320, 210)
        self.gradeCard.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        gradeLay = QVBoxLayout(self.gradeCard)
        gradeLay.setContentsMargins(18, 16, 18, 16)
        gradeLay.setSpacing(8)

        self.gradeTag = QLabel("GRADE A")
        self.gradeTag.setObjectName("GradeTag")
        self.gradeTag.setAlignment(Qt.AlignCenter)
        self.gradeTag.setFixedHeight(46)

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
        btnRow.setSpacing(12)
        btnRow.setContentsMargins(0, 10, 0, 0)
        bodyLay.addLayout(btnRow)

        self.printBtn = QPushButton(" Print Receipt")
        self.scanBtn = QPushButton(" New Scan")
        self.historyBtn = QPushButton(" View History")

        for btn in (self.printBtn, self.scanBtn, self.historyBtn):
            btn.setObjectName("ActionBtn")
            btn.setMinimumHeight(42)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btnRow.addWidget(btn)

        root.addWidget(self.panel)

        self.apply_styles()
        self.add_shadow()
        self.setup_connections()

    def setup_connections(self):
        self.scanBtn.clicked.connect(self.close)
        self.historyBtn.clicked.connect(self.open_history)
        self.printBtn.clicked.connect(self.print_report)

    def open_history(self):
        from history import HistoryDialog
        self.close()
        QTimer.singleShot(100, lambda: HistoryDialog(self.main_parent).exec_())

    def build_receipt_text(self):
        now = datetime.now()

        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%H:%M:%S")

        operator_text = self.operatorLabel.text().replace("Operator:", "").strip()
        batch_text = self.batchLabel.text().replace("Batch:", "").strip()

        batch_no = batch_text
        if "-" in batch_text:
            try:
                batch_no = str(int(batch_text.split("-")[-1]))
            except:
                batch_no = batch_text

        grade_num = self.gradeNumber.text().strip()
        grade_text = f"Grade {grade_num}"

        score_text = self.scoreValue.text().split("/")[0].strip()
        try:
            confidence_text = f"{float(score_text):.1f}%"
        except:
            confidence_text = score_text

        moisture_raw = self.moistureValue.text().replace("%", "").strip()
        moisture_1 = moisture_raw
        moisture_2 = moisture_raw

        raw_status = self.statusValue.text().strip().upper()
        status_text = "Accepted" if "PASS" in raw_status else "Rejected"

        recommendation_raw = self.recommendationLabel.text().replace("Recommendation:", "").strip()

        cooking_time = recommendation_raw
        if "min" not in recommendation_raw.lower():
            if grade_num == "1":
                cooking_time = "45-50 min"
            elif grade_num == "2":
                cooking_time = "50-55 min"
            elif grade_num == "3":
                cooking_time = "55-60 min"
            else:
                cooking_time = "Not recommended"

        line = "-" * 32
        top = "=" * 32

        receipt_text = (
            f"{top}\n"
            f"   COPRA QUALITY ANALYSIS\n"
            f"        SYSTEM RECEIPT\n"
            f"{top}\n"
            f"Date: {date_text}\n"
            f"Operator: {operator_text}\n"
            f"\n"
            f"Time: {time_text}\n"
            f"{line}\n"
            f"Batch No: {batch_no}\n"
            f"Grade: {grade_text}\n"
            f"Confidence: {confidence_text}\n"
            f"{line}\n"
            f"Moisture Readings:\n"
            f"  Sensor 1: {moisture_1}%\n"
            f"  Sensor 2: {moisture_2}%\n"
            f"{line}\n"
            f"Status: {status_text}\n"
            f"Recommendation:\n"
            f"  Cooking Time: {cooking_time}\n"
            f"{line}\n"
            f"         Thank you!\n"
            f"{top}"
        )
        return receipt_text

    def print_report(self):
        receipt_text = self.build_receipt_text()
        dialog = ReceiptDialog(receipt_text, self)
        dialog.exec_()

    def add_shadow(self):
        outer_shadow = QGraphicsDropShadowEffect(self)
        outer_shadow.setBlurRadius(36)
        outer_shadow.setOffset(0, 10)
        outer_shadow.setColor(QColor(65, 40, 18, 60))
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
        super().showEvent(event)

    def closeEvent(self, event):
        self.remove_blur()
        super().closeEvent(event)

    def reject(self):
        self.remove_blur()
        super().reject()

    def mousePressEvent(self, event):
        if not self.panel.geometry().contains(event.pos()):
            self.close()
        super().mousePressEvent(event)

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: rgba(242, 235, 227, 120);
            }

            #OuterCard {
                background: #f3ebe2;
                border: 1px solid #d8c8b9;
                border-radius: 18px;
            }

            #HeaderWrap {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #805834,
                    stop:1 #6c4827
                );
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
                min-height: 44px;
                max-height: 44px;
            }

            #HeaderBar {
                color: #f8efdf;
                font-family: Georgia;
                font-size: 22px;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
            }

            #TopCloseBtn {
                color: #fff4e3;
                font-size: 24px;
                font-weight: 900;
                background: transparent;
                border: none;
                border-radius: 8px;
            }

            #TopCloseBtn:pressed {
                background: rgba(255, 255, 255, 30);
            }

            #InfoWrap {
                background: transparent;
            }

            #TopInfo {
                color: #4c2e18;
                font-family: Georgia;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }

            #TopSep {
                color: #baa18b;
                font-size: 14px;
                background: transparent;
            }

            #BodyArea {
                background: transparent;
            }

            #ResultCard {
                background: #f8f3ed;
                border: 2px solid #d7c8bb;
                border-radius: 10px;
            }

            #ResultTitle {
                color: #6a3e1d;
                font-family: Georgia;
                font-size: 28px;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
                padding-left: 10px;
                padding-right: 10px;
            }

            #TitleLine {
                background: #d9cabd;
                border: none;
            }

            #MainText {
                color: #4d2b15;
                font-family: Georgia;
                font-size: 20px;
                font-weight: 600;
                background: transparent;
            }

            #BoldValue {
                color: #4d2b15;
                font-family: Georgia;
                font-size: 20px;
                font-weight: 700;
                background: transparent;
            }

            #StatusPass {
                color: #6b641f;
                font-family: Georgia;
                font-size: 20px;
                font-weight: 700;
                background: transparent;
            }

            #GradeCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #805126,
                    stop:0.45 #b07a42,
                    stop:1 #8b5929
                );
                border: 2px solid #a97a49;
                border-radius: 20px;
            }

            #GradeTag {
                color: #f9edd9;
                font-family: Georgia;
                font-size: 22px;
                font-weight: 700;
                letter-spacing: 1px;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #86572d,
                    stop:1 #714921
                );
                border: 2px solid #bf9463;
                border-radius: 11px;
                padding: 2px 16px;
                min-width: 135px;
                max-width: 165px;
            }

            #GradeNumber {
                color: #fff2dd;
                font-family: Georgia;
                font-size: 88px;
                font-weight: 700;
                background: transparent;
            }

            #ActionBtn {
                color: #f8ecd9;
                font-family: Georgia;
                font-size: 15px;
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

            #ActionBtn:pressed {
                background: #5e3c1f;
            }
        """)