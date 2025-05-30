import numpy as np
import scipy.ndimage
import random
import math
import colorsys

class Visualizer:
    def __init__(self, config):
        self.config = config.get("visualization", {})
        self.theme = config.get("theme", {})
        self.smooth = self.config.get("smoothing_enabled", True)
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
        window = np.hanning(len(data))
        spectrum = np.abs(np.fft.rfft(data * window))
        spectrum = self._smooth_data(spectrum)
        x = np.arange(len(spectrum))
        return x, spectrum