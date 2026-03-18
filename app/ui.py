import math
import os
import sys
import time
import wave
from array import array
from typing import List, Optional

try:
    import winsound
except ImportError:
    winsound = None

import cv2
import numpy as np
from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QRectF, QPropertyAnimation, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QDialog, QFileDialog, QGridLayout, QLCDNumber, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from app.model.runtime import Scorer
from app.model.vmc import MocapRecorder, VmcReceiver
from app.store import LocalStore


def ensure_ui_sounds() -> dict:
    base = os.path.join('assets', 'ui_sfx')
    os.makedirs(base, exist_ok=True)
    tones = {
        'PERFECT': [(1320, 0.06), (1760, 0.08)],
        'GREAT': [(1040, 0.06), (1320, 0.06)],
        'GOOD': [(880, 0.07)],
        'WARN': [(420, 0.10)],
    }
    paths = {}
    sample_rate = 22050
    volume = 9000
    for name, notes in tones.items():
        path = os.path.join(base, f'{name.lower()}.wav')
        paths[name] = path
        if os.path.exists(path):
            continue
        samples = array('h')
        for freq, duration in notes:
            count = int(sample_rate * duration)
            for i in range(count):
                t = i / sample_rate
                env = 1.0 - (i / max(count, 1))
                value = int(volume * env * math.sin(2.0 * math.pi * freq * t))
                samples.append(value)
            samples.extend([0] * int(sample_rate * 0.01))
        with wave.open(path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples.tobytes())
    return paths


class AuroraPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _tick(self):
        self.phase += 0.015
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor('#F5F5F7'))
        w, h = self.width(), self.height()
        painter.setPen(Qt.NoPen)
        orbs = [
            (QPointF(w * (0.18 + 0.02 * math.sin(self.phase)), h * 0.16), max(w, h) * 0.42, QColor(162, 210, 255, 110)),
            (QPointF(w * 0.76, h * (0.22 + 0.03 * math.cos(self.phase * 0.8))), max(w, h) * 0.38, QColor(200, 180, 255, 92)),
            (QPointF(w * (0.55 + 0.015 * math.sin(self.phase * 1.3)), h * 0.88), max(w, h) * 0.46, QColor(188, 230, 255, 70)),
        ]
        for center, radius, color in orbs:
            grad = QRadialGradient(center, radius)
            edge = QColor(color)
            edge.setAlpha(0)
            grad.setColorAt(0.0, color)
            grad.setColorAt(0.55, QColor(color.red(), color.green(), color.blue(), color.alpha() // 2))
            grad.setColorAt(1.0, edge)
            painter.setBrush(grad)
            painter.drawEllipse(center, radius, radius)


class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('glassCard')
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(120, 138, 170, 45))
        self.setGraphicsEffect(shadow)


class CameraThread(QThread):
    opened_signal = pyqtSignal()
    frame_signal = pyqtSignal(QImage)
    error_signal = pyqtSignal(str)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.running = False

    def stop(self):
        self.running = False
        self.wait(1500)

    def run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.error_signal.emit(f'无法打开摄像头索引 {self.camera_index}，请切换索引或检查占用。')
            return
        self.running = True
        opened = False
        while self.running:
            ok, frame_bgr = cap.read()
            if not ok:
                self.error_signal.emit('读取摄像头画面失败。')
                break
            if not opened:
                self.opened_signal.emit()
                opened = True
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
            self.frame_signal.emit(qimg)
            self.msleep(15)
        cap.release()


class MocapThread(QThread):
    opened_signal = pyqtSignal()
    preview_signal = pyqtSignal(object)
    score_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    saved_signal = pyqtSignal(str)

    def __init__(self, dance_type: str, host: str, port: int, parent=None):
        super().__init__(parent)
        self.running = False
        self.dance_type = dance_type
        self.receiver = VmcReceiver(host=host, port=port)
        self.scorer = Scorer(dance_type=dance_type, ckpt_path='assets/weights/best_dance_scoring.ckpt')
        self.model_loaded = self.scorer.model is not None
        self.recorder = MocapRecorder(dance_type)
        self.last_timestamp = 0.0

    def stop(self):
        self.running = False
        self.wait(1500)

    def run(self):
        try:
            self.receiver.start()
        except OSError as exc:
            self.error_signal.emit(f'无法监听 VMC 端口：{exc}')
            return
        self.running = True
        opened = False
        while self.running:
            frame = self.receiver.get_latest_frame()
            if frame and frame.timestamp > self.last_timestamp:
                self.last_timestamp = frame.timestamp
                if not opened:
                    self.opened_signal.emit()
                    opened = True
                self.recorder.append(frame.joints)
                self.preview_signal.emit(frame.joints.copy())
                result = self.scorer.score_mocap_frame(frame.joints)
                if result is not None:
                    self.score_signal.emit(result[0], result[1])
            self.msleep(15)
        self.receiver.stop()
        npy_path, bvh_path = self.recorder.save()
        self.saved_signal.emit(f'已保存录制：{npy_path} | {bvh_path}')


class Window(QMainWindow):
    COOLDOWN_SEC = 3.0
    PARENT_INDEX = {0: None, 1: 0, 2: 1, 3: 2, 4: 3, 5: 0, 6: 5, 7: 6, 8: 7, 9: 0, 10: 9, 11: 10, 12: 11, 13: 2, 14: 13, 15: 14, 16: 15, 17: 2, 18: 17, 19: 18, 20: 19, 21: 1, 22: 2, 23: 3}

    def __init__(self):
        super().__init__()
        self.setWindowTitle('民族舞智能评估系统')
        self.resize(1360, 860)
        self.setMinimumSize(1200, 760)
        self.camera_thread: Optional[CameraThread] = None
        self.mocap_thread: Optional[MocapThread] = None
        self.current_qimage: Optional[QImage] = None
        self.elapsed_sec = 0
        self.last_perfect_time = 0.0
        self.session_active = False
        self.video_ready = False
        self.mocap_ready = False
        self.max_feed_items = 7
        self.combo_count = 0
        self.combo_power = 0
        self.judge_stats = {'PERFECT': 0, 'GREAT': 0, 'GOOD': 0, 'WARN': 0}
        self.score_history = []
        self.best_combo = 0
        self.sound_paths = ensure_ui_sounds()
        self.last_record_text = ''
        self.last_summary_paths = {}
        self.store = LocalStore()
        state = self.store.get_state()
        self.current_user = state.get('current_user', '游客')
        self.current_role = state.get('current_role', '学生')
        self.app_settings = {'sound': '开启', 'auto_export': '开启', 'theme': 'Apple Light'}
        self.current_dance_type = '舞种未启动'
        self.current_camera_index = '0'
        self.current_vmc_host = '0.0.0.0'
        self.current_vmc_port = '39539'
        self.current_import_path = state.get('last_import_path', '')
        self.feed_animations = []
        self.ui_animations = []
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.on_tick)
        self.beat_timer = QTimer(self)
        self.beat_timer.setInterval(850)
        self.beat_timer.timeout.connect(self._beat_pulse)
        self._build_ui()
        self._style()
        self.refresh_cameras(auto=True)
        self.reset_view_state()
        QTimer.singleShot(120, self.open_welcome_dialog)
    @staticmethod
    def detect_camera_indices(max_index: int = 10) -> List[int]:
        found = []
        for i in range(max_index + 1):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(i)
            ok = cap.isOpened()
            if ok:
                ret, _ = cap.read()
                ok = bool(ret)
            cap.release()
            if ok:
                found.append(i)
        return found

    def refresh_cameras(self, auto: bool = False):
        cams = self.detect_camera_indices(10)
        self.cam_combo.clear()
        if cams:
            self.cam_combo.addItems([str(i) for i in cams])
            if not auto:
                self.push_feed('SYSTEM', f'检测到摄像头索引：{cams}', '系统已刷新可用视频设备。')
        else:
            self.cam_combo.addItem('0')
            self.push_feed('WARN', '未检测到可用摄像头', '已回退到索引 0，请检查虚拟摄像头是否启动。')

    def reset_view_state(self):
        self.session_active = False
        self.video_ready = False
        self.mocap_ready = False
        self.timer.stop()
        self.beat_timer.stop()
        self.elapsed_sec = 0
        self.current_qimage = None
        self.video.clear()
        self.video.setText('点击“开始”同时连接虚拟摄像头与 Rebocap VMC')
        self.score_text.setText('当前得分：-')
        self.bar.setValue(0)
        self.metric_mode.setText('舞种未启动')
        self.metric_state.setText('系统待机')
        self.metric_model.setText('模型待加载')
        self.camera_hint.setText('等待视频与骨骼输入')
        self.lcd.display('00:00')
        self.perfect_label.hide()
        self.combo_count = 0
        self.combo_power = 0
        self.judge_stats = {'PERFECT': 0, 'GREAT': 0, 'GOOD': 0, 'WARN': 0}
        self.score_history = []
        self.best_combo = 0
        self.last_record_text = ''
        self.last_summary_paths = {}
        self.account_chip.setText(f'账号：{self.current_user} / {self.current_role}')
        self.combo_label.setText('COMBO x0')
        self.combo_bar.setValue(0)
        self.combo_label.hide()
        self.combo_bar.hide()
        self.judge_label.hide()
        self.pulse_overlay.hide()
        self._refresh_stats()
        self.feed.clear()
        self.push_feed('READY', '等待舞蹈开始', '连接虚拟摄像头和 Rebocap 后，这里会以游戏战报形式展示实时诊断。')

    def _feed_theme(self, tag: str):
        palette = {
            'PERFECT': ('#884BFF', '#1FC8FF', '#FFFFFF'),
            'GREAT': ('#11C68A', '#66F3BE', '#FFFFFF'),
            'GOOD': ('#FFB431', '#FFE07A', '#2A1B00'),
            'WARN': ('#FF6B7A', '#FF9E9E', '#FFFFFF'),
            'SYSTEM': ('#4776FF', '#7FB3FF', '#FFFFFF'),
            'READY': ('#8B93FF', '#C2CCFF', '#FFFFFF'),
        }
        return palette.get(tag, ('#4776FF', '#7FB3FF', '#FFFFFF'))

    def push_feed(self, tag: str, title: str, detail: str):
        start_color, end_color, text_color = self._feed_theme(tag)
        stamp = time.strftime('%H:%M:%S')
        card = QFrame()
        card.setObjectName('feedCard')
        card.setStyleSheet(
            f"QFrame#feedCard{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {start_color},stop:1 {end_color});border:1px solid rgba(255,255,255,0.34);border-radius:18px;}}"
            f"QLabel{{background:transparent;color:{text_color};}}"
            "QLabel[tag='true']{font-size:11px;font-weight:800;letter-spacing:0.10em;}"
            "QLabel[stamp='true']{font-size:11px;font-weight:700;color:rgba(255,255,255,0.86);}"
            "QLabel[title='true']{font-size:16px;font-weight:800;}"
            "QLabel[detail='true']{font-size:12px;font-weight:600;color:rgba(255,255,255,0.92);}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        tag_label = QLabel(tag)
        tag_label.setProperty('tag', True)
        time_label = QLabel(stamp)
        time_label.setProperty('stamp', True)
        top_row.addWidget(tag_label)
        top_row.addStretch(1)
        top_row.addWidget(time_label)
        title_label = QLabel(title)
        title_label.setProperty('title', True)
        title_label.setWordWrap(True)
        detail_label = QLabel(detail)
        detail_label.setProperty('detail', True)
        detail_label.setWordWrap(True)
        layout.addLayout(top_row)
        layout.addWidget(title_label)
        layout.addWidget(detail_label)
        opacity = QGraphicsOpacityEffect(card)
        opacity.setOpacity(0.0)
        card.setGraphicsEffect(opacity)
        card.move(0, 10)
        item = QListWidgetItem()
        item.setSizeHint(card.sizeHint())
        self.feed.insertItem(0, item)
        self.feed.setItemWidget(item, card)
        fade = QPropertyAnimation(opacity, b'opacity', card)
        fade.setDuration(240)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        slide = QPropertyAnimation(card, b'pos', card)
        slide.setDuration(240)
        slide.setStartValue(QPoint(0, 14))
        slide.setEndValue(QPoint(0, 0))
        slide.setEasingCurve(QEasingCurve.OutBack)
        self.feed_animations.extend([fade, slide])
        fade.finished.connect(lambda: self._clear_finished_animations())
        slide.finished.connect(lambda: self._clear_finished_animations())
        fade.start()
        slide.start()
        while self.feed.count() > self.max_feed_items:
            self.feed.takeItem(self.feed.count() - 1)

    def _clear_finished_animations(self):
        self.feed_animations = [anim for anim in self.feed_animations if anim.state() != QPropertyAnimation.Stopped]

    def _clear_ui_animations(self):
        self.ui_animations = [anim for anim in self.ui_animations if anim.state() != QPropertyAnimation.Stopped]

    def _rank_colors(self, rank: str):
        palette = {
            'PERFECT': ('#8B5CFF', '#1FC8FF'),
            'GREAT': ('#32C27D', '#71E0AF'),
            'GOOD': ('#FFB340', '#FFD76A'),
            'WARN': ('#FF5F57', '#FF8A7A'),
        }
        return palette.get(rank, ('#8B5CFF', '#1FC8FF'))

    def _play_judge_sound(self, rank: str):
        if self.app_settings.get('sound') != '开启':
            return
        if winsound is not None:
            try:
                winsound.PlaySound(self.sound_paths.get(rank, ''), winsound.SND_ASYNC | winsound.SND_FILENAME)
                return
            except RuntimeError:
                pass
        app = QApplication.instance()
        if app is not None:
            app.beep()

    def _refresh_stats(self):
        total = max(1, sum(self.judge_stats.values()))
        for rank, label in self.stat_labels.items():
            count = self.judge_stats[rank]
            label.setText(str(count))
            self.stat_bars[rank].setValue(int(round(count * 100 / total)))

    def _beat_pulse(self):
        if not self.session_active:
            return
        self._flash_pulse('GOOD')

    def _score_grade(self, avg_score: float):
        if avg_score >= 92:
            return 'S', '#8B5CFF', '#1FC8FF'
        if avg_score >= 85:
            return 'A', '#32C27D', '#71E0AF'
        if avg_score >= 75:
            return 'B', '#FFB340', '#FFD76A'
        return 'C', '#FF5F57', '#FF8A7A'

    def _ensure_report_dir(self):
        path = os.path.join('assets', 'reports')
        os.makedirs(path, exist_ok=True)
        return path

    def _summary_stem(self):
        dance_slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in self.metric_mode.text()).strip("_")
        stamp = time.strftime('%Y%m%d_%H%M%S')
        return f'{dance_slug or "dance"}_{stamp}'

    def _export_summary_assets(self, avg_score: float):
        report_dir = self._ensure_report_dir()
        stem = self._summary_stem()
        screenshot_path = os.path.join(report_dir, f'{stem}_summary.png')
        report_path = os.path.join(report_dir, f'{stem}_summary.txt')
        self.grab().save(screenshot_path)
        total_hits = sum(self.judge_stats.values())
        lines = [
            '民族舞智能评估系统 - 成绩单',
            f'舞种: {self.metric_mode.text()}',
            f'平均得分: {avg_score:.1f}',
            f'最高连击: {self.best_combo}',
            f'总判定数: {total_hits}',
            f'舞蹈时长: {self.elapsed_sec // 60:02d}:{self.elapsed_sec % 60:02d}',
            f'模型状态: {self.metric_model.text()}',
            f'录制文件: {self.last_record_text or "无"}',
            '',
            '判定分布:',
        ]
        for rank in ['PERFECT', 'GREAT', 'GOOD', 'WARN']:
            percent = (self.judge_stats[rank] * 100 / total_hits) if total_hits else 0.0
            lines.append(f'- {rank}: {self.judge_stats[rank]} ({percent:.1f}%)')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        self.last_summary_paths = {'screenshot': screenshot_path, 'report': report_path}
        return screenshot_path, report_path

    def _open_summary_file(self, key: str):
        path = self.last_summary_paths.get(key)
        if not path:
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except AttributeError:
            self.push_feed('SYSTEM', '导出文件', path)

    def _show_summary_dialog(self):
        total_hits = sum(self.judge_stats.values())
        if total_hits == 0:
            return
        avg_score = sum(self.score_history) / max(len(self.score_history), 1)
        grade, grade_start, grade_end = self._score_grade(avg_score)
        screenshot_path, report_path = ('未导出', '未导出')
        self.last_summary_paths = {}
        if self.app_settings.get('auto_export') == '开启':
            screenshot_path, report_path = self._export_summary_assets(avg_score)
        self.store.save_history(
            {
                'username': self.current_user,
                'role': self.current_role,
                'dance_type': self.current_dance_type,
                'avg_score': avg_score,
                'best_combo': self.best_combo,
                'duration_sec': self.elapsed_sec,
                'grade': grade,
                'record_text': self.last_record_text,
                'summary_report': report_path if report_path != '未导出' else '',
                'summary_image': screenshot_path if screenshot_path != '未导出' else '',
            }
        )
        dialog = QDialog(self)
        dialog.setWindowTitle('本次舞蹈结算')
        dialog.setModal(True)
        dialog.resize(560, 500)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QLabel#title{font-size:28px;font-weight:800;color:#101426;}"
            "QLabel#sub{font-size:13px;color:#6a7288;} QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QLabel#metricName{font-size:12px;color:#7b8193;font-weight:700;} QLabel#metricValue{font-size:28px;color:#12192c;font-weight:800;}"
            "QLabel#rowName{font-size:13px;color:#22304d;font-weight:700;} QLabel#rowValue{font-size:13px;color:#22304d;font-weight:800;}"
            "QProgressBar{background:rgba(14,18,34,0.08);border:1px solid rgba(0,0,0,0.05);border-radius:8px;min-height:10px;max-height:10px;}"
            "QProgressBar::chunk{border-radius:8px;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8B5CFF, stop:1 #1FC8FF);}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;border:1px solid rgba(0,113,227,0.20);}"
            "QPushButton#ghost{color:#172033;background:#E9EEF8;border:1px solid rgba(0,0,0,0.06);}"
            "QLabel#badge{color:white;border-radius:30px;padding:10px 18px;font-size:32px;font-weight:900;letter-spacing:0.08em;}"
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        hero = QHBoxLayout()
        hero.setSpacing(14)
        badge = QLabel(grade)
        badge.setObjectName('badge')
        badge.setStyleSheet(
            f"QLabel#badge{{color:white;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {grade_start}, stop:1 {grade_end});"
            "border-radius:30px;padding:10px 18px;font-size:32px;font-weight:900;letter-spacing:0.08em;}}"
        )
        hero_text = QVBoxLayout()
        hero_text.setSpacing(4)
        title = QLabel('舞蹈结算')
        title.setObjectName('title')
        sub = QLabel('本次实时评估已经结束，以下是本轮表现摘要。')
        sub.setObjectName('sub')
        hero_text.addWidget(title)
        hero_text.addWidget(sub)
        hero.addWidget(badge, 0, Qt.AlignTop)
        hero.addLayout(hero_text, 1)
        layout.addLayout(hero)

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(12)
        top_grid.setVerticalSpacing(12)
        for idx, (name, value) in enumerate([
            ('平均得分', f'{avg_score:.1f}'),
            ('最高连击', str(self.best_combo)),
            ('总判定数', str(total_hits)),
            ('舞蹈时长', f'{self.elapsed_sec // 60:02d}:{self.elapsed_sec % 60:02d}'),
        ]):
            card = QFrame()
            card.setObjectName('card')
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(4)
            key = QLabel(name)
            key.setObjectName('metricName')
            val = QLabel(value)
            val.setObjectName('metricValue')
            card_layout.addWidget(key)
            card_layout.addWidget(val)
            top_grid.addWidget(card, idx // 2, idx % 2)
        layout.addLayout(top_grid)

        detail_card = QFrame()
        detail_card.setObjectName('card')
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)
        for rank in ['PERFECT', 'GREAT', 'GOOD', 'WARN']:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            name = QLabel(rank)
            name.setObjectName('rowName')
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setValue(int(round(self.judge_stats[rank] * 100 / total_hits)))
            value = QLabel(f"{self.judge_stats[rank]}  ({self.judge_stats[rank] * 100 / total_hits:.0f}%)")
            value.setObjectName('rowValue')
            row.addWidget(name)
            row.addWidget(bar, 1)
            row.addWidget(value)
            detail_layout.addLayout(row)
        layout.addWidget(detail_card)

        path_card = QFrame()
        path_card.setObjectName('card')
        path_layout = QVBoxLayout(path_card)
        path_layout.setContentsMargins(16, 14, 16, 14)
        path_layout.setSpacing(6)
        path_title = QLabel('录制输出')
        path_title.setObjectName('metricName')
        path_value = QLabel(self.last_record_text or '本轮未生成录制文件。')
        path_value.setObjectName('rowValue')
        path_value.setWordWrap(True)
        path_layout.addWidget(path_title)
        path_layout.addWidget(path_value)
        layout.addWidget(path_card)

        export_card = QFrame()
        export_card.setObjectName('card')
        export_layout = QVBoxLayout(export_card)
        export_layout.setContentsMargins(16, 14, 16, 14)
        export_layout.setSpacing(6)
        export_title = QLabel('导出结果')
        export_title.setObjectName('metricName')
        export_value = QLabel(f'截图: {screenshot_path}\n成绩单: {report_path}')
        export_value.setObjectName('rowValue')
        export_value.setWordWrap(True)
        export_layout.addWidget(export_title)
        export_layout.addWidget(export_value)
        layout.addWidget(export_card)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        shot_btn = QPushButton('打开截图')
        shot_btn.setObjectName('ghost')
        shot_btn.clicked.connect(lambda: self._open_summary_file('screenshot'))
        report_btn = QPushButton('打开成绩单')
        report_btn.setObjectName('ghost')
        report_btn.clicked.connect(lambda: self._open_summary_file('report'))
        open_btn = QPushButton('打开录制目录')
        open_btn.setObjectName('ghost')
        open_btn.clicked.connect(self._open_record_folder)
        close_btn = QPushButton('完成')
        close_btn.clicked.connect(dialog.accept)
        button_row.addWidget(shot_btn)
        button_row.addWidget(report_btn)
        button_row.addWidget(open_btn)
        button_row.addStretch(1)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)
        dialog.exec_()

    def _open_record_folder(self):
        folder = os.path.join(os.getcwd(), 'assets', 'data', 'records')
        os.makedirs(folder, exist_ok=True)
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except AttributeError:
            self.push_feed('SYSTEM', '录制目录', folder)

    def _open_summary_dir(self):
        folder = os.path.join(os.getcwd(), 'assets', 'reports')
        os.makedirs(folder, exist_ok=True)
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except AttributeError:
            self.push_feed('SYSTEM', '成绩目录', folder)

    def _list_dir_items(self, folder: str, suffixes=None):
        os.makedirs(folder, exist_ok=True)
        items = []
        for name in sorted(os.listdir(folder), reverse=True):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            if suffixes and not any(name.lower().endswith(sfx) for sfx in suffixes):
                continue
            items.append(path)
        return items

    def _open_path(self, path: str):
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except AttributeError:
            self.push_feed('SYSTEM', '文件路径', path)

    def _dialog_base_qss(self, extra: str = '') -> str:
        return (
            "QDialog{background:#f7f8fc;}"
            "QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QFrame#hero{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8B5CFF, stop:1 #1FC8FF);border-radius:24px;}"
            "QLabel#title{font-size:24px;font-weight:800;color:#101426;}"
            "QLabel#sub{font-size:13px;color:#6a7288;}"
            "QLabel#key{font-size:12px;color:#7b8193;font-weight:700;}"
            "QLabel#val{font-size:16px;color:#15203a;font-weight:800;}"
            "QLineEdit,QComboBox,QTextEdit{background:#F2F2F7;color:#1d1d1f;border:1px solid rgba(0,0,0,0.06);border-radius:16px;padding:8px 12px;min-height:34px;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;border:1px solid rgba(0,113,227,0.20);}"
            "QPushButton#ghost{color:#172033;background:#E9EEF8;border:1px solid rgba(0,0,0,0.06);}"
            "QListWidget{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;padding:12px;}"
            + extra
        )

    def open_login_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('账号登录')
        dialog.setModal(True)
        dialog.resize(460, 320)
        dialog.setStyleSheet(self._dialog_base_qss())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        title = QLabel('账号登录')
        title.setObjectName('title')
        sub = QLabel('支持本地登录、注册和找回密码，账号会保存在本地数据库。')
        sub.setObjectName('sub')
        mode = QComboBox()
        mode.addItems(['登录', '注册', '找回密码'])
        name_input = QLineEdit(self.current_user if self.current_user != '游客' else '')
        name_input.setPlaceholderText('请输入用户名')
        pwd_input = QLineEdit()
        pwd_input.setEchoMode(QLineEdit.Password)
        pwd_input.setPlaceholderText('请输入密码')
        role_combo = QComboBox()
        role_combo.addItems(['学生', '教师', '管理员'])
        card_layout.addWidget(title)
        card_layout.addWidget(sub)
        card_layout.addWidget(mode)
        card_layout.addWidget(name_input)
        card_layout.addWidget(pwd_input)
        card_layout.addWidget(role_combo)
        layout.addWidget(card)
        btn_row = QHBoxLayout()
        guest_btn = QPushButton('游客模式')
        guest_btn.setObjectName('ghost')
        ok_btn = QPushButton('确认')
        guest_btn.clicked.connect(lambda: name_input.setText('游客'))
        def apply_auth():
            username = name_input.text().strip() or '游客'
            password = pwd_input.text().strip() or 'guest123'
            selected_mode = mode.currentText()
            if username == '游客':
                self.current_user = '游客'
                self.current_role = '学生'
                self.store.set_state(current_user=self.current_user, current_role=self.current_role)
                dialog.accept()
                return
            if selected_mode == '登录':
                role = self.store.validate_user(username, password)
                if role is None:
                    QMessageBox.warning(dialog, '登录失败', '用户名或密码错误。')
                    return
                self.current_user = username
                self.current_role = role
            elif selected_mode == '注册':
                if not self.store.register_user(username, password, role_combo.currentText()):
                    QMessageBox.warning(dialog, '注册失败', '用户名已存在。')
                    return
                self.current_user = username
                self.current_role = role_combo.currentText()
            else:
                if not self.store.reset_password(username, password):
                    QMessageBox.warning(dialog, '重置失败', '用户名不存在。')
                    return
                self.current_user = username
                self.current_role = role_combo.currentText()
            self.store.set_state(current_user=self.current_user, current_role=self.current_role)
            dialog.accept()
        ok_btn.clicked.connect(apply_auth)
        btn_row.addWidget(guest_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)
        if dialog.exec_():
            self.account_chip.setText(f'账号：{self.current_user} / {self.current_role}')
            self.push_feed('SYSTEM', '账号状态已更新', f'当前登录用户：{self.current_user}，角色：{self.current_role}')

    def open_history_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('历史记录')
        dialog.setModal(True)
        dialog.resize(720, 520)
        dialog.setStyleSheet(self._dialog_base_qss("QListWidget{background:#fbfcff;border-radius:14px;padding:10px;}"))
        reports_dir = self._ensure_report_dir()
        records_dir = os.path.join('assets', 'data', 'records')
        os.makedirs(records_dir, exist_ok=True)
        history_rows = self.store.list_history(self.current_user)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('历史记录')
        title.setObjectName('title')
        sub = QLabel('集中查看导出的成绩单、截图和录制文件。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        row = QHBoxLayout()
        row.setSpacing(14)
        history_card = QFrame()
        history_card.setObjectName('card')
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(16, 16, 16, 16)
        history_layout.setSpacing(10)
        history_label = QLabel('数据库历史')
        history_label.setObjectName('sub')
        history_list = QListWidget()
        for item in history_rows:
            history_list.addItem(f"{item['created_at']} | {item['dance_type']} | {item['avg_score']:.1f} | {item['grade']}")
        history_layout.addWidget(history_label)
        history_layout.addWidget(history_list)
        report_card = QFrame()
        report_card.setObjectName('card')
        report_layout = QVBoxLayout(report_card)
        report_layout.setContentsMargins(16, 16, 16, 16)
        report_layout.setSpacing(10)
        report_label = QLabel('成绩单与截图')
        report_label.setObjectName('sub')
        report_list = QListWidget()
        for path in sorted(os.listdir(reports_dir), reverse=True):
            report_list.addItem(path)
        report_layout.addWidget(report_label)
        report_layout.addWidget(report_list)
        record_card = QFrame()
        record_card.setObjectName('card')
        record_layout = QVBoxLayout(record_card)
        record_layout.setContentsMargins(16, 16, 16, 16)
        record_layout.setSpacing(10)
        record_label = QLabel('录制文件')
        record_label.setObjectName('sub')
        record_list = QListWidget()
        for path in sorted(os.listdir(records_dir), reverse=True):
            record_list.addItem(path)
        record_layout.addWidget(record_label)
        record_layout.addWidget(record_list)
        row.addWidget(history_card, 1)
        row.addWidget(report_card, 1)
        row.addWidget(record_card, 1)
        layout.addLayout(row)
        btn_row = QHBoxLayout()
        detail_btn = QPushButton('查看选中详情')
        detail_btn.setObjectName('ghost')
        open_reports = QPushButton('打开成绩目录')
        open_reports.setObjectName('ghost')
        open_records = QPushButton('打开录制目录')
        open_records.setObjectName('ghost')
        close_btn = QPushButton('关闭')
        def open_selected_detail():
            history_row = history_list.currentRow()
            if 0 <= history_row < len(history_rows):
                row_data = history_rows[history_row]
                detail_path = row_data['summary_report'] or row_data['summary_image'] or ''
                if detail_path and os.path.exists(detail_path):
                    self.open_history_detail_dialog(detail_path)
                    return
            if report_list.currentItem():
                self.open_history_detail_dialog(os.path.join(reports_dir, report_list.currentItem().text()))
                return
            if record_list.currentItem():
                self.open_history_detail_dialog(os.path.join(records_dir, record_list.currentItem().text()))
                return
            QMessageBox.information(dialog, '历史记录', '请先选择一条历史、成绩单或录制文件。')
        detail_btn.clicked.connect(open_selected_detail)
        open_reports.clicked.connect(lambda: self._open_summary_dir())
        open_records.clicked.connect(self._open_record_folder)
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(detail_btn)
        btn_row.addWidget(open_reports)
        btn_row.addWidget(open_records)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec_()

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('设置 / 关于')
        dialog.setModal(True)
        dialog.resize(520, 360)
        dialog.setStyleSheet(self._dialog_base_qss())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('设置 / 关于')
        title.setObjectName('title')
        sub = QLabel('本地桌面版设置。适合答辩展示和演示机部署。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setHorizontalSpacing(12)
        card_layout.setVerticalSpacing(12)
        sound_label = QLabel('判定音效')
        sound_label.setObjectName('key')
        sound_combo = QComboBox()
        sound_combo.addItems(['开启', '关闭'])
        sound_combo.setCurrentText(self.app_settings['sound'])
        export_label = QLabel('自动导出')
        export_label.setObjectName('key')
        export_combo = QComboBox()
        export_combo.addItems(['开启', '关闭'])
        export_combo.setCurrentText(self.app_settings['auto_export'])
        theme_label = QLabel('主题')
        theme_label.setObjectName('key')
        theme_combo = QComboBox()
        theme_combo.addItems(['Apple Light'])
        theme_combo.setCurrentText(self.app_settings['theme'])
        about_label = QLabel('关于')
        about_label.setObjectName('key')
        about_value = QLabel('民族舞智能评估系统 v1.0\\n多模态展示前端 + Rebocap 实时评分 + 导出结算')
        about_value.setObjectName('sub')
        about_value.setWordWrap(True)
        card_layout.addWidget(sound_label, 0, 0)
        card_layout.addWidget(sound_combo, 0, 1)
        card_layout.addWidget(export_label, 1, 0)
        card_layout.addWidget(export_combo, 1, 1)
        card_layout.addWidget(theme_label, 2, 0)
        card_layout.addWidget(theme_combo, 2, 1)
        card_layout.addWidget(about_label, 3, 0)
        card_layout.addWidget(about_value, 3, 1)
        layout.addWidget(card)
        save_btn = QPushButton('保存设置')
        save_btn.clicked.connect(dialog.accept)
        layout.addWidget(save_btn, 0, Qt.AlignRight)
        if dialog.exec_():
            self.app_settings['sound'] = sound_combo.currentText()
            self.app_settings['auto_export'] = export_combo.currentText()
            self.app_settings['theme'] = theme_combo.currentText()
            self.push_feed('SYSTEM', '设置已更新', f"音效：{self.app_settings['sound']}，自动导出：{self.app_settings['auto_export']}")

    def open_profile_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('用户中心')
        dialog.setModal(True)
        dialog.resize(500, 340)
        dialog.setStyleSheet(self._dialog_base_qss("QLabel#val{font-size:18px;}"))
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('用户中心')
        title.setObjectName('title')
        sub = QLabel('当前演示版仅维护本地会话信息。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        rows = [
            ('当前账号', self.current_user),
            ('当前角色', self.current_role),
            ('默认舞种', self.current_dance_type),
            ('音效设置', self.app_settings['sound']),
            ('自动导出', self.app_settings['auto_export']),
            ('模型状态', self.metric_model.text()),
        ]
        for idx, (k, v) in enumerate(rows):
            key = QLabel(k)
            key.setObjectName('key')
            val = QLabel(v)
            val.setObjectName('val')
            grid.addWidget(key, idx, 0)
            grid.addWidget(val, idx, 1)
        layout.addWidget(card)
        btn = QPushButton('关闭')
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, 0, Qt.AlignRight)
        dialog.exec_()

    def open_welcome_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('欢迎使用')
        dialog.setModal(True)
        dialog.resize(620, 360)
        dialog.setStyleSheet(self._dialog_base_qss("QLabel#title{font-size:30px;font-weight:900;color:white;} QLabel#sub{font-size:14px;color:rgba(255,255,255,0.92);} QLabel#cardTitle{font-size:18px;font-weight:800;color:#101426;} QLabel#hint{font-size:13px;color:#4d5670;}"))
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        hero = QFrame()
        hero.setObjectName('hero')
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(20, 20, 20, 20)
        hero_layout.setSpacing(8)
        title = QLabel('民族舞智能评估系统')
        title.setObjectName('title')
        sub = QLabel('虚拟摄像头展示、Rebocap 实时评分、导出结算、历史与管理页面已集成。')
        sub.setObjectName('sub')
        sub.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(sub)
        layout.addWidget(hero)
        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(8)
        card_title = QLabel('快速开始')
        card_title.setObjectName('cardTitle')
        hint = QLabel('1. 账号登录\\n2. 选择舞种和摄像头\\n3. 启动 Rebocap 与虚拟摄像头\\n4. 点击“开始舞蹈”\\n5. 停止后查看结算与历史记录')
        hint.setObjectName('hint')
        hint.setWordWrap(True)
        card_layout.addWidget(card_title)
        card_layout.addWidget(hint)
        layout.addWidget(card)
        btn = QPushButton('进入系统')
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, 0, Qt.AlignRight)
        dialog.exec_()

    def open_history_detail_dialog(self, path: str):
        if not path or not os.path.exists(path):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('历史详情')
        dialog.setModal(True)
        dialog.resize(640, 460)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;} QLabel#text{font-size:13px;color:#22304d;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
            "QPushButton#ghost{color:#172033;background:#E9EEF8;border:1px solid rgba(0,0,0,0.06);}"
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('历史详情')
        title.setObjectName('title')
        sub = QLabel(path)
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        text = QLabel()
        text.setObjectName('text')
        text.setWordWrap(True)
        if path.lower().endswith('.txt'):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            text.setText(content[:2400] or '空文件')
        else:
            stat = os.stat(path)
            text.setText(f'文件名：{os.path.basename(path)}\n大小：{stat.st_size} bytes\n路径：{path}')
        card_layout.addWidget(text)
        layout.addWidget(card, 1)
        btn_row = QHBoxLayout()
        open_btn = QPushButton('打开文件')
        open_btn.setObjectName('ghost')
        open_btn.clicked.connect(lambda: self._open_path(path))
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(open_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec_()

    def open_history_filter_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('历史筛选')
        dialog.setModal(True)
        dialog.resize(720, 520)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;} QLabel#key{font-size:12px;color:#7b8193;font-weight:700;}"
            "QLineEdit,QComboBox{background:#F2F2F7;color:#1d1d1f;border:1px solid rgba(0,0,0,0.06);border-radius:16px;padding:8px 12px;min-height:34px;}"
            "QListWidget{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;padding:12px;} QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
            "QPushButton#ghost{color:#172033;background:#E9EEF8;border:1px solid rgba(0,0,0,0.06);}"
        )
        history_rows = self.store.list_history(None if self.current_role in {'教师', '管理员'} else self.current_user)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('历史筛选')
        title.setObjectName('title')
        sub = QLabel('按关键字、舞种和日期片段筛选导出记录。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        filters = QHBoxLayout()
        keyword = QLineEdit()
        keyword.setPlaceholderText('关键字 / 文件名')
        dance = QComboBox()
        dance.addItems(['全部', '黑走马', '木卡姆'])
        date_input = QLineEdit()
        date_input.setPlaceholderText('日期片段，如 20260316')
        filters.addWidget(keyword, 2)
        filters.addWidget(dance, 1)
        filters.addWidget(date_input, 1)
        layout.addLayout(filters)
        result_list = QListWidget()
        layout.addWidget(result_list, 1)
        filtered_rows = []
        def apply_filter():
            filtered_rows.clear()
            result_list.clear()
            kw = keyword.text().strip().lower()
            date_kw = date_input.text().strip().lower()
            dance_kw = dance.currentText()
            for row_data in history_rows:
                name = f"{row_data['created_at']} {row_data['dance_type']} {row_data['grade']} {row_data['username']}".lower()
                if kw and kw not in name:
                    continue
                if date_kw and date_kw not in row_data['created_at'].replace('-', '').replace(':', '').replace(' ', ''):
                    continue
                if dance_kw != '全部' and dance_kw not in row_data['dance_type']:
                    continue
                filtered_rows.append(row_data)
                result_list.addItem(f"{row_data['id']} | {row_data['created_at']} | {row_data['dance_type']} | {row_data['avg_score']:.1f}")
        apply_filter()
        keyword.textChanged.connect(lambda _: apply_filter())
        date_input.textChanged.connect(lambda _: apply_filter())
        dance.currentTextChanged.connect(lambda _: apply_filter())
        btn_row = QHBoxLayout()
        open_btn = QPushButton('查看详情')
        open_btn.setObjectName('ghost')
        def open_selected_history():
            row_index = result_list.currentRow()
            if row_index < 0 or row_index >= len(filtered_rows):
                QMessageBox.information(dialog, '历史详情', '请先选择一条历史记录。')
                return
            row_data = filtered_rows[row_index]
            detail_path = row_data['summary_report'] or row_data['summary_image'] or ''
            if detail_path and os.path.exists(detail_path):
                self.open_history_detail_dialog(detail_path)
                return
            QMessageBox.information(dialog, '历史详情', '该记录暂无可打开的成绩单或截图。')
        open_btn.clicked.connect(open_selected_history)
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(open_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec_()

    def open_model_manager_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('模型管理')
        dialog.setModal(True)
        dialog.resize(560, 360)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#key{font-size:12px;color:#7b8193;font-weight:700;} QLabel#val{font-size:16px;color:#15203a;font-weight:800;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('模型管理')
        title.setObjectName('title')
        layout.addWidget(title)
        card = QFrame()
        card.setObjectName('card')
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        rows = [
            ('当前舞种', self.current_dance_type),
            ('模型状态', self.metric_model.text()),
            ('权重路径', os.path.join('assets', 'weights', 'best_dance_scoring.ckpt')),
            ('权重存在', '是' if os.path.exists(os.path.join('assets', 'weights', 'best_dance_scoring.ckpt')) else '否'),
        ]
        for idx, (k, v) in enumerate(rows):
            key = QLabel(k)
            key.setObjectName('key')
            val = QLabel(v)
            val.setWordWrap(True)
            val.setObjectName('val')
            grid.addWidget(key, idx, 0)
            grid.addWidget(val, idx, 1)
        layout.addWidget(card)
        btn = QPushButton('关闭')
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, 0, Qt.AlignRight)
        dialog.exec_()

    def open_device_diag_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('设备诊断')
        dialog.setModal(True)
        dialog.resize(560, 380)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#key{font-size:12px;color:#7b8193;font-weight:700;} QLabel#val{font-size:15px;color:#15203a;font-weight:800;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('设备诊断')
        title.setObjectName('title')
        layout.addWidget(title)
        card = QFrame()
        card.setObjectName('card')
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        rows = [
            ('摄像头索引', self.current_camera_index),
            ('VMC Host', self.current_vmc_host),
            ('VMC Port', self.current_vmc_port),
            ('视频状态', '已连接' if self.video_ready else '未连接'),
            ('骨骼状态', '已连接' if self.mocap_ready else '未连接'),
            ('会话状态', '运行中' if self.session_active else '待机'),
        ]
        for idx, (k, v) in enumerate(rows):
            key = QLabel(k)
            key.setObjectName('key')
            val = QLabel(v)
            val.setObjectName('val')
            grid.addWidget(key, idx, 0)
            grid.addWidget(val, idx, 1)
        layout.addWidget(card)
        btn = QPushButton('关闭')
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, 0, Qt.AlignRight)
        dialog.exec_()

    def open_motion_library_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('标准动作库')
        dialog.setModal(True)
        dialog.resize(560, 400)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;}"
            "QListWidget{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;padding:12px;} QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('标准动作库')
        title.setObjectName('title')
        sub = QLabel('当前项目内可直接调用的标准动作与素材列表。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        file_list = QListWidget()
        for path in self._list_dir_items(os.path.join('assets', 'data'), ['.bvh', '.npy']):
            file_list.addItem(os.path.basename(path))
        layout.addWidget(file_list, 1)
        btn_row = QHBoxLayout()
        detail_btn = QPushButton('查看动作详情')
        detail_btn.clicked.connect(lambda: self.open_motion_detail_dialog(os.path.join('assets', 'data', file_list.currentItem().text())) if file_list.currentItem() else None)
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(detail_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec_()

    def open_motion_detail_dialog(self, path: str):
        if not path or not os.path.exists(path):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('标准动作详情')
        dialog.setModal(True)
        dialog.resize(620, 420)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;} QLabel#key{font-size:12px;color:#7b8193;font-weight:700;} QLabel#val{font-size:15px;color:#15203a;font-weight:800;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
        )
        stat = os.stat(path)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('标准动作详情')
        title.setObjectName('title')
        sub = QLabel(os.path.basename(path))
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        rows = [
            ('文件路径', path),
            ('文件大小', f'{stat.st_size} bytes'),
            ('文件类型', os.path.splitext(path)[1]),
            ('建议用途', '可作为标准动作样本或答辩演示素材'),
        ]
        for idx, (k, v) in enumerate(rows):
            key = QLabel(k)
            key.setObjectName('key')
            val = QLabel(v)
            val.setWordWrap(True)
            val.setObjectName('val')
            grid.addWidget(key, idx, 0)
            grid.addWidget(val, idx, 1)
        layout.addWidget(card)
        preview_card = QFrame()
        preview_card.setObjectName('card')
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        preview_layout.setSpacing(10)
        preview_title = QLabel('文件预览')
        preview_title.setObjectName('key')
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        if path.lower().endswith('.bvh'):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                preview_text.setPlainText(f.read(3000) or '空文件')
        elif path.lower().endswith('.npy'):
            arr = np.load(path, allow_pickle=True)
            preview_text.setPlainText(
                f"shape: {arr.shape}\ndtype: {arr.dtype}\nmin: {np.min(arr):.4f}\nmax: {np.max(arr):.4f}\nmean: {np.mean(arr):.4f}"
            )
        else:
            preview_text.setPlainText('当前文件类型不支持预览。')
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(preview_text)
        layout.addWidget(preview_card)
        btn = QPushButton('关闭')
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, 0, Qt.AlignRight)
        dialog.exec_()

    def open_teacher_feedback_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('教师评语')
        dialog.setModal(True)
        dialog.resize(620, 420)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;} QLabel#text{font-size:14px;color:#22304d;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
        )
        avg_score = (sum(self.score_history) / len(self.score_history)) if self.score_history else 0.0
        if avg_score >= 90:
            comment = '整体表现非常稳定，动作完成度高，建议保持当前节奏与神态表达。'
        elif avg_score >= 80:
            comment = '整体表现良好，建议继续提升高光动作的爆发力与手臂延展。'
        elif avg_score >= 70:
            comment = '基础节奏已经建立，建议重点强化动作幅度和重心控制。'
        else:
            comment = '建议从标准动作分解练习开始，优先纠正节奏和关键姿态。'
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(24, 24, 24, 24)
        dialog_layout.setSpacing(16)
        title = QLabel('教师评语')
        title.setObjectName('title')
        sub = QLabel('基于当前评分统计自动生成，可用于答辩展示。')
        sub.setObjectName('sub')
        dialog_layout.addWidget(title)
        dialog_layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        text = QTextEdit()
        text.setObjectName('text')
        existing = self.store.latest_comment(self.current_user, self.current_dance_type)
        text.setPlainText(existing or f'当前账号：{self.current_user}\\n当前舞种：{self.current_dance_type}\\n平均得分：{avg_score:.1f}\\n\\n评语：{comment}')
        text.setReadOnly(self.current_role not in {'教师', '管理员'})
        card_layout.addWidget(text)
        dialog_layout.addWidget(card, 1)
        btn_row = QHBoxLayout()
        save_btn = QPushButton('保存评语')
        save_btn.setEnabled(self.current_role in {'教师', '管理员'})
        def save_comment():
            content = text.toPlainText().strip()
            if not content:
                QMessageBox.information(dialog, '教师评语', '评语内容不能为空。')
                return
            self.store.save_comment(self.current_user, self.current_role, self.current_dance_type, content)
            self.push_feed('SYSTEM', '评语已保存', f'{self.current_user} / {self.current_dance_type}')
            dialog.accept()
        save_btn.clicked.connect(save_comment)
        btn = QPushButton('关闭')
        btn.clicked.connect(dialog.accept)
        btn_row.addWidget(save_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(btn)
        dialog_layout.addLayout(btn_row)
        dialog.exec_()

    def open_import_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('数据导入')
        dialog.setModal(True)
        dialog.resize(620, 320)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;}"
            "QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;} QLabel#path{font-size:13px;color:#22304d;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
            "QPushButton#ghost{color:#172033;background:#E9EEF8;border:1px solid rgba(0,0,0,0.06);}"
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('数据导入')
        title.setObjectName('title')
        sub = QLabel('支持手动导入 BVH / NPY / 视频路径，并记录到战报流。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        path_label = QLabel('尚未选择文件')
        path_label.setObjectName('path')
        path_label.setWordWrap(True)
        card_layout.addWidget(path_label)
        layout.addWidget(card)
        btn_row = QHBoxLayout()
        pick_btn = QPushButton('选择文件')
        pick_btn.setObjectName('ghost')
        imported = {'path': ''}
        def pick_file():
            path, _ = QFileDialog.getOpenFileName(dialog, '选择文件', os.getcwd(), 'Data Files (*.bvh *.npy *.mp4 *.avi);;All Files (*)')
            if path:
                path_label.setText(path)
                imported['path'] = path
        pick_btn.clicked.connect(pick_file)
        import_btn = QPushButton('导入到系统')
        def do_import():
            if not imported['path']:
                QMessageBox.information(dialog, '数据导入', '请先选择一个文件。')
                return
            imports_dir = os.path.join('assets', 'imports')
            stored_path = self.store.save_import(self.current_user, self.current_role, imported['path'], imports_dir)
            self.current_import_path = stored_path
            self.store.set_state(last_import_path=stored_path)
            self.push_feed('SYSTEM', '导入文件', stored_path)
            dialog.accept()
        import_btn.clicked.connect(do_import)
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(pick_btn)
        btn_row.addWidget(import_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec_()

    def open_result_analysis_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('结果分析')
        dialog.setModal(True)
        dialog.resize(580, 420)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;}"
            "QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;} QLabel#key{font-size:12px;color:#7b8193;font-weight:700;} QLabel#val{font-size:16px;color:#15203a;font-weight:800;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
        )
        avg_score = (sum(self.score_history) / len(self.score_history)) if self.score_history else 0.0
        total_hits = sum(self.judge_stats.values())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('结果分析')
        title.setObjectName('title')
        sub = QLabel('当前会话的统计摘要与可答辩化表述。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        rows = [
            ('平均分', f'{avg_score:.1f}'),
            ('最高连击', str(self.best_combo)),
            ('总判定数', str(total_hits)),
            ('最佳判定', max(self.judge_stats, key=self.judge_stats.get) if total_hits else '无'),
            ('分析建议', '可结合历史详情和成绩单继续做分段分析'),
        ]
        for idx, (k, v) in enumerate(rows):
            key = QLabel(k)
            key.setObjectName('key')
            val = QLabel(v)
            val.setWordWrap(True)
            val.setObjectName('val')
            grid.addWidget(key, idx, 0)
            grid.addWidget(val, idx, 1)
        layout.addWidget(card)
        btn = QPushButton('关闭')
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, 0, Qt.AlignRight)
        dialog.exec_()

    def open_admin_dialog(self):
        if self.current_role != '管理员':
            QMessageBox.warning(self, '权限不足', '管理后台仅允许管理员访问。')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('管理后台')
        dialog.setModal(True)
        dialog.resize(580, 420)
        dialog.setStyleSheet(
            "QDialog{background:#f7f8fc;} QLabel#title{font-size:24px;font-weight:800;color:#101426;} QLabel#sub{font-size:13px;color:#6a7288;}"
            "QFrame#card{background:white;border:1px solid rgba(0,0,0,0.06);border-radius:18px;} QLabel#key{font-size:12px;color:#7b8193;font-weight:700;} QLabel#val{font-size:16px;color:#15203a;font-weight:800;}"
            "QPushButton{min-height:38px;padding:0 18px;border-radius:19px;font-size:14px;font-weight:700;color:white;background:#0071e3;}"
        )
        report_count = len(self._list_dir_items(os.path.join('assets', 'reports')))
        record_count = len(self._list_dir_items(os.path.join('assets', 'data', 'records')))
        user_count = len(self.store.list_users())
        history_count = len(self.store.list_history())
        import_count = len(self.store.list_imports())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel('管理后台')
        title.setObjectName('title')
        sub = QLabel('桌面演示版的本地资源与导出统计。')
        sub.setObjectName('sub')
        layout.addWidget(title)
        layout.addWidget(sub)
        card = QFrame()
        card.setObjectName('card')
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        rows = [
            ('当前账号', self.current_user),
            ('用户数量', str(user_count)),
            ('历史入库', str(history_count)),
            ('导入记录', str(import_count)),
            ('成绩单数量', str(report_count)),
            ('录制文件数量', str(record_count)),
            ('权重文件', '已加载' if os.path.exists(os.path.join('assets', 'weights', 'best_dance_scoring.ckpt')) else '缺失'),
            ('标准动作库', str(len(self._list_dir_items(os.path.join('assets', 'data'), ['.bvh', '.npy'])))),
        ]
        for idx, (k, v) in enumerate(rows):
            key = QLabel(k)
            key.setObjectName('key')
            val = QLabel(v)
            val.setObjectName('val')
            grid.addWidget(key, idx, 0)
            grid.addWidget(val, idx, 1)
        layout.addWidget(card)
        btn = QPushButton('关闭')
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, 0, Qt.AlignRight)
        dialog.exec_()

    def _flash_judge(self, rank: str):
        start, end = self._rank_colors(rank)
        self.judge_label.setText(rank)
        self.judge_label.setStyleSheet(
            f"QLabel#judgeLabel{{color:#ffffff;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {start}, stop:1 {end});"
            "border:1px solid rgba(255,255,255,0.32);border-radius:20px;padding:10px 18px;font-size:28px;font-weight:900;letter-spacing:0.12em;}}"
        )
        self.judge_label.show()
        self.reposition_combo()
        opacity = QGraphicsOpacityEffect(self.judge_label)
        opacity.setOpacity(0.0)
        self.judge_label.setGraphicsEffect(opacity)
        fade = QPropertyAnimation(opacity, b'opacity', self.judge_label)
        fade.setDuration(520)
        fade.setKeyValueAt(0.0, 0.0)
        fade.setKeyValueAt(0.2, 1.0)
        fade.setKeyValueAt(0.75, 1.0)
        fade.setKeyValueAt(1.0, 0.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        self.ui_animations.append(fade)
        fade.finished.connect(self.judge_label.hide)
        fade.finished.connect(self._clear_ui_animations)
        fade.start()

    def _flash_pulse(self, rank: str):
        start, _ = self._rank_colors(rank)
        self.pulse_overlay.setStyleSheet(
            f"QFrame#pulseOverlay{{background:transparent;border:3px solid {start};border-radius:28px;}}"
        )
        self.pulse_overlay.show()
        opacity = QGraphicsOpacityEffect(self.pulse_overlay)
        opacity.setOpacity(0.0)
        self.pulse_overlay.setGraphicsEffect(opacity)
        fade = QPropertyAnimation(opacity, b'opacity', self.pulse_overlay)
        fade.setDuration(360)
        fade.setKeyValueAt(0.0, 0.0)
        fade.setKeyValueAt(0.25, 0.95)
        fade.setKeyValueAt(1.0, 0.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        self.ui_animations.append(fade)
        fade.finished.connect(self.pulse_overlay.hide)
        fade.finished.connect(self._clear_ui_animations)
        fade.start()

    def _bounce_combo(self):
        self.combo_label.adjustSize()
        base = QPoint(22, max(22, self.video.height() - self.combo_label.height() - 54))
        self.combo_label.move(base)
        bounce = QPropertyAnimation(self.combo_label, b'pos', self.combo_label)
        bounce.setDuration(260)
        bounce.setKeyValueAt(0.0, base + QPoint(0, 18))
        bounce.setKeyValueAt(0.55, base + QPoint(0, -8))
        bounce.setKeyValueAt(1.0, base)
        bounce.setEasingCurve(QEasingCurve.OutBack)
        self.ui_animations.append(bounce)
        bounce.finished.connect(self._clear_ui_animations)
        bounce.start()

    def _build_ui(self):
        central = AuroraPanel(self)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(0)
        shell = QWidget()
        shell.setMaximumWidth(1320)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(24)
        root.addStretch(1)
        root.addWidget(shell, 0)
        root.addStretch(1)

        brand = QWidget()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(8)
        eyebrow = QLabel('民族舞智能评估系统')
        eyebrow.setObjectName('eyebrow')
        hero_title = QLabel('实时评估控制台')
        hero_title.setObjectName('heroTitle')
        hero_desc = QLabel('虚拟摄像头只负责展示，Rebocap 骨骼流负责实时评分。界面按稳定布局重排，避免控件拥挤错位。')
        hero_desc.setObjectName('heroSubtitle')
        hero_desc.setWordWrap(True)
        brand_layout.addWidget(eyebrow)
        brand_layout.addWidget(hero_title)
        brand_layout.addWidget(hero_desc)

        self.combo = QComboBox()
        self.combo.addItems(['黑走马 (Kara Jorga)', '木卡姆 (Muqam)'])
        self.cam_combo = QComboBox()
        self.btn_scan = QPushButton('刷新设备')
        self.btn_scan.setObjectName('secondaryButton')
        self.btn_scan.clicked.connect(self.refresh_cameras)
        self.vmc_host = QLineEdit('0.0.0.0')
        self.vmc_port = QLineEdit('39539')
        self.lcd = QLCDNumber()
        self.lcd.setDigitCount(5)
        self.lcd.setSegmentStyle(QLCDNumber.Flat)
        self.lcd.setObjectName('timeDisplay')
        self.btn_start = QPushButton('开始舞蹈')
        self.btn_start.setObjectName('primaryButton')
        self.btn_stop = QPushButton('停止评估')
        self.btn_stop.setObjectName('secondaryButton')
        self.btn_login = QPushButton('账号登录')
        self.btn_login.setObjectName('secondaryButton')
        self.btn_login.clicked.connect(self.open_login_dialog)
        self.btn_history = QPushButton('历史记录')
        self.btn_history.setObjectName('secondaryButton')
        self.btn_history.clicked.connect(self.open_history_dialog)
        self.btn_settings = QPushButton('设置/关于')
        self.btn_settings.setObjectName('secondaryButton')
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self.start_system)
        self.btn_stop.clicked.connect(self.stop_system)
        self.account_chip = QLabel(f'账号：{self.current_user} / {self.current_role}')
        self.account_chip.setObjectName('metricChip')

        top_main = GlassCard()
        top_main_layout = QHBoxLayout(top_main)
        top_main_layout.setContentsMargins(28, 22, 28, 22)
        top_main_layout.setSpacing(20)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        for btn in [self.btn_start, self.btn_stop, self.btn_scan, self.btn_login, self.btn_history, self.btn_settings]:
            action_row.addWidget(btn)
        action_row.addStretch(1)
        top_main_layout.addWidget(brand, 1)
        top_main_layout.addLayout(action_row, 1)
        shell_layout.addWidget(top_main)

        top_info = GlassCard()
        top_info_layout = QGridLayout(top_info)
        top_info_layout.setContentsMargins(24, 18, 24, 18)
        top_info_layout.setHorizontalSpacing(12)
        top_info_layout.setVerticalSpacing(10)
        info_items = [
            ('舞种', self.combo),
            ('摄像头', self.cam_combo),
            ('VMC Host', self.vmc_host),
            ('VMC Port', self.vmc_port),
            ('计时', self.lcd),
            ('账号状态', self.account_chip),
        ]
        for idx, (title, widget) in enumerate(info_items):
            block = QWidget()
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(4)
            label = QLabel(title)
            label.setObjectName('fieldLabel')
            block_layout.addWidget(label)
            block_layout.addWidget(widget)
            top_info_layout.addWidget(block, 0 if idx < 3 else 1, idx % 3)
        shell_layout.addWidget(top_info)

        body = QHBoxLayout()
        body.setSpacing(24)

        video_card = GlassCard()
        video_layout = QVBoxLayout(video_card)
        video_layout.setContentsMargins(24, 24, 24, 24)
        video_layout.setSpacing(16)
        video_head = QHBoxLayout()
        video_title_box = QVBoxLayout()
        video_title_box.setContentsMargins(0, 0, 0, 0)
        video_title_box.setSpacing(4)
        video_title = QLabel('实时展示画面')
        video_title.setObjectName('sectionTitle')
        video_subtitle = QLabel('默认显示虚拟摄像头视频；若视频断开，则自动回退骨骼预览。')
        video_subtitle.setObjectName('sectionNote')
        video_title_box.addWidget(video_title)
        video_title_box.addWidget(video_subtitle)
        self.camera_hint = QLabel('等待视频与骨骼输入')
        self.camera_hint.setObjectName('statusPill')
        video_head.addLayout(video_title_box)
        video_head.addStretch(1)
        video_head.addWidget(self.camera_hint)
        self.video = QLabel('点击“开始舞蹈”连接视频与骨骼流')
        self.video.setObjectName('videoSurface')
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(760, 540)
        self.perfect_label = QLabel('PERFECT!', self.video)
        self.perfect_label.setObjectName('perfectLabel')
        self.perfect_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.perfect_label.hide()
        self.judge_label = QLabel('PERFECT', self.video)
        self.judge_label.setObjectName('judgeLabel')
        self.judge_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.judge_label.hide()
        self.combo_label = QLabel('COMBO x0', self.video)
        self.combo_label.setObjectName('comboLabel')
        self.combo_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.combo_label.hide()
        self.combo_bar = QProgressBar(self.video)
        self.combo_bar.setObjectName('comboBar')
        self.combo_bar.setRange(0, 100)
        self.combo_bar.setTextVisible(False)
        self.combo_bar.setValue(0)
        self.combo_bar.hide()
        self.pulse_overlay = QFrame(self.video)
        self.pulse_overlay.setObjectName('pulseOverlay')
        self.pulse_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.pulse_overlay.hide()
        video_layout.addLayout(video_head)
        video_layout.addWidget(self.video, 1)

        right_scroll = QScrollArea()
        right_scroll.setObjectName('sideScroll')
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 8, 0)
        right_layout.setSpacing(18)

        score_card = GlassCard()
        score_card.setMinimumHeight(320)
        score_card.setMaximumHeight(360)
        score_layout = QVBoxLayout(score_card)
        score_layout.setContentsMargins(22, 22, 22, 22)
        score_layout.setSpacing(14)
        score_head = QLabel('评分总览')
        score_head.setObjectName('sectionTitle')
        score_note = QLabel('实时分数只来自 Rebocap。视频区域不参与主评分。')
        score_note.setObjectName('sectionNote')
        self.score_text = QLabel('当前得分：-')
        self.score_text.setObjectName('scoreDisplay')
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setObjectName('scoreBar')
        metric_wrap = QWidget()
        metric_layout = QGridLayout(metric_wrap)
        metric_layout.setContentsMargins(0, 0, 0, 0)
        metric_layout.setHorizontalSpacing(8)
        metric_layout.setVerticalSpacing(8)
        self.metric_mode = QLabel('舞种未启动')
        self.metric_mode.setObjectName('metricChip')
        self.metric_state = QLabel('系统待机')
        self.metric_state.setObjectName('metricChip')
        self.metric_model = QLabel('模型待加载')
        self.metric_model.setObjectName('metricChip')
        metric_layout.addWidget(self.metric_mode, 0, 0)
        metric_layout.addWidget(self.metric_state, 0, 1)
        metric_layout.addWidget(self.metric_model, 1, 0, 1, 2)
        score_layout.addWidget(score_head)
        score_layout.addWidget(score_note)
        score_layout.addWidget(self.score_text)
        score_layout.addWidget(self.bar)
        score_layout.addWidget(metric_wrap)
        stat_wrap = QWidget()
        stat_layout = QVBoxLayout(stat_wrap)
        stat_layout.setContentsMargins(0, 0, 0, 0)
        stat_layout.setSpacing(8)
        stat_title = QLabel('命中统计')
        stat_title.setObjectName('fieldLabel')
        stat_layout.addWidget(stat_title)
        self.stat_labels = {}
        self.stat_bars = {}
        for rank in ['PERFECT', 'GREAT', 'GOOD', 'WARN']:
            row = QHBoxLayout()
            row.setSpacing(8)
            chip = QLabel(rank)
            chip.setObjectName('statChip')
            bar = QProgressBar()
            bar.setObjectName('statBar')
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            count = QLabel('0')
            count.setObjectName('statValue')
            self.stat_labels[rank] = count
            self.stat_bars[rank] = bar
            row.addWidget(chip)
            row.addWidget(bar, 1)
            row.addWidget(count)
            stat_layout.addLayout(row)
        score_layout.addWidget(stat_wrap)

        log_card = GlassCard()
        log_card.setMinimumHeight(320)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(22, 22, 22, 22)
        log_layout.setSpacing(14)
        log_title = QLabel('舞台战报')
        log_title.setObjectName('sectionTitle')
        log_note = QLabel('游戏化提示流。新消息固定压在顶部。')
        log_note.setObjectName('sectionNote')
        self.feed = QListWidget()
        self.feed.setObjectName('feedPanel')
        self.feed.setSpacing(10)
        self.feed.setUniformItemSizes(False)
        self.feed.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.feed.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.feed.setFocusPolicy(Qt.NoFocus)
        self.feed.setMinimumHeight(260)
        log_layout.addWidget(log_title)
        log_layout.addWidget(log_note)
        log_layout.addWidget(self.feed, 1)

        work_card = GlassCard()
        work_card.setMinimumHeight(300)
        work_layout = QVBoxLayout(work_card)
        work_layout.setContentsMargins(22, 22, 22, 22)
        work_layout.setSpacing(14)
        work_title = QLabel('工作台')
        work_title.setObjectName('sectionTitle')
        work_note = QLabel('功能页面统一收纳到这里，避免主界面继续膨胀。')
        work_note.setObjectName('sectionNote')
        work_layout.addWidget(work_title)
        work_layout.addWidget(work_note)
        self.work_pages = QStackedWidget()
        nav_shell = QHBoxLayout()
        nav_shell.setSpacing(12)
        nav_rail = QVBoxLayout()
        nav_rail.setSpacing(8)
        page_defs = [
            ('业务', [
                ('用户中心', self.open_profile_dialog),
                ('历史筛选', self.open_history_filter_dialog),
                ('结果分析', self.open_result_analysis_dialog),
                ('教师评语', self.open_teacher_feedback_dialog),
            ]),
            ('资源', [
                ('标准动作库', self.open_motion_library_dialog),
                ('动作详情', lambda: self.open_motion_detail_dialog(os.path.join('assets', 'data', 'shifu.bvh'))),
                ('数据导入', self.open_import_dialog),
                ('历史记录', self.open_history_dialog),
            ]),
            ('系统', [
                ('模型管理', self.open_model_manager_dialog),
                ('设备诊断', self.open_device_diag_dialog),
                ('设置/关于', self.open_settings_dialog),
                ('管理后台', self.open_admin_dialog),
            ]),
        ]
        self.work_nav_buttons = []
        for page_index, (page_name, page_buttons) in enumerate(page_defs):
            nav_btn = QPushButton(page_name)
            nav_btn.setObjectName('segmentButton')
            nav_btn.clicked.connect(lambda _, idx=page_index: self._switch_work_page(idx))
            self.work_nav_buttons.append(nav_btn)
            nav_rail.addWidget(nav_btn)
            page = QWidget()
            page_grid = QGridLayout(page)
            page_grid.setContentsMargins(0, 0, 0, 0)
            page_grid.setHorizontalSpacing(10)
            page_grid.setVerticalSpacing(10)
            for btn_index, (label, handler) in enumerate(page_buttons):
                btn = QPushButton(label)
                btn.setObjectName('secondaryButton')
                btn.clicked.connect(handler)
                page_grid.addWidget(btn, btn_index // 2, btn_index % 2)
            self.work_pages.addWidget(page)
        nav_rail.addStretch(1)
        nav_shell.addLayout(nav_rail)
        nav_shell.addWidget(self.work_pages, 1)
        work_layout.addLayout(nav_shell)
        self._switch_work_page(0)

        right_layout.addWidget(score_card)
        right_layout.addWidget(log_card, 1)
        right_layout.addWidget(work_card)
        right_layout.addStretch(1)
        right_scroll.setWidget(right_panel)

        body.addWidget(video_card, 8)
        body.addWidget(right_scroll, 4)
        shell_layout.addLayout(body, 1)

    def _switch_work_page(self, index: int):
        if not hasattr(self, 'work_pages'):
            return
        self.work_pages.setCurrentIndex(index)
        for btn_index, btn in enumerate(getattr(self, 'work_nav_buttons', [])):
            btn.setProperty('active', btn_index == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _style(self):
        self.setStyleSheet("""
        QMainWindow { background: transparent; }
        QFrame#glassCard { background: rgba(255,255,255,0.80); border:1px solid rgba(255,255,255,0.64); border-radius:24px; }
        QLabel#eyebrow { color:#6d6d73; font-size:13px; font-weight:600; letter-spacing:0.06em; }
        QLabel#heroTitle { color:#1d1d1f; font-size:30px; font-weight:700; letter-spacing:-0.02em; }
        QLabel#heroSubtitle { color:#6e6e73; font-size:14px; }
        QLabel#fieldLabel { color:#86868b; font-size:12px; font-weight:600; }
        QLabel#sectionTitle { color:#1d1d1f; font-size:20px; font-weight:700; letter-spacing:-0.02em; }
        QLabel#sectionNote { color:#86868b; font-size:13px; }
        QLabel#scoreDisplay { color:#111111; font-size:38px; font-weight:700; letter-spacing:-0.03em; padding:4px 0 2px 0; }
        QLabel#statusPill, QLabel#metricChip { color:#3a3a3c; background:rgba(255,255,255,0.74); border:1px solid rgba(0,0,0,0.08); border-radius:16px; padding:7px 12px; font-size:12px; font-weight:600; }
        QLabel#statChip { color:#172033; background:rgba(245,247,255,0.95); border:1px solid rgba(0,0,0,0.06); border-radius:14px; padding:7px 10px; font-size:11px; font-weight:700; }
        QLabel#statValue { color:#38435d; font-size:12px; font-weight:800; min-width:28px; }
        QLabel#videoSurface { color:#8e8e93; background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(255,255,255,0.76),stop:1 rgba(244,246,250,0.92)); border:1px solid rgba(255,255,255,0.58); border-radius:28px; font-size:16px; }
        QLabel#perfectLabel { color:#ffffff; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 rgba(138,75,255,0.98),stop:1 rgba(31,200,255,0.94)); border:1px solid rgba(255,255,255,0.64); border-radius:24px; padding:12px 24px; font-size:34px; font-weight:800; letter-spacing:0.10em; }
        QLabel#judgeLabel { color:#ffffff; background:rgba(14,18,34,0.72); border:1px solid rgba(255,255,255,0.24); border-radius:20px; padding:10px 18px; font-size:28px; font-weight:900; letter-spacing:0.12em; }
        QLabel#comboLabel { color:#ffffff; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 rgba(13,20,38,0.78),stop:1 rgba(43,62,112,0.70)); border:1px solid rgba(255,255,255,0.22); border-radius:18px; padding:10px 16px; font-size:24px; font-weight:800; letter-spacing:0.06em; }
        QComboBox, QLineEdit { background:#F2F2F7; color:#1d1d1f; border:1px solid rgba(0,0,0,0.06); border-radius:16px; padding:7px 12px; min-height:32px; font-size:13px; }
        QComboBox:hover, QLineEdit:hover { background:#ffffff; }
        QComboBox:focus, QLineEdit:focus { background:#ffffff; border:1px solid rgba(0,113,227,0.24); }
        QComboBox::drop-down { border:none; width:24px; }
        QLCDNumber#timeDisplay, QLCDNumber { background:rgba(255,255,255,0.92); color:#1d1d1f; border:1px solid rgba(0,0,0,0.08); border-radius:16px; min-width:132px; min-height:42px; }
        QPushButton { min-height:36px; padding:0 16px; border-radius:18px; font-size:13px; font-weight:600; }
        QPushButton#primaryButton { color:white; background:#0071e3; border:1px solid rgba(0,113,227,0.20); }
        QPushButton#secondaryButton { color:#1d1d1f; background:#E5E5EA; border:1px solid rgba(0,0,0,0.05); }
        QPushButton#segmentButton { color:#3b455d; background:rgba(229,229,234,0.82); border:1px solid rgba(0,0,0,0.05); min-height:34px; padding:0 14px; border-radius:17px; }
        QPushButton#segmentButton[active="true"] { color:white; background:#0071e3; border:1px solid rgba(0,113,227,0.20); }
        QScrollArea#sideScroll { background:transparent; border:none; }
        QScrollArea#sideScroll QWidget { background:transparent; }
        QListWidget#feedPanel { background:rgba(255,255,255,0.54); border:1px solid rgba(0,0,0,0.06); border-radius:22px; padding:12px; outline:none; }
        QListWidget#feedPanel::item { border:none; margin:0px; padding:0px; }
        QProgressBar#scoreBar, QProgressBar { background:rgba(0,0,0,0.06); border:1px solid rgba(0,0,0,0.03); border-radius:14px; text-align:center; color:#4b4b4f; height:18px; font-size:12px; font-weight:600; }
        QProgressBar::chunk { border-radius:14px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6ad59d, stop:1 #39b67d); }
        QProgressBar#statBar { background:rgba(14,18,34,0.08); border:1px solid rgba(0,0,0,0.05); border-radius:8px; min-height:10px; max-height:10px; }
        QProgressBar#statBar::chunk { border-radius:8px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8B5CFF, stop:1 #1FC8FF); }
        QProgressBar#comboBar { background:rgba(10,14,24,0.30); border:1px solid rgba(255,255,255,0.18); border-radius:10px; }
        QProgressBar#comboBar::chunk { border-radius:10px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8B5CFF, stop:1 #1FC8FF); }
        QFrame#pulseOverlay { background:transparent; border:3px solid rgba(139,92,255,0.72); border-radius:28px; }
        """)
        self.setFont(QFont('Microsoft YaHei', 10))
    def start_system(self):
        if (self.camera_thread and self.camera_thread.isRunning()) or (self.mocap_thread and self.mocap_thread.isRunning()):
            return
        dance_type = self.combo.currentText()
        camera_index = int(self.cam_combo.currentText())
        host = self.vmc_host.text().strip() or '0.0.0.0'
        try:
            port = int(self.vmc_port.text().strip() or '39539')
        except ValueError:
            QMessageBox.warning(self, '端口错误', 'VMC 端口必须是整数。')
            return
        print(f'正在加载 {dance_type} 的 MindSpore 模型权重...')
        self.reset_view_state()
        self.current_dance_type = dance_type
        self.current_camera_index = str(camera_index)
        self.current_vmc_host = host
        self.current_vmc_port = str(port)
        self.push_feed('SYSTEM', f'载入 {dance_type}', f'视频索引 {camera_index}，Rebocap VMC {host}:{port}')
        self.metric_mode.setText(dance_type)
        self.metric_state.setText('连接中')
        self.camera_hint.setText(f'视频 {camera_index} / VMC {host}:{port} 连接中')
        self.camera_thread = CameraThread(camera_index=camera_index)
        self.camera_thread.opened_signal.connect(self.on_video_ready)
        self.camera_thread.frame_signal.connect(self.update_frame)
        self.camera_thread.error_signal.connect(self.on_camera_error)
        self.camera_thread.finished.connect(self.on_thread_finished)
        self.camera_thread.start()
        self.mocap_thread = MocapThread(dance_type=dance_type, host=host, port=port)
        self.metric_model.setText('真实模型' if self.mocap_thread.model_loaded else '降级评分')
        self.mocap_thread.opened_signal.connect(self.on_mocap_ready)
        self.mocap_thread.preview_signal.connect(self.on_mocap_preview)
        self.mocap_thread.score_signal.connect(self.update_score)
        self.mocap_thread.error_signal.connect(self.on_mocap_error)
        self.mocap_thread.saved_signal.connect(self.on_record_saved)
        self.mocap_thread.finished.connect(self.on_thread_finished)
        self.mocap_thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo.setEnabled(False)
        self.cam_combo.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.vmc_host.setEnabled(False)
        self.vmc_port.setEnabled(False)

    def on_video_ready(self):
        self.video_ready = True
        self._refresh_session_state()

    def on_mocap_ready(self):
        self.mocap_ready = True
        self._refresh_session_state()

    def _refresh_session_state(self):
        if self.video_ready and self.mocap_ready and not self.session_active:
            self.session_active = True
            self.elapsed_sec = 0
            self.update_lcd()
            self.timer.start()
            self.beat_timer.start()
            self.metric_state.setText('实时评估中')
            self.camera_hint.setText('视频展示已连接，Rebocap 骨骼流已连接')
            self.push_feed('SYSTEM', '双链路已就绪', '视频展示与骨骼评分已同步启动。')
        elif self.video_ready and not self.mocap_ready:
            self.camera_hint.setText('视频已连接，等待 Rebocap 骨骼流')
        elif self.mocap_ready and not self.video_ready:
            self.camera_hint.setText('Rebocap 骨骼流已连接，等待视频')

    def stop_system(self):
        self.timer.stop()
        self.beat_timer.stop()
        if self.camera_thread:
            self.camera_thread.stop()
        if self.mocap_thread:
            self.mocap_thread.stop()

    def on_camera_error(self, msg: str):
        self.push_feed('WARN', '视频输入异常', msg)
        QMessageBox.warning(self, '视频输入异常', msg)
        self.reset_view_state()
        self.stop_system()

    def on_mocap_error(self, msg: str):
        self.push_feed('WARN', 'Rebocap 输入异常', msg)
        QMessageBox.warning(self, 'Rebocap 输入异常', msg)
        self.reset_view_state()
        self.stop_system()

    def on_thread_finished(self):
        camera_done = self.camera_thread is None or not self.camera_thread.isRunning()
        mocap_done = self.mocap_thread is None or not self.mocap_thread.isRunning()
        if not (camera_done and mocap_done):
            return
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo.setEnabled(True)
        self.cam_combo.setEnabled(True)
        self.btn_scan.setEnabled(True)
        self.vmc_host.setEnabled(True)
        self.vmc_port.setEnabled(True)
        self.session_active = False
        self.video_ready = False
        self.mocap_ready = False
        self.camera_thread = None
        self.mocap_thread = None
        self.push_feed('SYSTEM', '评估已停止', '视频链路和骨骼链路都已安全关闭。')
        self._show_summary_dialog()

    def on_record_saved(self, text: str):
        self.last_record_text = text
        self.push_feed('SYSTEM', '录制已保存', text)

    def on_tick(self):
        self.elapsed_sec += 1
        self.update_lcd()

    def update_lcd(self):
        self.lcd.display(f'{self.elapsed_sec // 60:02d}:{self.elapsed_sec % 60:02d}')

    def update_frame(self, qimg: QImage):
        self.current_qimage = qimg
        self.render_video()

    def on_mocap_preview(self, joints: np.ndarray):
        if not self.video_ready:
            self.current_qimage = self._draw_skeleton_preview(joints)
            self.render_video()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.render_video()
        self.reposition_perfect()
        self.reposition_combo()

    def render_video(self):
        if self.current_qimage is None:
            return
        target_size = self.video.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        src = QPixmap.fromImage(self.current_qimage)
        scaled = src.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QPixmap(target_size)
        canvas.fill(QColor('#EEF1F6'))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        path = QPainterPath()
        path.addRoundedRect(QRectF(canvas.rect()), 28, 28)
        painter.setClipPath(path)
        x = (target_size.width() - scaled.width()) // 2
        y = (target_size.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
        painter.drawRoundedRect(QRectF(0.5, 0.5, target_size.width() - 1, target_size.height() - 1), 28, 28)
        painter.end()
        self.video.setPixmap(canvas)
    def _draw_skeleton_preview(self, joints: np.ndarray) -> QImage:
        width, height = 960, 720
        canvas = QPixmap(width, height)
        canvas.fill(QColor('#EEF1F6'))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(canvas.rect(), QColor('#EEF1F6'))
        if joints.size > 0:
            xy = joints[:, [0, 1]].astype(np.float32)
            xy[:, 1] *= -1.0
            mins = xy.min(axis=0)
            maxs = xy.max(axis=0)
            span = np.maximum(maxs - mins, 1e-4)
            scale = min((width * 0.70) / span[0], (height * 0.78) / span[1])
            center = (mins + maxs) / 2.0
            pts = (xy - center) * scale
            pts[:, 0] += width * 0.5
            pts[:, 1] += height * 0.56
            painter.setPen(QPen(QColor('#8D99AE'), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for idx, parent in self.PARENT_INDEX.items():
                if parent is None:
                    continue
                painter.drawLine(int(pts[parent, 0]), int(pts[parent, 1]), int(pts[idx, 0]), int(pts[idx, 1]))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#0071E3'))
            for x, y in pts:
                painter.drawEllipse(QPointF(float(x), float(y)), 8.0, 8.0)
        painter.setPen(QColor('#6E6E73'))
        painter.setFont(QFont('Microsoft YaHei', 13))
        painter.drawText(QRectF(0, 18, width, 40), Qt.AlignHCenter, 'Rebocap 实时骨骼预览')
        painter.end()
        return canvas.toImage()

    def reposition_perfect(self):
        self.perfect_label.move(max(0, (self.video.width() - self.perfect_label.width()) // 2), 22)

    def reposition_combo(self):
        self.combo_label.adjustSize()
        self.combo_label.move(22, max(22, self.video.height() - self.combo_label.height() - 54))
        self.combo_bar.setGeometry(22, self.video.height() - 24, min(220, self.video.width() - 44), 14)
        self.judge_label.adjustSize()
        self.judge_label.move(max(22, self.video.width() - self.judge_label.width() - 22), 22)
        self.pulse_overlay.setGeometry(0, 0, self.video.width(), self.video.height())

    def update_score(self, score: int, feedback: str):
        if not self.mocap_ready:
            return
        self.score_history.append(score)
        self.score_text.setText(f'当前得分：{score}')
        self.bar.setValue(score)
        if score < 70:
            chunk = ('#FF8A7A', '#FF5F57')
            state_text, rank, title = '动作偏差较大', 'WARN', f'动作偏差较大  {score}'
        elif score < 85:
            chunk = ('#FFD76A', '#FFB340')
            state_text, rank, title = '稳定推进中', 'GOOD', f'节奏保持稳定  {score}'
        elif score < 92:
            chunk = ('#71E0AF', '#32C27D')
            state_text, rank, title = '完成度很高', 'GREAT', f'动作完成度优秀  {score}'
        else:
            chunk = ('#8B5CFF', '#1FC8FF')
            state_text, rank, title = '高光表现', 'PERFECT', f'节奏爆点命中  {score}'
        self.metric_state.setText(state_text)
        self.judge_stats[rank] += 1
        self._refresh_stats()
        self.bar.setStyleSheet(
            'QProgressBar{background: rgba(0,0,0,0.06);border:1px solid rgba(0,0,0,0.03);border-radius:14px;text-align:center;color:#4b4b4f;height:18px;font-size:12px;font-weight:600;}'
            f'QProgressBar::chunk{{border-radius:14px;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {chunk[0]}, stop:1 {chunk[1]});}}'
        )
        if score >= 90:
            self.combo_count += 1
            self.combo_power = min(100, self.combo_power + 20)
        elif score >= 78:
            self.combo_power = max(0, self.combo_power - 8)
        else:
            self.combo_count = 0
            self.combo_power = 0
        self.best_combo = max(self.best_combo, self.combo_count)
        self.combo_label.setText(f'COMBO x{self.combo_count}')
        self.combo_bar.setValue(self.combo_power)
        if self.combo_count > 0:
            self.combo_label.show()
            self.combo_bar.show()
            self.reposition_combo()
            self._bounce_combo()
        else:
            self.combo_label.hide()
            self.combo_bar.hide()
        self.push_feed(rank, title, feedback)
        self._flash_judge(rank)
        self._flash_pulse(rank)
        self._play_judge_sound(rank)
        now = time.time()
        if score >= 90 and (now - self.last_perfect_time) >= self.COOLDOWN_SEC:
            self.perfect_label.show()
            self.perfect_label.adjustSize()
            self.reposition_perfect()
            QTimer.singleShot(1000, self.perfect_label.hide)
            self.last_perfect_time = now

    def closeEvent(self, event):
        self.stop_system()
        event.accept()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


