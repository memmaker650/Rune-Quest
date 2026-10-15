"""Entrada: un toque (iOS) o un clic (macOS/Windows) es la única acción del juego."""

import pygame


def _synthetic_mouse(event) -> bool:
    """SDL genera ratón falso a partir de toques; lo ignoramos para no duplicar."""
    return bool(getattr(event, "touch", False))


def is_real_mouse_motion(event) -> bool:
    return event.type == pygame.MOUSEMOTION and not _synthetic_mouse(event)


def tap_position(event, display):
    """Posición lógica si el evento es un toque/clic de 'pulsar'; si no, None."""
    if event.type == pygame.FINGERDOWN:
        return display.event_pos(event)
    if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            and not _synthetic_mouse(event)):
        return display.event_pos(event)
    return None


def is_confirm(event, display) -> bool:
    if tap_position(event, display) is not None:
        return True
    return event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)
