import sys
import cv2

from PyQt5.QtCore import (
    Qt, QTimer, QDateTime, QRectF,
    QPropertyAnimation, QEasingCurve, pyqtProperty
)
from PyQt5.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QFont
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect
)

from history import HistoryDialog


PREVIEW_W = 470
PREVIEW_H = 570
CAM_FPS_MS = 30
AI_READ_INTERVAL_MS = 120_000
AI_FIRST_READ_DELAY_MS = 600
POWER_HOLD_MS = 3000


class ConfidenceGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._value = 40.0
        self._segments = 10
        self._gap_deg = 2.5
        self._start_deg = 90.0
        self._span_deg = 360.0

        self._seg_on = QColor("#8a5921")
        self._seg_off = QColor("#ece8e2")
        self._value_color = QColor("#6b3d10")

        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.setFixedSize(230, 230)

    def stop_animation(self):
        if self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()

    def set_target(self, percent: float):
        percent = max(0.0, min(100.0, float(percent)))
        self.stop_animation()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(percent)
        self._anim.start()

    def get_value(self):
        return float(self._value)

    def set_value(self, v):
        self._value = max(0.0, min(100.0, float(v)))
        self.update()

    value = pyqtProperty(float, fget=get_value, fset=set_value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        side = min(self.width(), self.height())
        pad = 18
        ring_th = 34

        rect = QRectF(
            (self.width() - side) / 2 + pad,
            (self.height() - side) / 2 + pad,
            side - 2 * pad,
            side - 2 * pad
        )

        seg_span = self._span_deg / self._segments
        on_segments = int(round((self._value / 100.0) * self._segments))

        pen_off = QPen(self._seg_off)
        pen_off.setWidth(ring_th)
        pen_off.setCapStyle(Qt.FlatCap)

        pen_on = QPen(self._seg_on)
        pen_on.setWidth(ring_th)
        pen_on.setCapStyle(Qt.FlatCap)

        for i in range(self._segments):
            start = self._start_deg + i * seg_span
            span = seg_span - self._gap_deg
            p.setPen(pen_on if i < on_segments else pen_off)
            p.drawArc(rect, int(start * 16), int(-span * 16))

        p.setPen(self._value_color)
        f = QFont("Arial", 26)
        f.setBold(True)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, f"{int(self._value)}%")


class SoftPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SoftPanel")


class BrownHeader(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("BrownHeader")
        self.setAlignment(Qt.AlignCenter)


class CreamHeader(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("CreamHeader")
        self.setAlignment(Qt.AlignCenter)


class OverlayPage(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("OverlayPage")
        self.setVisible(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.dialog = QFrame(self)
        self.dialog.setObjectName("OverlayDialog")
        dialogLay = QVBoxLayout(self.dialog)
        dialogLay.setContentsMargins(18, 16, 18, 16)
        dialogLay.setSpacing(12)

        header = QHBoxLayout()
        self.titleLabel = QLabel(title)
        self.titleLabel.setObjectName("OverlayTitle")

        self.closeBtn = QPushButton("✕")
        self.closeBtn.setObjectName("OverlayClose")
        self.closeBtn.setFixedSize(38, 38)

        header.addWidget(self.titleLabel, 1)
        header.addWidget(self.closeBtn, 0, Qt.AlignRight)

        self.body = QLabel("Content goes here…")
        self.body.setObjectName("OverlayBody")
        self.body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.body.setWordWrap(True)

        dialogLay.addLayout(header)
        dialogLay.addWidget(self.body, 1)

        root.addStretch(1)
        root.addWidget(self.dialog, 0, Qt.AlignHCenter)
        root.addStretch(1)

    def show_overlay(self):
        self.setVisible(True)
        self.raise_()

    def hide_overlay(self):
        self.setVisible(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle("Copra Quality Analysis System")

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_W)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_H)

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_frame)

        self.is_running = False
        self.last_frame = None

        self.ai_timer = QTimer(self)
        self.ai_timer.setInterval(AI_READ_INTERVAL_MS)
        self.ai_timer.timeout.connect(self.do_ai_read)

        self.powerHoldTimer = QTimer(self)
        self.powerHoldTimer.setSingleShot(True)
        self.powerHoldTimer.timeout.connect(self.close)

        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        headerWrap = QFrame()
        headerWrap.setObjectName("HeaderWrap")
        headerLay = QVBoxLayout(headerWrap)
        headerLay.setContentsMargins(20, 14, 20, 14)

        self.titleLabel = QLabel("COPRA QUALITY ANALYSIS SYSTEM")
        self.titleLabel.setObjectName("HeaderTitle")
        self.titleLabel.setAlignment(Qt.AlignCenter)
        headerLay.addWidget(self.titleLabel)
        outer.addWidget(headerWrap)

        bodyWrap = QFrame()
        bodyWrap.setObjectName("BodyWrap")
        bodyLay = QHBoxLayout(bodyWrap)
        bodyLay.setContentsMargins(20, 18, 20, 18)
        bodyLay.setSpacing(16)

        # LEFT
        leftPanel = SoftPanel()
        leftPanel.setMinimumWidth(500)
        leftLay = QVBoxLayout(leftPanel)
        leftLay.setContentsMargins(18, 18, 18, 18)
        leftLay.setSpacing(0)

        self.previewLabel = QLabel("Tap START to show camera")
        self.previewLabel.setObjectName("Preview")
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setFixedSize(PREVIEW_W, PREVIEW_H)
        self.previewLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.previewLabel.setScaledContents(False)
        leftLay.addWidget(self.previewLabel, 0, Qt.AlignCenter)

        # CENTER - adjusted professionally
        centerPanel = SoftPanel()
        centerPanel.setMinimumWidth(400)
        centerLay = QVBoxLayout(centerPanel)
        centerLay.setContentsMargins(12, 12, 12, 12)
        centerLay.setSpacing(6)

        analysisHeader = QLabel("AI ANALYSIS RESULT:")
        analysisHeader.setObjectName("MidTopStrip")
        analysisHeader.setAlignment(Qt.AlignCenter)
        analysisHeader.setFixedHeight(40)
        centerLay.addWidget(analysisHeader)

        centerLay.addSpacing(8)

        gradeTitle = QLabel("GRADE")
        gradeTitle.setObjectName("MidGradeTitle")
        gradeTitle.setAlignment(Qt.AlignCenter)
        gradeTitle.setFixedHeight(28)
        centerLay.addWidget(gradeTitle)

        centerLay.addSpacing(4)

        gradeWrap = QFrame()
        gradeWrap.setObjectName("MidGradeWrap")
        gradeWrapLay = QHBoxLayout(gradeWrap)
        gradeWrapLay.setContentsMargins(20, 0, 20, 0)
        gradeWrapLay.setSpacing(0)

        self.gradeValue = QLabel("GRADE 1")
        self.gradeValue.setObjectName("MidGradeBig")
        self.gradeValue.setAlignment(Qt.AlignCenter)
        self.gradeValue.setFixedHeight(56)
        gradeWrapLay.addWidget(self.gradeValue)

        centerLay.addWidget(gradeWrap)

        centerLay.addSpacing(14)

        confTitle = QLabel("CONFIDENCE LEVEL:")
        confTitle.setObjectName("MidConfidenceTitle")
        confTitle.setAlignment(Qt.AlignCenter)
        confTitle.setFixedHeight(30)
        centerLay.addWidget(confTitle)

        centerLay.addSpacing(8)

        self.confGauge = ConfidenceGauge(self)
        centerLay.addWidget(self.confGauge, 0, Qt.AlignCenter)

        centerLay.addSpacing(14)

        self.colorNote = QLabel("Clean and White to Pale Color")
        self.colorNote.setObjectName("MidBottomNote")
        self.colorNote.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.colorNote.setFixedHeight(54)
        centerLay.addWidget(self.colorNote)

        # RIGHT
        rightCol = QVBoxLayout()
        rightCol.setSpacing(12)
        rightCol.setContentsMargins(0, 0, 0, 0)

        batchPanel = SoftPanel()
        batchPanel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        batchLay = QVBoxLayout(batchPanel)
        batchLay.setContentsMargins(8, 8, 8, 10)
        batchLay.setSpacing(8)

        batchHead = BrownHeader("BATCH COUNT")
        batchHead.setFixedHeight(48)
        batchLay.addWidget(batchHead)

        self.batchLabel = QLabel("BATCH 1: 26 COPRA")
        self.batchLabel.setObjectName("BatchValueText")
        self.batchLabel.setAlignment(Qt.AlignCenter)
        batchLay.addWidget(self.batchLabel)
        batchLay.addStretch(1)

        sensorPanel = SoftPanel()
        sensorPanel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sensorLay = QVBoxLayout(sensorPanel)
        sensorLay.setContentsMargins(8, 8, 8, 8)
        sensorLay.setSpacing(8)

        sensorHead = CreamHeader("SENSOR READING")
        sensorHead.setFixedHeight(48)
        sensorLay.addWidget(sensorHead)

        self.copraStatus = QLabel("COPRA STATUS: WET")
        self.copraStatus.setObjectName("SensorStatusText")
        self.copraStatus.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        sensorLay.addWidget(self.copraStatus)

        moistureBox = QFrame()
        moistureBox.setObjectName("MoistureBox")
        moistureLay = QHBoxLayout(moistureBox)
        moistureLay.setContentsMargins(16, 8, 16, 8)
        moistureLay.setSpacing(8)

        self.moistureLabelTitle = QLabel("MOISTURE LEVEL:")
        self.moistureLabelTitle.setObjectName("MoistureTitle")

        self.moistureValue = QLabel("12%")
        self.moistureValue.setObjectName("MoistureValue")
        self.moistureValue.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        moistureLay.addWidget(self.moistureLabelTitle, 1)
        moistureLay.addWidget(self.moistureValue, 0)

        sensorLay.addWidget(moistureBox)
        sensorLay.addStretch(1)

        recoPanel = SoftPanel()
        recoPanel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        recoLay = QVBoxLayout(recoPanel)
        recoLay.setContentsMargins(8, 8, 8, 10)
        recoLay.setSpacing(8)

        recoHead = BrownHeader("RECOMMENDATION")
        recoHead.setFixedHeight(48)
        recoLay.addWidget(recoHead)

        self.recommendation = QLabel("✔ PASSED: READY TO SELL")
        self.recommendation.setObjectName("RecoValueText")
        self.recommendation.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        recoLay.addWidget(self.recommendation)
        recoLay.addStretch(1)

        rightCol.addWidget(batchPanel, 2)
        rightCol.addWidget(sensorPanel, 4)
        rightCol.addWidget(recoPanel, 2)

        bodyLay.addWidget(leftPanel, 5)
        bodyLay.addWidget(centerPanel, 4)
        bodyLay.addLayout(rightCol, 5)
        outer.addWidget(bodyWrap, 1)

        bottomWrap = QFrame()
        bottomWrap.setObjectName("BottomWrap")
        bottomLay = QHBoxLayout(bottomWrap)
        bottomLay.setContentsMargins(12, 12, 12, 14)
        bottomLay.setSpacing(16)

        self.historyBtn = QPushButton("HISTORY")
        self.historyBtn.setObjectName("FooterLightBtn")
        self.historyBtn.setMinimumHeight(74)

        self.mainBtn = QPushButton("START")
        self.mainBtn.setObjectName("FooterMainBtn")
        self.mainBtn.setMinimumHeight(84)

        self.reportBtn = QPushButton("RECEIPT")
        self.reportBtn.setObjectName("FooterLightBtn")
        self.reportBtn.setMinimumHeight(74)

        self.powerBtn = QPushButton("⏻")
        self.powerBtn.setObjectName("PowerBtn")
        self.powerBtn.setFixedSize(74, 74)
        self.powerBtn.setCheckable(True)

        bottomLay.addWidget(self.historyBtn, 3)
        bottomLay.addWidget(self.mainBtn, 5)
        bottomLay.addWidget(self.reportBtn, 3)
        bottomLay.addWidget(self.powerBtn, 0)
        outer.addWidget(bottomWrap)

        self.reportOverlay = OverlayPage("  RECEIPT", central)
        self.reportOverlay.body.setText(
            "• Generate receipt here\n"
            "• Export PDF\n"
            "• Print summary per batch"
        )
        self.reportOverlay.closeBtn.clicked.connect(self.reportOverlay.hide_overlay)

        self.mainBtn.clicked.connect(self.toggle_system)
        self.historyBtn.clicked.connect(self.open_history)
        self.reportBtn.clicked.connect(self.open_report)

        self.powerBtn.pressed.connect(self.start_power_hold)
        self.powerBtn.released.connect(self.cancel_power_hold)

        self.clock = QTimer(self)
        self.clock.timeout.connect(self.update_datetime)
        self.clock.start(500)
        self.update_datetime()

        self.apply_styles()
        self.add_shadows()
        self._resize_overlays()

        if not self.cap.isOpened():
            self.previewLabel.setText("No camera detected.\nCheck webcam / permissions.")
            self.previewLabel.setAlignment(Qt.AlignCenter)

    def mouseDoubleClickEvent(self, event):
        corner_size = 120
        if event.pos().x() > self.width() - corner_size and event.pos().y() < corner_size:
            self.close()

    def start_power_hold(self):
        self.powerBtn.setText("...")
        self.powerHoldTimer.start(POWER_HOLD_MS)

    def cancel_power_hold(self):
        if self.powerHoldTimer.isActive():
            self.powerHoldTimer.stop()
        self.powerBtn.setChecked(False)
        self.powerBtn.setText("⏻")

    def add_shadows(self):
        panels = self.findChildren(QFrame, "SoftPanel")
        for panel in panels:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(18)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(90, 60, 20, 25))
            panel.setGraphicsEffect(shadow)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background: #f3eee7;
                color: #4f2a08;
                font-family: Arial;
            }

            #HeaderWrap {
                background: #f6f1ea;
                border: none;
            }

            #HeaderTitle {
                font-size: 34px;
                font-weight: 900;
                color: #5a2d03;
                letter-spacing: 1px;
                padding: 8px 0;
            }

            #BodyWrap {
                background: #efe8e0;
            }

            #SoftPanel {
                background: #f8f8f8;
                border: none;
                border-radius: 22px;
            }

            #Preview {
                background: #e5d0c0;
                border: 3px solid #3f3f3f;
                border-radius: 0px;
                color: #6b3d10;
                font-size: 22px;
                font-weight: 700;
            }

            /* MIDDLE PANEL */
            #MidTopStrip {
                background: #dddddd;
                color: #6b3d10;
                border-radius: 8px;
                font-size: 18px;
                font-weight: 900;
                padding: 0 10px;
            }

            #MidGradeTitle {
                background: transparent;
                color: #6b3d10;
                font-size: 15px;
                font-weight: 900;
                padding: 0;
            }

            #MidGradeWrap {
                background: transparent;
                border: none;
            }

            #MidGradeBig {
                background: #8a5921;
                color: white;
                border-radius: 10px;
                font-size: 32px;
                font-weight: 900;
                padding: 0 12px;
            }

            #MidConfidenceTitle {
                background: transparent;
                color: #6b3d10;
                font-size: 15px;
                font-weight: 900;
                padding: 0;
            }

            #MidBottomNote {
                background: #f1ece5;
                color: #4f2a08;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 900;
                padding-left: 14px;
                padding-right: 14px;
            }

            /* RIGHT PANEL */
            #BrownHeader {
                background: #7b4d21;
                color: white;
                border-radius: 10px;
                font-size: 23px;
                font-weight: 900;
                padding: 6px 8px;
            }

            #CreamHeader {
                background: #efe1c8;
                color: #5a2d03;
                border-radius: 10px;
                font-size: 23px;
                font-weight: 900;
                padding: 6px 8px;
            }

            #BatchValueText {
                color: #4f2a08;
                font-size: 21px;
                font-weight: 900;
                padding: 2px 6px 4px 6px;
            }

            #SensorStatusText {
                background: #ece7e7;
                color: #4f2a08;
                border-radius: 8px;
                font-size: 17px;
                font-weight: 900;
                padding: 10px 14px;
            }

            #MoistureBox {
                background: #ece7e7;
                border-radius: 8px;
            }

            #MoistureTitle {
                color: #4f2a08;
                font-size: 18px;
                font-weight: 900;
            }

            #MoistureValue {
                color: #7b4d21;
                font-size: 54px;
                font-weight: 900;
            }

            #RecoValueText {
                color: #4f2a08;
                font-size: 19px;
                font-weight: 900;
                padding: 4px 6px 2px 6px;
            }

            #BottomWrap {
                background: white;
                border: none;
            }

            #FooterLightBtn {
                background: #efe1c8;
                color: #6b3d10;
                border: none;
                border-radius: 14px;
                font-size: 28px;
                font-weight: 900;
            }

            #FooterLightBtn:pressed {
                background: #e1d0b5;
            }

            #FooterMainBtn {
                background: #7b4d21;
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 42px;
                font-weight: 900;
            }

            #FooterMainBtn:pressed {
                background: #613a15;
            }

            #DangerBtn {
                background: #a23425;
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 42px;
                font-weight: 900;
            }

            #DangerBtn:pressed {
                background: #82271b;
            }

            #PowerBtn {
                background: #8b5a21;
                color: white;
                border: none;
                border-radius: 37px;
                font-size: 38px;
                font-weight: 900;
            }

            #PowerBtn:pressed {
                background: #6d4518;
            }

            #PowerBtn:checked {
                background: #6d4518;
            }

            #OverlayPage {
                background: rgba(0, 0, 0, 110);
            }

            #OverlayDialog {
                background: white;
                border: 1px solid #e5d7ca;
                border-radius: 18px;
                min-width: 520px;
                max-width: 900px;
                min-height: 380px;
            }

            #OverlayTitle {
                font-size: 18px;
                font-weight: 900;
                color: #6a3b20;
            }

            #OverlayClose {
                background: #efe5db;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 900;
                color: #6a3b20;
            }

            #OverlayClose:pressed {
                background: #e4d5c6;
            }

            #OverlayBody {
                font-size: 14px;
                color: #4b2f1e;
            }
        """)

    def _resize_overlays(self):
        c = self.centralWidget()
        if c:
            self.reportOverlay.setGeometry(c.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_overlays()

    def open_history(self):
        self.reportOverlay.hide_overlay()
        dialog = HistoryDialog(self)
        dialog.exec_()

    def open_report(self):
        self.reportOverlay.show_overlay()

    def update_datetime(self):
        now = QDateTime.currentDateTime()
        self.current_date = now.toString("yyyy-MM-dd")
        self.current_time = now.toString("hh:mm:ss AP")

    def toggle_system(self):
        if not self.is_running:
            self.is_running = True
            self.mainBtn.setText("STOP")
            self.mainBtn.setObjectName("DangerBtn")
            self._repolish(self.mainBtn)

            if self.cap.isOpened():
                self.preview_timer.start(CAM_FPS_MS)
            else:
                self.previewLabel.setText("No camera detected.\nCheck webcam / permissions.")
                self.previewLabel.setAlignment(Qt.AlignCenter)

            self.ai_timer.stop()
            QTimer.singleShot(AI_FIRST_READ_DELAY_MS, self.do_ai_read)
            self.ai_timer.start()

        else:
            self.is_running = False
            self.mainBtn.setText("START")
            self.mainBtn.setObjectName("FooterMainBtn")
            self._repolish(self.mainBtn)

            self.preview_timer.stop()
            self.ai_timer.stop()
            self.confGauge.stop_animation()

            if self.last_frame is None:
                self.previewLabel.setText("Stopped.\nTap START to show camera.")
                self.previewLabel.setAlignment(Qt.AlignCenter)
            else:
                self._set_preview_from_bgr(self.last_frame)

    def do_ai_read(self):
        if not self.is_running:
            return

        import random

        confidence = random.uniform(35.0, 95.0)
        moisture = random.randint(10, 18)

        self.confGauge.set_target(confidence)
        self.moistureValue.setText(f"{moisture}%")

        if confidence >= 85:
            self.gradeValue.setText("GRADE 1")
            self.colorNote.setText("Clean and White to Pale Color")
            self.recommendation.setText("✔ PASSED: READY TO SELL")
        elif confidence >= 70:
            self.gradeValue.setText("GRADE 2")
            self.colorNote.setText("Good Color and Acceptable Quality")
            self.recommendation.setText("✔ PASSED: GOOD FOR MARKET")
        elif confidence >= 50:
            self.gradeValue.setText("GRADE 3")
            self.colorNote.setText("Needs Further Drying / Sorting")
            self.recommendation.setText("⚠ NEEDS FURTHER PROCESS")
        else:
            self.gradeValue.setText("REJECT")
            self.colorNote.setText("Poor Quality and High Moisture")
            self.recommendation.setText("✖ REJECTED: NOT READY")

        if moisture >= 14:
            self.copraStatus.setText("COPRA STATUS: WET")
        else:
            self.copraStatus.setText("COPRA STATUS: DRY")

    def _repolish(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_preview_from_bgr(self, frame_bgr):
        if frame_bgr is None:
            return

        frame_bgr = cv2.resize(frame_bgr, (PREVIEW_W, PREVIEW_H), interpolation=cv2.INTER_AREA)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self.previewLabel.setPixmap(QPixmap.fromImage(qt_image))
        self.previewLabel.setAlignment(Qt.AlignCenter)

    def update_frame(self):
        if not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        self.last_frame = frame
        self._set_preview_from_bgr(frame)

    def closeEvent(self, event):
        try:
            self.powerHoldTimer.stop()
        except Exception:
            pass
        try:
            self.preview_timer.stop()
        except Exception:
            pass
        try:
            self.ai_timer.stop()
        except Exception:
            pass
        try:
            self.confGauge.stop_animation()
        except Exception:
            pass
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()