import numpy as np
import scipy.ndimage
import random
import math
import colorsys

class Visualizer:
    def __init__(self, config):
        self.config = config.get("visualization", {})
        self.theme = config.get("theme", {})
        self.smooth = self.config.get("smooth", True)
        self.smooth_type = self.config.get("smooth_type", "uniform")  # uniform, gaussian
        self.smooth_window = self.config.get("smoothing_window", 5)
        self.fill = self.config.get("fill", True)
        self.sym_spec_conf = config.get("symmetric_spectrum", {})
        self.rotation_angle = 0.0
        self.trail_buffer = []
        self.colors = [(0, 0, 255)]

    def _smooth_data(self, data):
        if not self.smooth or len(data) < self.smooth_window:
            return data
        if self.smooth_type == "gaussian":
            return scipy.ndimage.gaussian_filter1d(data, sigma=self.smooth_window / 3)
        else:
            return scipy.ndimage.uniform_filter1d(data, size=self.smooth_window)

    def get_waveform(self, data):
        if data.ndim > 1:
            data = data.mean(axis=1)
        x = np.arange(len(data))
        data = self._smooth_data(data)
        return x, data

    def get_spectrum(self, data):
        if data.ndim > 1:
            data = data.mean(axis=1)
        spectrum = np.abs(np.fft.rfft(data))
        spectrum = self._smooth_data(spectrum)
        x = np.arange(len(spectrum))
        return x, spectrum

    def get_rotated_spectrum(self, data):
        _, spectrum = self.get_spectrum(data)
        x = np.arange(len(spectrum))

        # Добавляем случайный разброс угла
        random_angle_offset = random.uniform(-self.sym_spec_conf['random_angle_range'],
                                             self.sym_spec_conf['random_angle_range'])
        total_angle = self.rotation_angle + random_angle_offset
        angle_radians = math.radians(total_angle)

        # Применяем поворот по углам
        rotated_spectrum = spectrum.copy()
        for idx in range(len(rotated_spectrum)):
            x_pos = x[idx] * math.cos(angle_radians) - rotated_spectrum[idx] * math.sin(angle_radians)
            y_pos = x[idx] * math.sin(angle_radians) + rotated_spectrum[idx] * math.cos(angle_radians)
            rotated_spectrum[idx] = y_pos

        return x, rotated_spectrum

    def get_trailing_lines(self, new_points):
        decayed_trails = []
        decay_value = 1.0
        for trail in reversed(self.trail_buffer):
            decayed_trails.insert(0, trail * decay_value)
            decay_value *= self.sym_spec_conf['trail_decay_factor']
        self.trail_buffer.append(new_points)
        if len(self.trail_buffer) > self.sym_spec_conf['trail_length']:
            self.trail_buffer.pop(0)
        return decayed_trails

    def update_colors(self, intensity):
        hue_shift = intensity * self.sym_spec_conf['intensity_to_color_factor']  # Скорость смены оттенков
        sat_shift = intensity * 0.05  # Насыщенность
        value_shift = intensity * 0.05  # Яркость

        base_color = list(map(lambda x: x / 255.0, self.colors[0]))
        hsv_color = colorsys.rgb_to_hsv(*base_color)
        updated_hsv = (hsv_color[0] + hue_shift, hsv_color[1] + sat_shift, hsv_color[2] + value_shift)
        updated_rgb = tuple(map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*updated_hsv)))
        self.colors = [updated_rgb]

    def update_rotation(self, signal_intensity):
        rotation_speed = signal_intensity * self.sym_spec_conf['rotation_speed_multiplier']
        self.rotation_angle += rotation_speed
        self.rotation_angle %= 360  # Периодическое вращение