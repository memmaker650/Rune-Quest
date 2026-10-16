import os

# Pygame sin ventana ni audio, para CI y para este entorno.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Sin Game Center real en los tests (no hay app firmada ni sesión de usuario).
os.environ.setdefault("RUNEQUEST_GAMECENTER", "0")
