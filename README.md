# Orbes

Puzle de cadenas de orbes de colores para **iOS, macOS y Windows**, en el estilo de *Orba*
(Kieffer Bros.): tocas grupos de orbes del mismo color para reventarlos; cuanto más largo el
grupo, más puntos. Reglas, arte y nombre propios; no se usa ningún recurso del original.

Python + **pygame-ce** (dibujo y entrada), **sqlite3** (puntuaciones y ajustes) y **Briefcase**
(empaquetado). Todo el dibujo es con formas básicas: no hay imágenes ni sonidos externos.

## Cómo se juega

- Toca (o haz clic en) un orbe con al menos otro orbe del mismo color pegado (arriba, abajo, izquierda o
  derecha; las diagonales no cuentan). Todo el grupo revienta y suma `n × (n − 1) × 10` puntos.
- Los orbes caen y las columnas vacías se compactan hacia la izquierda.
- Cada pocos toques **sube una fila nueva** desde abajo (la vista previa y el contador están bajo el
  tablero). Si la pila toca el techo, se acaba la partida.
- Si no queda ninguna jugada, suben filas solas hasta que haya una… o se llene la pantalla.
- Al **vaciar el tablero** pasas de nivel con bonus: más filas iniciales, más colores (3 → 6) y filas
  nuevas más seguidas.
- En el menú, **Ayuda de color** dibuja una marca distinta dentro de cada color (útil con daltonismo).
- En escritorio, al pasar el ratón se resalta el grupo y se muestra cuántos puntos daría.

Teclado: `Esc` vuelve al menú; `Enter` empieza una partida.

## Estructura

```
pyproject.toml           Briefcase (macOS, iOS, windows) y pytest
src/orbes/
  settings.py            Constantes: tablero, reglas, dificultad, colores
  board.py               Tablero: grupos, gravedad, compactación, subida de fila   (lógica pura)
  game.py                Partida: puntos, niveles, filas nuevas, fin de partida     (lógica pura)
  db.py                  sqlite3: puntuaciones y ajustes (migraciones con user_version)
  display.py             Superficie lógica escalada a la ventana + coordenadas de ratón/dedo
  controls.py            Un toque o clic es la única acción; ignora el ratón sintético de SDL
  sprites.py             Orbes con formas básicas y caché
  scenes.py              Menú, partida (animaciones, partículas), puntuaciones
  app.py / __main__.py   Bucle principal y punto de entrada de Briefcase
tests/                   pytest
.github/workflows/       Tests en Linux, macOS y Windows
```

`board.py`, `game.py` y `db.py` no importan pygame, así que se prueban sin ventana y se pueden
reutilizar si algún día cambias de motor gráfico. Para ajustar la dificultad toca `settings.py`
(`START_ROWS`, `START_PUSH_INTERVAL`, `MAX_COLORS`…) y `level_params` en `game.py`.

## Desarrollo

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install briefcase pygame-ce platformdirs pytest

python -m pytest                     # tests (driver de vídeo "dummy": no abren ventana)
briefcase dev                        # jugar en el escritorio
```

Si ya tienes `pygame` (el clásico) instalado, desinstálalo: comparte el nombre de módulo con
`pygame-ce` y no deben convivir.

Los datos (`orbes.db`) se guardan en la carpeta de datos de usuario (`platformdirs`):
`~/Library/Application Support/Orbes` en macOS, `%LOCALAPPDATA%\Orbes\Orbes` en Windows y el sandbox de la
app en iOS.

## Tests

| Fichero          | Qué cubre                                                                   |
|------------------|-----------------------------------------------------------------------------|
| `test_board.py`  | Grupos ortogonales, gravedad, compactación, movimientos, subida de fila, desbordamiento |
| `test_game.py`   | Puntuación, filas nuevas, subida de nivel, sin jugadas, fin de partida, partidas aleatorias |
| `test_db.py`     | Puntuaciones, récord, ajustes, versión de esquema, persistencia en disco    |
| `test_smoke.py`  | Arranque headless con pygame real: menú, clic en "Jugar", clic en un grupo, guardado al terminar |

## Empaquetar

Cada plataforma se empaqueta **desde su propio sistema**: Briefcase no hace compilación cruzada.

```bash
# macOS (también necesario para iOS; iOS requiere Xcode)
briefcase create macOS && briefcase build macOS && briefcase run macOS
briefcase package macOS --adhoc-sign

# iOS (simulador)
briefcase create iOS && briefcase build iOS && briefcase run iOS

# Windows (en un PC con Windows; genera un instalador .msi)
briefcase create windows
briefcase build windows
briefcase run windows
briefcase package windows
```

Antes de publicar cambia en `pyproject.toml`: `bundle`, `author`, `author_email`, `url`, y el nombre en
`LICENSE`. Los iconos van en `src/orbes/resources/` (`icon.icns` macOS, `icon.ico` Windows,
`icon-<tamaño>.png` iOS); sin ellos Briefcase usa uno por defecto y avisa.

## Riesgo iOS

**macOS y Windows no tienen problema; iOS es el punto débil del stack.** Briefcase en iOS solo instala:

- paquetes Python puros, o
- paquetes con código nativo para los que exista una *wheel* compilada para iOS. PyPI no admite
  wheels de iOS: Briefcase consulta un repositorio secundario mantenido por BeeWare (en anaconda.org)
  que no cubre todos los paquetes ni todas las versiones. Para los que faltan se usa
  [BeeWare Mobile Forge](https://github.com/beeware/mobile-forge), donde se pueden aportar recetas.

`pygame-ce` es una extensión en C que depende de SDL2, así que **necesita una wheel para iOS que no he
podido comprobar que exista**. Antes de invertir más en el juego:

1. Ejecuta `briefcase create iOS` con este proyecto tal cual. Si falla el `pip install` con
   "no matching distribution" o "Cannot compile native modules", la wheel no está disponible.
2. Si falta: compila `pygame-ce` para iOS con Mobile Forge (requiere SDL2, SDL2_image/mixer/ttf
   compilados para iOS) o busca una wheel ya construida por la comunidad.
3. Plan B: sustituir solo la capa de dibujo y entrada (`display.py`, `controls.py`, `sprites.py`,
   `scenes.py`). La lógica (`board.py`, `game.py`, `db.py`) no depende de pygame y se reutiliza tal cual.

## Qué falta (hoja de ruta)

- Sonido y música; vibración al reventar en iOS.
- Modo rápido con temporizador y modo sin fin; Game Center / tablas online en iOS.
- Pantalla para escribir el nombre (hoy se usa el ajuste `player_name`, por defecto "Jugador").
- Pausa al perder el foco; guardar la partida en curso al pasar a segundo plano (importante en iOS).
- Iconos, pantalla de arranque y ajuste fino de la dificultad (una partida al azar llega al nivel 3–5).
