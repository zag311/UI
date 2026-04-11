import sys
import os
import cv2
import tensorflow as tf
import numpy as np
import serial
import re
import create_tables
from datetime import datetime
from statistics import mode, StatisticsError

from PyQt5.QtCore import (
    Qt, QTimer, QDateTime, QRectF,
    QPropertyAnimation, QEasingCurve, pyqtProperty, 
    QThread, pyqtSignal
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
from report import ReportDialog

# ===== Constants (Scaled down) =====
MODEL_PATH = "/home/aldenrecharge/Desktop/Raspberry/Copra_Final.tflite"
CLASS_NAMES = ['G1', 'G2', 'G3', 'NOT', 'REJ']
IMAGE_SIZE = (224, 224)
PREVIEW_W = 360
PREVIEW_H = 450
CAM_FPS_MS = 30
AI_READ_INTERVAL_MS = 1_000
AI_FIRST_READ_DELAY_MS = 600
POWER_HOLD_MS = 1000
NORMALIZED_RANK = {
    "GRADE 1": 1,
    "G1": 1,
    "GRADE 2": 2,
    "G2": 2,
    "GRADE 3": 3,
    "G3": 3,
    "REJECT": 4,
    "REJ": 4,
}

def get_worst_grade(grade1, grade2):
    """
    Returns the "worst" grade (highest rank) between two grades,
    regardless of whether it's AI or moisture.
    """
    rank1 = NORMALIZED_RANK.get(grade1, 0)
    rank2 = NORMALIZED_RANK.get(grade2, 0)
    
    # Return the one with higher numeric rank (worse)
    return grade1 if rank1 >= rank2 else grade2

class CameraThread(QThread):
    frame_ready = pyqtSignal(object)
    camera_failed = pyqtSignal()
    

    def __init__(self, cam_index=0, width=400, height=680, fps=20):
        super().__init__()
        self.cam_index = cam_index
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False

    def run(self):
        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_V4L2)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        # 🔴 VERY IMPORTANT: reduce buffer
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # if not cap.isOpened():
        #     print("Camera failed to open")
        #     return

        self.running = True

        while self.running:
            ret, frame = cap.read()

            if not ret or frame is None:
                # skip corrupted frame
                self.msleep(10)
                continue

            # emit only good frames
            self.frame_ready.emit(frame)

            # 🔴 throttle to avoid MJPG corruption
            self.msleep(30)  # ~30ms ≈ 30 FPS safe pacing

        cap.release()

    def stop(self):
        self.running = False
        self.wait()

# ===== Confidence Gauge =====
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

        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        pad = 12
        ring_th = 26

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
        f = QFont("Arial", 20)
        f.setBold(True)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, f"{int(self._value)}%")

# ===== Panels =====
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

# ===== AI Thread =====
class AIWorker(QThread):
    result_ready = pyqtSignal(str, float)

    def __init__(self, frame, interpreter, input_details, output_details):
        super().__init__()
        self.frame = frame.copy()
        self.interpreter = interpreter
        self.input_details = input_details
        self.output_details = output_details

    def run(self):
        frame_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(frame_rgb, IMAGE_SIZE)
        img_array = resized.astype(np.float32)
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        img_array = np.expand_dims(img_array, axis=0)

        self.interpreter.set_tensor(self.input_details[0]['index'], img_array)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])

        idx = int(np.argmax(output))
        confidence = float(output[0][idx])
        label = CLASS_NAMES[idx]
        print(label)
        self.result_ready.emit(label, confidence)

# ===== Main Window =====
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        create_tables.init_db()

        # This exit button
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 18px;
                font-weight: bold;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_moisture_collection)
        self.cancel_button.hide()

        # This is Start Button
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(12)
        self.startBtn = QPushButton("Start Collection")
        self.startBtn.setObjectName("PrimaryBtn")
        self.startBtn.setMinimumHeight(46)
        self.startBtn.clicked.connect(self.start_moisture_collection)
        buttonLayout.addWidget(self.startBtn)

        self.overlay_start_button = QPushButton("Start Collection", self)
        self.overlay_start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 18px;
                font-weight: bold;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.overlay_start_button.clicked.connect(self.start_moisture_collection)
        self.overlay_start_button.hide()

        # Updated Camera
        self.camera_thread = CameraThread(cam_index=0, width=400, height=680, fps=20)
        self.camera_thread.frame_ready.connect(self.update_preview)
        self.camera_thread.start()
        self.camera_thread.camera_failed.connect(self.on_camera_failed)
        self.moisture_samples = []
        self.arduino_grades = []  # new list to track grades

        # Start a batch when app starts
        self.current_batch_id, self.image_folder, self.receipt_folder = create_tables.start_new_batch(operator_id=1)
        
        # Moisture Capture
        self.auto_capture_enabled = True
        self.is_paused_for_measurement = False

        self.moisture_done = False

        self.moisture_threshold = 6.0  # adjust based on your calibration
        self.moisture_samples = []
        self.required_samples = 5

        self.current_moisture = None
        self.awaiting_stable_reading = False
        self.moisture_active = False

        # Load AI model
        self.interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        self.ai_thread_running = False
        self.last_label = None
        self.stable_counter = 0
        self.STABLE_REQUIRED = 3
        self.MIN_CONFIDENCE = 0.80
        self.capture_cooldown = False

        # Serial
        try:
            self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
            self.serial_connected = True
            print("[SERIAL] Connected")
        except Exception as e:
            self.ser = None
            self.serial_connected = False
            print("[SERIAL] Not connected:", e)
        self.serial_timer = QTimer(self)
        self.serial_timer.timeout.connect(self.read_serial)

        if self.serial_connected:
            self.serial_timer.start(200)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle("Copra Quality Analysis System")

        # Camera
        # self.cam_index = 0
        # self.cap = cv2.VideoCapture(self.cam_index, cv2.CAP_V4L2)
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 400)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 680)
        # self.cap.set(cv2.CAP_PROP_FPS, 30)
        # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        # self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.is_running = False
        self.last_frame = None

        self.ai_timer = QTimer(self)
        self.ai_timer.setInterval(AI_READ_INTERVAL_MS)
        self.ai_timer.timeout.connect(self.do_ai_read)

        self.powerHoldTimer = QTimer(self)
        self.powerHoldTimer.setSingleShot(True)
        self.powerHoldTimer.timeout.connect(self.close)

        # ===== Layout =====
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)

        # Header
        headerWrap = QFrame()
        headerWrap.setObjectName("HeaderWrap")
        headerLay = QVBoxLayout(headerWrap)
        headerLay.setContentsMargins(16,10,16,10)
        self.titleLabel = QLabel("COPRA QUALITY ANALYSIS SYSTEM")
        self.titleLabel.setObjectName("HeaderTitle")
        self.titleLabel.setAlignment(Qt.AlignCenter)
        headerLay.addWidget(self.titleLabel)
        outer.addWidget(headerWrap)

        # Body
        bodyWrap = QFrame()
        bodyWrap.setObjectName("BodyWrap")
        bodyLay = QHBoxLayout(bodyWrap)
        bodyLay.setContentsMargins(16,14,16,14)
        bodyLay.setSpacing(10)

        # LEFT Panel
        leftPanel = SoftPanel()
        leftPanel.setMinimumWidth(280)
        leftLay = QVBoxLayout(leftPanel)
        leftLay.setContentsMargins(12,12,12,12)
        leftLay.setSpacing(2)

        self.previewLabel = QLabel("Tap START to show camera")
        self.previewLabel.setObjectName("Preview")
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setMinimumSize(280, 200)
        leftLay.addWidget(self.previewLabel, 0, Qt.AlignCenter)
        # if not self.cap.isOpened():
        #     self.previewLabel.setText("No camera detected.\nCheck webcam / permissions.")
        #     self.previewLabel.setAlignment(Qt.AlignCenter)

        # CENTER Panel
        centerPanel = SoftPanel()
        centerPanel.setMinimumWidth(220)
        centerLay = QVBoxLayout(centerPanel)
        centerLay.setContentsMargins(8,8,8,8)
        centerLay.setSpacing(4)

        analysisHeader = QLabel("AI ANALYSIS RESULT:")
        analysisHeader.setObjectName("MidTopStrip")
        analysisHeader.setAlignment(Qt.AlignCenter)
        analysisHeader.setFixedHeight(32)
        centerLay.addWidget(analysisHeader)

        gradeTitle = QLabel("GRADE")
        gradeTitle.setObjectName("MidGradeTitle")
        gradeTitle.setAlignment(Qt.AlignCenter)
        gradeTitle.setFixedHeight(22)
        centerLay.addWidget(gradeTitle)

        centerLay.addSpacing(2)
        gradeWrap = QFrame()
        gradeWrap.setObjectName("MidGradeWrap")
        gradeWrapLay = QHBoxLayout(gradeWrap)
        gradeWrapLay.setContentsMargins(16,0,16,0)
        self.gradeValue = QLabel("GRADE 1")
        self.gradeValue.setObjectName("MidGradeBig")
        self.gradeValue.setAlignment(Qt.AlignCenter)
        self.gradeValue.setFixedHeight(42)
        gradeWrapLay.addWidget(self.gradeValue)
        centerLay.addWidget(gradeWrap)

        centerLay.addSpacing(8)
        confTitle = QLabel("CONFIDENCE LEVEL:")
        confTitle.setObjectName("MidConfidenceTitle")
        confTitle.setAlignment(Qt.AlignCenter)
        confTitle.setFixedHeight(24)
        centerLay.addWidget(confTitle)
        centerLay.addSpacing(4)

        self.confGauge = ConfidenceGauge(self)
        centerLay.addWidget(self.confGauge, 0, Qt.AlignCenter)
        centerLay.addSpacing(8)

        self.colorNote = QLabel("Clean and White to Pale Color")
        self.colorNote.setObjectName("MidBottomNote")
        self.colorNote.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.colorNote.setFixedHeight(40)
        centerLay.addWidget(self.colorNote)

        # RIGHT Column
        rightCol = QVBoxLayout()
        rightCol.setSpacing(8)
        rightCol.setContentsMargins(0,0,0,0)

        # Batch Panel
        batchPanel = SoftPanel()
        batchPanel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        batchLay = QVBoxLayout(batchPanel)
        batchLay.setContentsMargins(6,6,6,8)
        batchLay.setSpacing(6)
        batchHead = BrownHeader("BATCH COUNT")
        batchHead.setFixedHeight(36)
        batchLay.addWidget(batchHead)
        self.batchLabel = QLabel("BATCH 1: 0 COPRA", self)
        self.batchLabel.setObjectName("BatchValueText")
        self.batchLabel.setAlignment(Qt.AlignCenter)
        batchLay.addWidget(self.batchLabel)
        batchLay.addStretch(1)

        # Sensor Panel
        sensorPanel = SoftPanel()
        sensorPanel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sensorLay = QVBoxLayout(sensorPanel)
        sensorLay.setContentsMargins(6,6,6,6)
        sensorLay.setSpacing(6)
        sensorHead = CreamHeader("SENSOR READING")
        sensorHead.setFixedHeight(36)
        sensorLay.addWidget(sensorHead)
        self.copraStatus = QLabel("COPRA STATUS: WET")
        self.copraStatus.setObjectName("SensorStatusText")
        self.copraStatus.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        sensorLay.addWidget(self.copraStatus)

        moistureBox = QFrame()
        moistureBox.setObjectName("MoistureBox")
        moistureLay = QHBoxLayout(moistureBox)
        moistureLay.setContentsMargins(12,6,12,6)
        moistureLay.setSpacing(6)
        self.moistureLabelTitle = QLabel("MOISTURE LEVEL:")
        self.moistureLabelTitle.setObjectName("MoistureTitle")
        self.moistureValue = QLabel("12%")
        self.moistureValue.setObjectName("MoistureValue")
        self.moistureValue.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        moistureLay.addWidget(self.moistureLabelTitle, 1)
        moistureLay.addWidget(self.moistureValue, 0)
        sensorLay.addWidget(moistureBox)
        sensorLay.addStretch(1)

        # Recommendation Panel
        recoPanel = SoftPanel()
        recoPanel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        recoLay = QVBoxLayout(recoPanel)
        recoLay.setContentsMargins(6,6,6,8)
        recoLay.setSpacing(6)
        recoHead = BrownHeader("RECOMMENDATION")
        recoHead.setFixedHeight(36)
        recoLay.addWidget(recoHead)
        self.recommendation = QLabel("✔ PASSED: READY TO SELL")
        self.recommendation.setObjectName("RecoValueText")
        self.recommendation.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        recoLay.addWidget(self.recommendation)
        recoLay.addStretch(1)

        rightCol.addWidget(batchPanel, 2)
        rightCol.addWidget(sensorPanel, 4)
        rightCol.addWidget(recoPanel, 2)

        bodyLay.addWidget(leftPanel,5)
        bodyLay.addWidget(centerPanel,4)
        bodyLay.addLayout(rightCol,5)
        outer.addWidget(bodyWrap,1)

        # Bottom Buttons
        bottomWrap = QFrame()
        bottomWrap.setObjectName("BottomWrap")
        bottomLay = QHBoxLayout(bottomWrap)
        bottomLay.setContentsMargins(10,10,10,10)
        bottomLay.setSpacing(10)

        self.historyBtn = QPushButton("HISTORY")
        self.historyBtn.setObjectName("FooterLightBtn")
        self.historyBtn.setMinimumHeight(60)

        self.mainBtn = QPushButton("START")
        self.mainBtn.setObjectName("FooterMainBtn")
        self.mainBtn.setMinimumHeight(72)

        self.reportBtn = QPushButton("RECEIPT")
        self.reportBtn.setObjectName("FooterLightBtn")
        self.reportBtn.setMinimumHeight(60)

        self.powerBtn = QPushButton("⏻")
        self.powerBtn.setObjectName("PowerBtn")
        self.powerBtn.setFixedSize(60,60)
        self.powerBtn.setCheckable(True)

        bottomLay.addWidget(self.historyBtn,3)
        bottomLay.addWidget(self.mainBtn,5)
        bottomLay.addWidget(self.reportBtn,3)
        bottomLay.addWidget(self.powerBtn,0)
        outer.addWidget(bottomWrap)

        self.reportDialog = ReportDialog(self)
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

        # if not self.cap.isOpened():
        #     self.previewLabel.setText("No camera detected.\nCheck webcam / permissions.")
        #     self.previewLabel.setAlignment(Qt.AlignCenter)

        self.overlay_label = QLabel(self)
        self.overlay_label.setAlignment(Qt.AlignCenter)
        self.overlay_label.setStyleSheet("""
            background-color: rgba(20, 20, 20, 200);
            color: #FFFFFF;    
            font-size: 28px;
            font-weight: bold;
            border-radius: 16px;
            padding: 40px;
        """)
        self.overlay_label.setGeometry(self.rect())
        self.overlay_label.hide()

        # ✅ CREATE layout FIRST
        self.overlay_layout = QVBoxLayout(self.overlay_label)
        self.overlay_layout.setAlignment(Qt.AlignCenter)

        # Push button toward bottom
        button_row = QHBoxLayout()
        button_row.setSpacing(20)

        button_row.addWidget(self.overlay_start_button)
        button_row.addWidget(self.cancel_button)

        self.overlay_layout.addStretch()
        self.overlay_layout.addLayout(button_row)

        self.load_current_batch()


    def mouseDoubleClickEvent(self, event):
        corner_size = 120
        if event.pos().x() > self.width() - corner_size and event.pos().y() < corner_size:
            self.close()
    
    def on_camera_failed(self):
        self.previewLabel.setText("No camera detected.\nCheck webcam / permissions.")

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
        """)

    def open_history(self):
        dialog = HistoryDialog(self)
        dialog.exec_()

    def open_report(self):
        self.reportDialog.exec_()

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

            # if self.cap:
            #     self.preview_timer.start(CAM_FPS_MS)
            # else:
            #     self.previewLabel.setText("No camera detected.\nCheck webcam / permissions.")
            #     self.previewLabel.setAlignment(Qt.AlignCenter)

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
                # Temporary addition for testing purposes
                # self.auto_capture("GRADE 1", 1.0)

    def do_ai_read(self):
        if not self.is_running or self.last_frame is None:
            return
        
        if self.is_paused_for_measurement:
            return
        
        if self.ai_thread_running:
            return

        self.ai_thread_running = True

        self.ai_worker = AIWorker(
            self.last_frame,
            self.interpreter,
            self.input_details,
            self.output_details
        )

        self.ai_worker.result_ready.connect(self.handle_ai_result)
        self.ai_worker.finished.connect(self.on_ai_finished)
        self.ai_worker.start()

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
        frame_rgb = np.ascontiguousarray(frame_rgb)
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.previewLabel.setPixmap(QPixmap.fromImage(qt_image))
        self.previewLabel.setAlignment(Qt.AlignCenter)


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
        # try:
        #     if self.cap is not None:
        #         self.cap.release()
        # except Exception:
        #     pass
        try:
            self.camera_thread.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def on_ai_finished(self):
        self.ai_thread_running = False
        self.ai_worker.deleteLater()
        self.ai_worker = None


    def handle_ai_result(self, label, confidence):
        confidence_percent = confidence * 100.0
        self.confGauge.set_target(confidence_percent)

        # === Grade Mapping ===
        grade_map = {
            'G1': ("GRADE 1", "Clean and White to Pale Color", "✔ PASSED: READY TO SELL"),
            'G2': ("GRADE 2", "Good Color and Acceptable Quality", "✔ PASSED: GOOD FOR MARKET"),
            'G3': ("GRADE 3", "Needs Further Drying / Sorting", "⚠ NEEDS FURTHER PROCESS"),
            'REJ': ("REJECT", "Poor Quality and High Moisture", "✖ REJECTED: NOT READY"),
            'NOT': ("NON-COPRA", "Not a copra sample", "Ignored")
        }

        grade, note, reco = grade_map.get(label, ("UNKNOWN", "-", "-"))
        self.captured_label = grade

        # === UI Update (optional: still show NON-COPRA) ===
        self.gradeValue.setText(grade)
        self.colorNote.setText(note)
        self.recommendation.setText(reco)

        # === 🚫 HARD FILTER ===
        if label == "NOT":
            self.stable_counter = 0
            self.last_label = None
            return  # 💀 kill the pipeline here

        # === Stability Logic (auto capture trigger) ===
        if confidence >= self.MIN_CONFIDENCE:
            if label == self.last_label:
                self.stable_counter += 1
            else:
                self.stable_counter = 1
                self.last_label = label
        else:
            self.stable_counter = 0
            self.last_label = None

        if self.stable_counter >= self.STABLE_REQUIRED and not self.capture_cooldown:
            self.capture_cooldown = True
            self.auto_capture(label, confidence)

    def process_moisture(self, moisture, grade=None):
        if not self.moisture_active:
            return
        
        if self.moisture_done:
            return

        self.startBtn.setEnabled(False)
        # Step 1: wait for threshold
        # if not self.moisture_samples and moisture < self.moisture_threshold:
            # self.show_overlay(
            #     f"Moisture: {moisture:.2f}%\nWaiting threshold...",
            #     show_cancel=True
            # )
        #     return

        # Step 2: collect sample and optional grade
        self.moisture_samples.append(moisture)
        if grade:
            self.arduino_grades.append(grade)

        # Compute current mode of grades (live)
        try:
            current_mode_grade = mode(self.arduino_grades) if self.arduino_grades else "-"
        except StatisticsError:
            current_mode_grade = "-"

        self.show_overlay(
            f"Moisture: {moisture:.2f}%\nSamples: {len(self.moisture_samples)}/{self.required_samples}",
            show_cancel=True,
            show_start=False
        )

        # Step 3: finalize if enough samples
        if len(self.moisture_samples) >= self.required_samples:
            self.moisture_done = True
            self.moisture_active = False
            avg_moisture = sum(self.moisture_samples) / len(self.moisture_samples)
            try:
                moisture_final_grade = mode(self.arduino_grades) if self.arduino_grades else self.captured_label
            except StatisticsError:
                moisture_final_grade = self.captured_label

            self.show_overlay(
                f"Final Moisture:\n{avg_moisture:.2f}%\nFinal Moisture Grade: {moisture_final_grade}",
                show_cancel=False
            )
            QTimer.singleShot(1500, lambda: self.finish_capture(avg_moisture, moisture_final_grade))
        
        self.startBtn.setEnabled(True)

    def read_serial(self):
        if not self.ser or not self.serial_connected:
            return

        if self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                print("[SERIAL]", line)

                moisture_match = re.search(r"Moisture:\s*([\d.]+)", line)
                grade_match = re.search(r"RESULT:\s*(GRADE \d+|REJECT|NON-COPRA)", line)

                if moisture_match:
                    value = float(moisture_match.group(1))
                    self.current_moisture = value
                    self.moistureValue.setText(f"{int(value)}%")

                    if value >= 14:
                        self.copraStatus.setText("COPRA STATUS: WET")
                    else:
                        self.copraStatus.setText("COPRA STATUS: DRY")

                    # Only pass to capture logic if we're waiting for stable reading
                    if self.awaiting_stable_reading:
                        # Normalize Arduino grade into DB format
                        if grade_match:
                            final_grade = grade_match.group(1).upper()  # already "GRADE 1", "GRADE 2", or "REJECT"
                        else:
                            final_grade = "REJECT"

                        self.process_moisture(value, final_grade)

            except Exception as e:
                print("Serial error:", e)

    def finish_capture(self, avg_moisture, moisture_grade):
        print("[SYSTEM] Finalizing capture")

        # Determine final grade as the worst between AI and moisture
        ai_grade = self.captured_label
        # Temporary for testing
        # ai_grade = getattr(self, "captured_label", "GRADE 1")
        # Normalize both grades immediately
        normalized_ai_grade = {
            'G1': 'GRADE 1', 'G2': 'GRADE 2', 'G3': 'GRADE 3', 'REJ': 'REJECT', 'NOT': 'NON-COPRA',
            'GRADE 1': 'GRADE 1', 'GRADE 2': 'GRADE 2', 'GRADE 3': 'GRADE 3', 'REJECT': 'REJECT', 'NOT': 'NON-COPRA'
        }.get(self.captured_label, 'NON-COPRA')  # default to REJECT if unknown

        normalized_moisture_grade = {
            'G1': 'GRADE 1', 'G2': 'GRADE 2', 'G3': 'GRADE 3', 'REJ': 'REJECT', 'NOT': 'NON-COPRA',
            'GRADE 1': 'GRADE 1', 'GRADE 2': 'GRADE 2', 'GRADE 3': 'GRADE 3', 'REJECT': 'REJECT', 'NOT': 'NON-COPRA',
        }.get(moisture_grade, 'NON-COPRA')

        # Now pick worst
        final_grade_to_save = get_worst_grade(normalized_ai_grade, normalized_moisture_grade)

        print("[DEBUG] AI:", normalized_ai_grade, "Moisture:", normalized_moisture_grade, "FINAL:", final_grade_to_save)

        base_dir = "/home/aldenrecharge/Desktop/Raspberry/images"
        batch_folder = os.path.join(base_dir, f"batch_{self.current_batch_id:03}")

        # If batch folder doesn't exist OR is empty → create/use it
        if not os.path.exists(batch_folder):
            os.makedirs(batch_folder)

        # Count current images BEFORE saving
        existing_images = [
            f for f in os.listdir(batch_folder)
            if f.lower().endswith((".jpg", ".png"))
        ]

        # If folder exists but is empty → reuse it
        # If it already has images → continue using same batch

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{final_grade_to_save}_{int(self.captured_confidence*100)}_{timestamp}.jpg"
        filepath = os.path.join(batch_folder, filename)

        # Save image
        if self.captured_frame is not None:
            cv2.imwrite(filepath, self.captured_frame)
            print(f"[SAVED IMAGE] {filepath}")
        else:
            print("[INFO] No image captured (camera disabled)")
        filepath = os.path.abspath(filepath)

        print(f"[SAVED] {filepath} | Moisture Avg: {avg_moisture:.2f} | Final Grade: {final_grade_to_save}")

        # Save to DB
        try:
            create_tables.save_image(
                batch_id=self.current_batch_id,
                image_path=filepath,
                grade=final_grade_to_save
            )
            print("[DB] Capture saved successfully.")
        except Exception as e:
            print("[DB ERROR]", e)

        # Update UI
        new_count = len(existing_images) + 1
        self.update_batch_label(new_count)

        # Reset state
        self.overlay_label.hide()
        self.is_paused_for_measurement = False
        self.awaiting_stable_reading = False
        self.moisture_samples.clear()
        self.arduino_grades.clear()
        QTimer.singleShot(3000, self.reset_capture_state)
        self.moisture_done = False
        self.startBtn.setEnabled(True)

    def auto_capture(self, label, confidence):
        if self.last_frame is not None:
            self.captured_frame = self.last_frame.copy()
        else:
            self.captured_frame = None  # 👈 allow no image

        print("[AUTO] Capture triggered")

        # Save frame temporarily (DO NOT SAVE YET)
        self.captured_label = label
        self.captured_confidence = confidence

        # Pause system
        self.is_paused_for_measurement = True
        self.awaiting_stable_reading = True
        self.moisture_samples.clear()

        # Show overlay
        self.show_overlay("Ready for moisture check", show_cancel=True, show_start=True)
        
    def show_overlay(self, text, show_cancel=False, show_start=False):
        self.overlay_label.setText(text)
        self.overlay_label.setGeometry(self.rect())
        self.overlay_label.show()

        self.cancel_button.setVisible(show_cancel)
        self.overlay_start_button.setVisible(show_start)

        if show_cancel:
            self.cancel_button.show()
        else:
            self.cancel_button.hide()

    def cancel_moisture_collection(self):
        print("[SYSTEM] Moisture collection cancelled")

        self.moisture_samples.clear()
        self.arduino_grades.clear()

        self.moisture_active = False
        self.awaiting_stable_reading = False
        self.is_paused_for_measurement = False
        self.moisture_done = True
        self.startBtn.setEnabled(True)

        self.show_overlay("Final Moisture...", show_cancel=False, show_start=False)
        QTimer.singleShot(800, self.overlay_label.hide)

        # Allow system to run again
        QTimer.singleShot(1000, self.reset_capture_state)

    def reset_capture_state(self):
        self.capture_cooldown = False
        self.stable_counter = 0
        self.last_label = None

    def update_preview(self, frame):
        if frame is None:
            return

        self.last_frame = frame.copy()  # 👈 prevent race condition
        self._set_preview_from_bgr(frame)

    def start_moisture_collection(self):
        if self.moisture_active:
            return

        self.moisture_active = True
        self.moisture_done = False   # 🔥 important reset

        if self.last_frame is not None:
            self.captured_frame = self.last_frame.copy()
        else:
            self.captured_frame = None

        self.captured_label = getattr(self, "captured_label", "GRADE 1")
        self.captured_confidence = getattr(self, "captured_confidence", 1.0)

        self.is_paused_for_measurement = True
        self.awaiting_stable_reading = True

        self.moisture_samples.clear()
        self.arduino_grades.clear()

        self.show_overlay("Waiting for moisture...", show_cancel=True)
        self.startBtn.setEnabled(False)

    def load_current_batch(self):
        base_dir = "/home/aldenrecharge/Desktop/Raspberry/images"

        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            self.current_batch_id = 1
            self.update_batch_label(0)
            return

        batches = [d for d in os.listdir(base_dir) if d.startswith("batch_")]

        if not batches:
            self.current_batch_id = 1
            self.update_batch_label(0)
            return

        # Get latest batch
        batches.sort(key=lambda x: int(x.split("_")[1]))
        latest_batch = batches[-1]

        self.current_batch_id = int(latest_batch.split("_")[1])

        batch_path = os.path.join(base_dir, latest_batch)

        # Count images
        count = len([
            f for f in os.listdir(batch_path)
            if f.lower().endswith((".jpg", ".png"))
        ])

        self.update_batch_label(count)

    def update_batch_label(self, count):
        self.batchLabel.setText(f"BATCH {self.current_batch_id}: {count} COPRA")

    # def update_preview(self):
    #     if self.cap is None:
    #         # No camera mode
    #         self.previewLabel.setText("Camera Disabled")
    #         self.previewLabel.setAlignment(Qt.AlignCenter)
    #         return

    #     if not self.cap.isOpened():
    #         self.previewLabel.setText("No camera detected")
    #         self.previewLabel.setAlignment(Qt.AlignCenter)
    #         return

    #     ret, frame = self.cap.read()
    #     if not ret or frame is None:
    #         return

    #     self.last_frame = frame.copy()
    #     self._set_preview_from_bgr(frame)

def main():
    app = QApplication(sys.argv)
    create_tables.init_db()
    w = MainWindow()
    w.showFullScreen()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()