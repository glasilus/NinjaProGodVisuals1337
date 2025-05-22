import colorsys
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog,
    QLabel, QHBoxLayout, QSlider, QComboBox, QListWidget, QListWidgetItem
)

from core.audio_player import AudioPlayer
from core.visualizer import Visualizer


class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("NinjaProGodVisuals1337")
        self.resize(1000, 600)

        self.config = config
        self.player = AudioPlayer()
        self.is_playing = False
        self.visualizer = Visualizer(config)

        self.disco_hue = 0.0
        self.disco_speed = self.config.get("disco", {}).get("color_speed", 0.2)

        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout()

        # Верхняя панель с кнопками
        top_panel = QHBoxLayout()
        self.load_btn = QPushButton("Load")
        self.prev_btn = QPushButton("Prev")
        self.play_pause_btn = QPushButton("Play")
        self.stop_btn = QPushButton("Stop")  # Новая кнопка стоп
        self.next_btn = QPushButton("Next")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)

        self.load_btn.clicked.connect(self.load_audio_files)
        self.prev_btn.clicked.connect(self.play_prev)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.stop_btn.clicked.connect(self.stop_audio)  # Обработчик стопа
        self.next_btn.clicked.connect(self.play_next)
        self.seek_slider.sliderReleased.connect(self.seek_audio)

        top_panel.addWidget(self.load_btn)
        top_panel.addWidget(self.prev_btn)
        top_panel.addWidget(self.play_pause_btn)
        top_panel.addWidget(self.stop_btn)
        top_panel.addWidget(self.next_btn)
        top_panel.addWidget(self.seek_slider)
        main_layout.addLayout(top_panel)

        # График визуализации
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')

        # Фон и цвета для каждого режима из конфига
        self.bg_waveform = self.config["theme"].get("background_waveform", "#000000")
        self.bg_spectrum = self.config["theme"].get("background_spectrum", "#000000")

        self.plot_widget.setBackground(self.bg_waveform)

        pen_color = self.config["theme"].get("line_color", "#00FF00")
        self.plot = self.plot_widget.plot(pen=pg.mkPen(pen_color, width=2))
        self.zero_line = self.plot_widget.plot([], pen=pg.mkPen('w', width=0))

        fill_color = self.config["theme"].get("fill_color", [0, 255, 0, 80])
        self.fill_item = pg.FillBetweenItem(self.plot, self.zero_line,
                                            brush=pg.mkBrush(*fill_color))
        self.plot_widget.addItem(self.fill_item)
        self.fill_item.setVisible(False)

        main_layout.addWidget(self.plot_widget)

        # Нижняя панель с настройками
        bottom_panel = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.config["player"].get("volume", 80))
        self.volume_slider.valueChanged.connect(self.change_volume)

        self.mode_selector = QComboBox()
        modes = self.config.get("ui", {}).get("modes", ["Waveform", "Spectrum", "Disco"])
        self.mode_selector.addItems(modes)
        self.mode_selector.currentTextChanged.connect(self.on_mode_change)

        bottom_panel.addWidget(QLabel("Volume"))
        bottom_panel.addWidget(self.volume_slider)
        bottom_panel.addWidget(QLabel("Mode"))
        bottom_panel.addWidget(self.mode_selector)

        # Плейлист справа
        self.playlist_widget = QListWidget()
        self.playlist_widget.setMaximumWidth(250)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected)

        container = QHBoxLayout()
        container.addLayout(main_layout)
        container.addWidget(self.playlist_widget)

        central.setLayout(container)
        central.layout().addLayout(bottom_panel)
        self.setCentralWidget(central)

        # Плейлист файлов
        self.playlist = []
        self.current_track_index = -1

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_visualization)
        fps = self.config["visualization"].get("fps", 30)
        self.timer.start(1000 // fps)

    def toggle_play_pause(self):
        if self.is_playing:
            self.player.pause()
            self.play_pause_btn.setText("Play")
        else:
            if self.player.paused:
                self.player.resume()
            else:
                if self.current_track_index < 0 and self.playlist:
                    self.current_track_index = 0
                    self.load_track(self.current_track_index)
                else:
                    self.player.play()
            self.play_pause_btn.setText("Pause")
        self.is_playing = not self.is_playing

    def stop_audio(self):
        self.player.stop()
        self.player.seek(0)
        self.is_playing = False
        self.play_pause_btn.setText("Play")
        self.seek_slider.setValue(0)

    def load_audio_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Audio Files", "", "Audio Files (*.mp3 *.wav *.flac)")
        if files:
            self.playlist.extend(files)
            for f in files:
                item = QListWidgetItem(f.split('/')[-1])
                self.playlist_widget.addItem(item)
            if self.current_track_index == -1:
                self.current_track_index = 0
                self.load_track(self.current_track_index)

    def load_track(self, index):
        if 0 <= index < len(self.playlist):
            self.player.load(self.playlist[index])
            self.player.set_volume(self.volume_slider.value() / 100)
            self.play_pause_btn.setText("Play")
            self.is_playing = False
            self.playlist_widget.setCurrentRow(index)
            # Сбрасываем фон при загрузке трека
            self.reset_background()

    def play_selected(self, item):
        index = self.playlist_widget.row(item)
        if index != self.current_track_index:
            self.current_track_index = index
            self.load_track(index)
            self.toggle_play_pause()

    def play_next(self):
        if not self.playlist:
            return
        self.current_track_index = (self.current_track_index + 1) % len(self.playlist)
        self.load_track(self.current_track_index)
        self.toggle_play_pause()

    def play_prev(self):
        if not self.playlist:
            return
        self.current_track_index = (self.current_track_index - 1) % len(self.playlist)
        self.load_track(self.current_track_index)
        self.toggle_play_pause()

    def seek_audio(self):
        fraction = self.seek_slider.value() / 1000.0
        self.player.seek(fraction)

    def change_volume(self):
        self.player.set_volume(self.volume_slider.value() / 100)

    def on_mode_change(self, mode):
        if mode == "Waveform":
            self.plot_widget.setBackground(self.bg_waveform)
        elif mode == "Spectrum":
            self.plot_widget.setBackground(self.bg_spectrum)
        elif mode == "Disco":
            # Фон будет динамическим
            pass
        self.reset_background()

    def reset_background(self):
        mode = self.mode_selector.currentText()
        if mode == "Waveform":
            self.plot_widget.setBackground(self.bg_waveform)
        elif mode == "Spectrum":
            self.plot_widget.setBackground(self.bg_spectrum)
        elif mode == "Disco":
            # Для диско фон управляется динамически в update_visualization
            pass

    def update_visualization(self):
        data = self.player.get_current_frame()
        if data.size == 0:
            return

        if data.ndim > 1:
            data = data.mean(axis=1)

        mode = self.mode_selector.currentText()

        if mode == "Waveform":
            x, y = self.visualizer.get_waveform(data)
            max_abs = max(abs(y.min()), abs(y.max()), 1)
            y_norm = y / max_abs

            self.plot.setData(x, y_norm)
            self.zero_line.setData(x, [0] * len(x))
            self.plot.setVisible(True)
            self.plot_widget.setYRange(-1.1, 1.1, padding=0)
            self.fill_item.setVisible(False)

        elif mode == "Spectrum":
            # Получаем спектр
            x_freq, y = self.visualizer.get_spectrum(data)

            # Преобразуем частоты в логарифмическую шкалу (для ОЧХ)
            x_log = np.log10(x_freq + 1)  # +1 чтобы избежать log(0)

            # Нормализация амплитуды (0..1)
            y_norm = y / max(y.max(), 1e-6)

            self.plot.setData(x_log, y_norm)
            self.zero_line.setData(x_log, [0] * len(x_log))
            self.plot.setVisible(True)

            # Настраиваем вид диапазона Y и X под спектр
            self.plot_widget.setYRange(0, 1.1, padding=0)
            self.plot_widget.setXRange(x_log.min(), x_log.max(), padding=0)

            self.fill_item.setVisible(self.visualizer.fill)

        elif mode == "Disco":
            intensity = np.abs(data).mean()
            self.disco_hue += self.disco_speed * intensity
            self.disco_hue %= 1.0
            rgb = colorsys.hsv_to_rgb(self.disco_hue, 1, 1)
            r, g, b = [int(255 * c) for c in rgb]
            color_str = f'#{r:02x}{g:02x}{b:02x}'
            self.plot_widget.setBackground(color_str)

            self.plot.setVisible(False)
            self.fill_item.setVisible(False)
            self.zero_line.setData([], [])

        # Обновляем позицию ползунка, если он не зажат пользователем
        if not self.seek_slider.isSliderDown():
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(int(self.player.get_progress() * 1000))
            self.seek_slider.blockSignals(False)
