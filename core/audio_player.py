import soundfile as sf
import sounddevice as sd
import numpy as np
import threading

class AudioPlayer:
    def __init__(self):
        self.stream = None
        self.audio_data = None
        self.samplerate = None
        self.position = 0
        self.volume = 1.0
        self.playing = False
        self.paused = False
        self.lock = threading.Lock()

    def load(self, path):
        self.stop()
        self.audio_data, self.samplerate = sf.read(path, dtype='float32', always_2d=True)
        self.position = 0

    def callback(self, outdata, frames, time, status):
        with self.lock:
            if self.audio_data is None or not self.playing:
                outdata[:] = np.zeros((frames, self.audio_data.shape[1]))
                return

            end = self.position + frames
            chunk = self.audio_data[self.position:end]

            if len(chunk) < frames:
                chunk = np.pad(chunk, ((0, frames - len(chunk)), (0, 0)))
                self.playing = False
                self.position = 0
                sd.sleep(int(frames / self.samplerate * 1000))

            outdata[:] = chunk * self.volume
            self.position += frames

    def play(self):
        if self.audio_data is None:
            return

        self.playing = True
        self.paused = False
        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=self.audio_data.shape[1],
                callback=self.callback
            )
            self.stream.start()

    def pause(self):
        self.playing = False
        self.paused = True

    def resume(self):
        if self.audio_data is None:
            return
        self.playing = True
        self.paused = False
        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=self.audio_data.shape[1],
                callback=self.callback
            )
            self.stream.start()

    def stop(self):
        with self.lock:
            self.playing = False
            self.paused = False
            self.position = 0
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
                self.stream = None

    def set_volume(self, volume):
        self.volume = volume

    def seek(self, fraction):
        if self.audio_data is None:
            return
        with self.lock:
            fraction = max(0, min(1, fraction))
            self.position = int(len(self.audio_data) * fraction)

    def get_current_frame(self, window_size=2048):
        if self.audio_data is None:
            return np.array([])
        with self.lock:
            end = min(self.position, len(self.audio_data))
            start = max(0, end - window_size)
            return self.audio_data[start:end]

    def get_progress(self):
        if self.audio_data is None or len(self.audio_data) == 0:
            return 0
        return self.position / len(self.audio_data)
