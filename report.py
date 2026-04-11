from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QTextDocument, QFont
from PyQt5.QtWidgets import (
    QDialog, QWidget, QFrame, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QSizePolicy,
    QGraphicsDropShadowEffect, QGraphicsBlurEffect,
    QTextEdit, QMessageBox, QScrollArea, QGridLayout
)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from datetime import datetime


class ReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_parent = parent
        self.blur_effect = None

        self.grade_counts = {
            "g1": 20,
            "g2": 30,
            "g3": 20,
            "reject": 10
        }

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

        sep = QLabel("|")
        sep.setObjectName("TopSep")

        infoLay.addWidget(self.dateLabel)
        infoLay.addWidget(sep)
        infoLay.addWidget(self.timeLabel)
        infoLay.addStretch(1)
        infoLay.addWidget(self.operatorLabel, 0, Qt.AlignRight | Qt.AlignVCenter)

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

        self.gradeTag = QLabel("GRADE A")
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
        self.refresh_receipt_preview()

    def setup_connections(self):
        self.scanBtn.clicked.connect(self.close)
        self.historyBtn.clicked.connect(self.open_history)
        self.printBtn.clicked.connect(self.print_report)

    def open_history(self):
        from history import HistoryDialog
        self.close()
        QTimer.singleShot(100, lambda: HistoryDialog(self.main_parent).exec_())

    def refresh_grade_summary(self):
        self.g1Label.setText(f"1 = {self.grade_counts['g1']}pcs")
        self.g2Label.setText(f"2 = {self.grade_counts['g2']}pcs")
        self.g3Label.setText(f"3 = {self.grade_counts['g3']}pcs")
        self.rejectLabel.setText(f"Rejects = {self.grade_counts['reject']}pcs")

    def set_batch(self, batch_text):
        self.batchLabel.setText(f"Batch: {batch_text}")
        self.refresh_receipt_preview()

    def set_recommendation(self, recommendation_text):
        if not recommendation_text.startswith("Recommendation:"):
            recommendation_text = f"Recommendation: {recommendation_text}"
        self.recommendationLabel.setText(recommendation_text)
        self.refresh_receipt_preview()

    def set_grade(self, grade_number, grade_tag=None):
        self.gradeNumber.setText(str(grade_number))
        if grade_tag is None:
            grade_tag = f"GRADE {chr(64 + int(grade_number))}" if str(grade_number).isdigit() and 1 <= int(grade_number) <= 26 else "GRADE"
        self.gradeTag.setText(grade_tag)
        self.refresh_receipt_preview()

    def set_operator(self, operator_name):
        self.operatorLabel.setText(f"Operator: {operator_name}")
        self.refresh_receipt_preview()

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
        now = datetime.now()

        date_label_text = self.dateLabel.text().replace("Date:", "").strip()
        time_label_text = self.timeLabel.text().replace("Time:", "").strip()

        date_text = now.strftime("%Y-%m-%d") if not date_label_text else date_label_text
        time_text = now.strftime("%H:%M:%S") if not time_label_text else time_label_text

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

        confidence_map = {
            "1": "89.0%",
            "2": "80.0%",
            "3": "70.0%"
        }
        confidence_text = confidence_map.get(grade_num, "0.0%")

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
            f"  Sensor 1: 12.4%\n"
            f"  Sensor 2: 12.4%\n"
            f"{line}\n"
            f"Status: Accepted\n"
            f"Recommendation:\n"
            f"  Cooking Time: 45-50 min\n"
            f"{line}\n"
            f"         Thank you!\n"
            f"{top}"
        )
        return receipt_text

    def refresh_receipt_preview(self):
        self.receiptText.setPlainText(self.build_receipt_text())

    def print_report(self):
        self.refresh_receipt_preview()

        reply = QMessageBox.question(
            self,
            "Print Receipt",
            "Do you want to print the receipt?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

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
                ">{self.build_receipt_text()}</body>
            </html>
            """
            doc.setHtml(html)
            doc.print_(printer)

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
        """)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = ReportDialog()
    w.update_report_data(
        batch="BCH-2026-001",
        recommendation="Ready for storage and selling",
        grade_number="1",
        grade_tag="GRADE A",
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