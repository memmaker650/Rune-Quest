"""Sonido: efectos (FX) y música de fondo, cada uno con su interruptor guardado en los ajustes.

El efecto al reventar una combinación se sintetiza al arrancar (un "plop" suave: un tono que
baja ligeramente y se apaga rápido), así que no hace falta ningún fichero de audio. Si no hay
dispositivo de sonido o el mezclador falla, todo sigue funcionando en silencio.

La música de fondo aún no está definida: el interruptor ya existe y se guarda, y cuando haya un
fichero bastará con cargarlo en ``start_music``.
"""

import array
import logging
import math

import pygame

log = logging.getLogger(__name__)

POP_VOLUME = 0.22          # volumen del efecto (0..1): suave


def synth_pop(freq: int, fmt: int, channels: int) -> bytes:
    """Muestras de un "plop" suave en el formato del mezclador (16 bits con signo o float)."""
    duration = 0.16
    n = int(freq * duration)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / freq
        pitch = 660 + 240 * math.exp(-t * 30)          # de ~900 Hz baja hacia 660 Hz
        phase += 2 * math.pi * pitch / freq
        attack = min(1.0, t / 0.004)                    # 4 ms de entrada: sin chasquido
        env = attack * math.exp(-t * 28)
        value = env * (0.8 * math.sin(phase) + 0.2 * math.sin(2 * phase))
        samples.extend([value] * channels)
    if fmt in (32, -32):                                # float32
        return array.array("f", samples).tobytes()
    return array.array("h", (int(v * 32767) for v in samples)).tobytes()


class Audio:
    def __init__(self, fx_enabled: bool = True, music_enabled: bool = True):
        self.fx_enabled = fx_enabled
        self.music_enabled = music_enabled
        self.available = False
        self._pop = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            freq, fmt, channels = pygame.mixer.get_init()
            if abs(fmt) not in (16, 32):
                raise ValueError(f"formato de audio no soportado: {fmt}")
            self._pop = pygame.mixer.Sound(buffer=synth_pop(freq, fmt, channels))
            self._pop.set_volume(POP_VOLUME)
            self.available = True
            log.info("Audio listo (%d Hz, formato %d, %d canales)", freq, fmt, channels)
        except Exception:
            log.warning("Sin audio: los efectos de sonido quedan desactivados", exc_info=True)

    def play_pop(self) -> None:
        """Efecto al reventar una combinación."""
        if self.fx_enabled and self._pop is not None:
            self._pop.play()

    def set_fx(self, enabled: bool) -> None:
        self.fx_enabled = enabled
        log.info("Efectos de sonido: %s", "sí" if enabled else "no")

    def set_music(self, enabled: bool) -> None:
        self.music_enabled = enabled
        log.info("Música: %s", "sí" if enabled else "no")
        if enabled:
            self.start_music()
        elif self.available:
            pygame.mixer.music.stop()

    def start_music(self) -> None:
        """Música de fondo: todavía no hay ninguna definida."""
        if self.music_enabled:
            log.debug("Música de fondo activada, pero aún no hay ninguna pista definida")
