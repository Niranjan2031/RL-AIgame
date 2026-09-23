import pygame
import os
import math
import random
import colorsys
import pytmx
import sys

# Allow main.py (inside src/) to import the RL environment
# stored in the RL COMPONENTS folder.
RL_COMPONENTS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "RL COMPONENTS"
)

if RL_COMPONENTS_PATH not in sys.path:
    sys.path.append(RL_COMPONENTS_PATH)

from tactical_shooter_env import TacticalShooterEnv
from dqn_agent import DQNAgent

from player import Player
from bullet import Bullet
from enemy import Enemy
from obstacle import Obstacle
from rl_bot import RLBot


# =====================================================
# INITIALIZE PYGAME
# =====================================================

pygame.init()


# =====================================================
# SCREEN SETTINGS
# =====================================================

WIDTH = 1000
HEIGHT = 700

screen = pygame.display.set_mode(
    (WIDTH, HEIGHT)
)

pygame.display.set_caption(
    "DUNGEON OPS"
)


# =====================================================
# LOAD TILED MAP
# =====================================================

map_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "assets",
    "maps",
    "Dungeon1.tmx"
)

tmx_data = pytmx.load_pygame(
    map_path
)


# =====================================================
# MAP INFORMATION
# =====================================================

MAP_WIDTH = (
    tmx_data.width *
    tmx_data.tilewidth
)

MAP_HEIGHT = (
    tmx_data.height *
    tmx_data.tileheight
)


# =====================================================
# MAP SCALE
# =====================================================

TILE_SCALE = 1.638

MAP_VERTICAL_OFFSET = -30


# =====================================================
# CLOCK
# =====================================================

clock = pygame.time.Clock()


# =====================================================
# FONTS / DUNGEON OPS GUI
# =====================================================

menu_title_font = pygame.font.SysFont(
    "trebuchetms", 68, bold=True
)

menu_subtitle_font = pygame.font.SysFont(
    "trebuchetms", 24, bold=True
)

menu_button_font = pygame.font.SysFont(
    "trebuchetms", 30, bold=True
)

menu_hint_font = pygame.font.SysFont(
    "trebuchetms", 18, bold=True
)

font = pygame.font.SysFont(None, 36)

big_font = pygame.font.SysFont(None, 72)


# =====================================================
# MENU BACKGROUNDS
# =====================================================

MENU_ASSET_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "..",
    "assets",
    "menu"
)

MAIN_MENU_BACKGROUND_PATH = os.path.join(
    MENU_ASSET_FOLDER,
    "dungeon_ops_main_menu.jpg"
)

PAUSE_MENU_BACKGROUND_PATH = os.path.join(
    MENU_ASSET_FOLDER,
    "dungeon_ops_pause_menu.jpg"
)

DEATH_SCREEN_BACKGROUND_PATH = os.path.join(
    MENU_ASSET_FOLDER,
    "dungeon_ops_death.jpg"
)

VICTORY_SCREEN_BACKGROUND_PATH = os.path.join(
    MENU_ASSET_FOLDER,
    "dungeon_ops_victory.jpg"
)


def load_menu_background(image_path):
    """Load and scale a menu background to the game window."""
    if not os.path.exists(image_path):
        print(
            "WARNING: Menu background not found:",
            os.path.abspath(image_path)
        )
        fallback = pygame.Surface((WIDTH, HEIGHT))
        fallback.fill((12, 10, 20))
        return fallback

    image = pygame.image.load(image_path).convert()

    return pygame.transform.scale(
        image,
        (WIDTH, HEIGHT)
    )


main_menu_background = load_menu_background(
    MAIN_MENU_BACKGROUND_PATH
)

pause_menu_background = load_menu_background(
    PAUSE_MENU_BACKGROUND_PATH
)

death_screen_background = load_menu_background(
    DEATH_SCREEN_BACKGROUND_PATH
)

victory_screen_background = load_menu_background(
    VICTORY_SCREEN_BACKGROUND_PATH
)


# =====================================================
# CUSTOM MENU BUTTON
# =====================================================

class MenuButton:

    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.hovered = False

    def update(self, mouse_position):
        self.hovered = self.rect.collidepoint(
            mouse_position
        )

    def draw(self, surface):

        # Shadow
        shadow_rect = self.rect.move(0, 6)

        pygame.draw.rect(
            surface,
            (5, 5, 10),
            shadow_rect,
            border_radius=8
        )

        if self.hovered:
            fill_color = (95, 48, 35)
            border_color = (255, 194, 92)
            border_width = 3
        else:
            fill_color = (35, 25, 35)
            border_color = (185, 130, 65)
            border_width = 2

        pygame.draw.rect(
            surface,
            fill_color,
            self.rect,
            border_radius=8
        )

        pygame.draw.rect(
            surface,
            border_color,
            self.rect,
            border_width,
            border_radius=8
        )

        accent_color = (
            (255, 194, 92)
            if self.hovered
            else (145, 95, 45)
        )

        pygame.draw.rect(
            surface,
            accent_color,
            (
                self.rect.left + 7,
                self.rect.top + 10,
                4,
                self.rect.height - 20
            ),
            border_radius=2
        )

        pygame.draw.rect(
            surface,
            accent_color,
            (
                self.rect.right - 11,
                self.rect.top + 10,
                4,
                self.rect.height - 20
            ),
            border_radius=2
        )

        text_surface = menu_button_font.render(
            self.text,
            True,
            (245, 235, 215)
        )

        text_rect = text_surface.get_rect(
            center=self.rect.center
        )

        surface.blit(
            text_surface,
            text_rect
        )


main_menu_start_button = MenuButton(
    (WIDTH // 2 - 150, 390, 300, 62),
    "START GAME"
)

main_menu_exit_button = MenuButton(
    (WIDTH // 2 - 150, 470, 300, 62),
    "EXIT GAME"
)

pause_resume_button = MenuButton(
    (WIDTH // 2 - 150, 390, 300, 62),
    "RESUME"
)

pause_exit_button = MenuButton(
    (WIDTH // 2 - 150, 470, 300, 62),
    "EXIT GAME"
)


# =====================================================
# DEATH / VICTORY BUTTONS
# =====================================================
#
# The two supplied outcome images already contain their
# own large messages.  The button is therefore deliberately
# placed near the bottom of the 1000x700 window so it does
# not touch or cover the artwork/message.
# =====================================================

class OutcomeButton:
    def __init__(self, rect, text, theme):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.theme = theme
        self.hovered = False

    def update(self, mouse_position):
        self.hovered = self.rect.collidepoint(mouse_position)

    def draw(self, surface):
        if self.theme == "death":
            base = (28, 28, 32)
            hover = (55, 55, 62)
            border = (210, 210, 215)
            accent = (245, 245, 245)
            text_color = (248, 248, 248)
        else:
            base = (8, 48, 55)
            hover = (10, 78, 88)
            border = (57, 235, 239)
            accent = (35, 220, 225)
            text_color = (240, 255, 255)

        # Soft shadow.
        shadow = self.rect.move(0, 7)
        pygame.draw.rect(
            surface,
            (0, 0, 0),
            shadow,
            border_radius=12
        )

        # Main button body.
        pygame.draw.rect(
            surface,
            hover if self.hovered else base,
            self.rect,
            border_radius=12
        )

        # Double tactical border.
        pygame.draw.rect(
            surface,
            border,
            self.rect,
            2 if not self.hovered else 3,
            border_radius=12
        )

        inner_rect = self.rect.inflate(-8, -8)
        pygame.draw.rect(
            surface,
            accent,
            inner_rect,
            1,
            border_radius=9
        )

        # Side accents.
        pygame.draw.rect(
            surface,
            accent,
            (
                self.rect.left + 10,
                self.rect.top + 13,
                4,
                self.rect.height - 26
            ),
            border_radius=2
        )

        pygame.draw.rect(
            surface,
            accent,
            (
                self.rect.right - 14,
                self.rect.top + 13,
                4,
                self.rect.height - 26
            ),
            border_radius=2
        )

        text_surface = menu_button_font.render(
            self.text,
            True,
            text_color
        )

        text_rect = text_surface.get_rect(
            center=self.rect.center
        )

        surface.blit(
            text_surface,
            text_rect
        )


outcome_button_rect = (
    WIDTH // 2 - 150,
    615,
    300,
    58
)

death_back_button = OutcomeButton(
    outcome_button_rect,
    "BACK TO MAIN MENU",
    "death"
)

victory_back_button = OutcomeButton(
    outcome_button_rect,
    "BACK TO MAIN MENU",
    "victory"
)


def draw_menu_overlay(surface, alpha=100):

    overlay = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA
    )

    overlay.fill(
        (0, 0, 0, alpha)
    )

    surface.blit(
        overlay,
        (0, 0)
    )


def draw_menu_title(
    surface,
    subtitle
):

    title = menu_title_font.render(
        "DUNGEON OPS",
        True,
        (248, 231, 198)
    )

    shadow = menu_title_font.render(
        "DUNGEON OPS",
        True,
        (15, 8, 15)
    )

    title_rect = title.get_rect(
        center=(WIDTH // 2, 205)
    )

    shadow_rect = shadow.get_rect(
        center=(WIDTH // 2 + 3, 208)
    )

    surface.blit(shadow, shadow_rect)
    surface.blit(title, title_rect)

    divider_y = title_rect.bottom + 18

    pygame.draw.line(
        surface,
        (184, 127, 63),
        (WIDTH // 2 - 155, divider_y),
        (WIDTH // 2 + 155, divider_y),
        2
    )

    subtitle_surface = menu_subtitle_font.render(
        subtitle,
        True,
        (230, 210, 177)
    )

    subtitle_rect = subtitle_surface.get_rect(
        center=(WIDTH // 2, divider_y + 28)
    )

    surface.blit(
        subtitle_surface,
        subtitle_rect
    )


def draw_main_menu(surface):

    surface.blit(
        main_menu_background,
        (0, 0)
    )

    draw_menu_overlay(
        surface,
        105
    )

    draw_menu_title(
        surface,
        "TACTICAL DUNGEON ASSAULT"
    )

    mouse_position = pygame.mouse.get_pos()

    main_menu_start_button.update(
        mouse_position
    )

    main_menu_exit_button.update(
        mouse_position
    )

    main_menu_start_button.draw(surface)
    main_menu_exit_button.draw(surface)

    hint = menu_hint_font.render(
        "ENTER  •  ENGAGE  •  SURVIVE",
        True,
        (218, 194, 157)
    )

    hint_rect = hint.get_rect(
        center=(WIDTH // 2, 570)
    )

    surface.blit(
        hint,
        hint_rect
    )


def draw_pause_menu(surface):

    surface.blit(
        pause_menu_background,
        (0, 0)
    )

    draw_menu_overlay(
        surface,
        125
    )

    # Smaller title layout for the pause screen.
    title = menu_title_font.render(
        "DUNGEON OPS",
        True,
        (248, 231, 198)
    )

    title_shadow = menu_title_font.render(
        "DUNGEON OPS",
        True,
        (15, 8, 15)
    )

    title_rect = title.get_rect(
        center=(WIDTH // 2, 155)
    )

    shadow_rect = title_shadow.get_rect(
        center=(WIDTH // 2 + 3, 158)
    )

    surface.blit(
        title_shadow,
        shadow_rect
    )

    surface.blit(
        title,
        title_rect
    )

    pygame.draw.line(
        surface,
        (184, 127, 63),
        (WIDTH // 2 - 145, title_rect.bottom + 14),
        (WIDTH // 2 + 145, title_rect.bottom + 14),
        2
    )

    paused = menu_title_font.render(
        "PAUSED",
        True,
        (248, 231, 198)
    )

    paused_rect = paused.get_rect(
        center=(WIDTH // 2, 275)
    )

    surface.blit(
        paused,
        paused_rect
    )

    mouse_position = pygame.mouse.get_pos()

    pause_resume_button.update(
        mouse_position
    )

    pause_exit_button.update(
        mouse_position
    )

    pause_resume_button.draw(surface)
    pause_exit_button.draw(surface)

    hint = menu_hint_font.render(
        "ESC  •  RESUME",
        True,
        (218, 194, 157)
    )

    hint_rect = hint.get_rect(
        center=(WIDTH // 2, 570)
    )

    surface.blit(
        hint,
        hint_rect
    )


def draw_death_screen(surface):
    """Draw the supplied death artwork and its single return button."""
    surface.blit(
        death_screen_background,
        (0, 0)
    )

    mouse_position = pygame.mouse.get_pos()
    death_back_button.update(mouse_position)
    death_back_button.draw(surface)


def draw_victory_screen(surface):
    """Draw the supplied victory artwork and its single return button."""
    surface.blit(
        victory_screen_background,
        (0, 0)
    )

    mouse_position = pygame.mouse.get_pos()
    victory_back_button.update(mouse_position)
    victory_back_button.draw(surface)


# =====================================================
# PLAYER
# =====================================================

player = Player()


# =====================================================
# BULLETS
# =====================================================

# Player bullets
bullets = []

# Enemy bullets
enemy_bullets = []


# =====================================================
# SCORE
# =====================================================

score = 0


# =====================================================
# GAME STATE
# =====================================================

game_state = "MENU"


# =====================================================
# NORMAL ENEMY ACTIVATION SETTINGS
# =====================================================

# Only ONE normal enemy can be active at a time.
# An enemy becomes active only when the player is
# very close to it.
ENEMY_ACTIVATION_DISTANCE = 80
ENEMY_DEACTIVATION_DISTANCE = 200

# The currently active normal enemy.
active_enemy = None


# =====================================================
# PLAYER MELEE SETTINGS
# =====================================================

MELEE_RANGE = 100

MELEE_ANGLE = 90

MELEE_COOLDOWN = 500

last_melee_time = 0


# =====================================================
# GET MAP SCREEN OFFSET
# =====================================================

def get_map_offset():

    map_width = (
        tmx_data.width *
        tmx_data.tilewidth
    )

    map_height = (
        tmx_data.height *
        tmx_data.tileheight
    )


    enlarged_width = int(
        map_width *
        TILE_SCALE
    )

    enlarged_height = int(
        map_height *
        TILE_SCALE
    )


    screen_width, screen_height = (
        screen.get_size()
    )


    offset_x = (
        screen_width -
        enlarged_width
    ) // 2


    offset_y = (
        (
            screen_height -
            enlarged_height
        ) // 2
    ) + MAP_VERTICAL_OFFSET


    return (
        offset_x,
        offset_y
    )


# =====================================================
# GET ACTUAL SCALED MAP BOUNDS
# =====================================================

def get_map_bounds():

    map_width = (
        tmx_data.width *
        tmx_data.tilewidth
    )

    map_height = (
        tmx_data.height *
        tmx_data.tileheight
    )

    enlarged_width = int(
        map_width *
        TILE_SCALE
    )

    enlarged_height = int(
        map_height *
        TILE_SCALE
    )

    offset_x, offset_y = (
        get_map_offset()
    )

    return (
        offset_x,
        offset_y,
        offset_x + enlarged_width,
        offset_y + enlarged_height
    )


# =====================================================
# PICKUP SETTINGS
# =====================================================

HEALTH_PACK_AMOUNT = 15

# The player currently has a magazine-based ammo system.
# An ammo pickup refills the currently equipped weapon's
# magazine to its maximum capacity.
#
# Pickups are NOT added to the obstacle list and are NOT
# considered by enemy A* navigation.

PICKUP_SOURCE_SIZE = 8


# =====================================================
# LOAD PICKUP SPRITES
# =====================================================

pickup_folder = os.path.join(
    os.path.dirname(__file__),
    "..",
    "assets",
    "pickups"
)


def load_pickup_image(filename):

    image_path = os.path.join(
        pickup_folder,
        filename
    )

    if not os.path.exists(image_path):

        print(
            "WARNING: Pickup image not found:",
            image_path
        )

        return None

    image = pygame.image.load(
        image_path
    ).convert_alpha()

    # Keep the tiny pixel-art pickup size consistent
    # with the 8x8 pickup sprites prepared for the map.
    display_size = max(
        1,
        int(PICKUP_SOURCE_SIZE * TILE_SCALE)
    )

    image = pygame.transform.scale(
        image,
        (
            display_size,
            display_size
        )
    )

    return image


health_pack_image = load_pickup_image(
    "health_pack.png"
)

ammo_pack_image = load_pickup_image(
    "ammo_pack.png"
)


# =====================================================
# LOAD HEALTH-BAR SPRITE SHEET
# =====================================================
#
# Expected asset:
#     assets/ui/health_bars.png
#
# The supplied sheet contains many UI bars.  We automatically
# extract the long horizontal RED, GREEN and PURPLE bars so the
# exact source coordinates do not have to be hard-coded.
#
# Usage:
#     RED    -> normal enemies
#     GREEN  -> player
#     PURPLE -> RL bots
#
# The extracted frames are selected according to the current
# health ratio.  If the sheet cannot be found, the game falls
# back to the existing simple bars instead of crashing.
# =====================================================

HEALTH_BAR_ASSET_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "..",
    "assets",
    "ui"
)

HEALTH_BAR_SPRITE_SHEET_PATH = os.path.join(
    HEALTH_BAR_ASSET_FOLDER,
    "health_bars.png"
)


def _health_bar_color_match(rgb, color_name):
    """Classify health-bar pixels using HSV hue ranges.

    The old RGB rules were too broad. In particular, cyan/teal pixels
    were being classified as GREEN and other coloured UI elements could
    be classified as PURPLE. That caused the player/RL health sprites
    to contain mixed bars.

    These hue ranges are intentionally narrow:
        RED    -> red
        GREEN  -> green / yellow-green
        PURPLE -> purple / magenta
    """

    r, g, b = rgb

    # Ignore very dark pixels.
    if max(r, g, b) < 45:
        return False

    h, s, v = colorsys.rgb_to_hsv(
        r / 255.0,
        g / 255.0,
        b / 255.0,
    )

    hue = h * 360.0

    if color_name == "red":
        return (
            (hue <= 18.0 or hue >= 342.0)
            and s >= 0.45
            and v >= 0.35
        )

    if color_name == "green":
        return (
            70.0 <= hue <= 145.0
            and s >= 0.35
            and v >= 0.30
        )

    if color_name == "purple":
        return (
            245.0 <= hue <= 325.0
            and s >= 0.30
            and v >= 0.25
        )

    return False


def _make_black_transparent(image):
    """Remove the black sprite-sheet background."""

    image = image.convert_alpha()
    image = image.copy()

    width, height = image.get_size()

    for px in range(width):
        for py in range(height):
            r, g, b, a = image.get_at((px, py))

            # The supplied sheet uses black as its empty background.
            if r < 20 and g < 20 and b < 20:
                image.set_at((px, py), (r, g, b, 0))

    return image


def _extract_health_bar_candidates(sheet, color_name):
    """
    Find long horizontal colored regions in the sprite sheet.

    This intentionally filters out the small gem/icon sprites and
    keeps only wide, short bar-like regions.
    """

    width, height = sheet.get_size()

    # First collect horizontal colored runs for every row.
    row_runs = []

    for y in range(height):
        runs = []
        start_x = None

        for x in range(width):
            r, g, b, a = sheet.get_at((x, y))

            is_bar_pixel = (
                a > 0
                and _health_bar_color_match(
                    (r, g, b),
                    color_name
                )
            )

            if is_bar_pixel and start_x is None:
                start_x = x

            elif not is_bar_pixel and start_x is not None:
                if x - start_x >= 8:
                    runs.append((start_x, x - 1))
                start_x = None

        if start_x is not None and width - start_x >= 8:
            runs.append((start_x, width - 1))

        row_runs.append(runs)

    # Merge overlapping runs on neighbouring rows.
    components = []

    for y, runs in enumerate(row_runs):
        for x1, x2 in runs:
            merged = False

            for component in components:
                cx1, cy1, cx2, cy2 = component

                if y <= cy2 + 1 and x1 <= cx2 + 3 and x2 >= cx1 - 3:
                    component[0] = min(cx1, x1)
                    component[1] = min(cy1, y)
                    component[2] = max(cx2, x2)
                    component[3] = max(cy2, y)
                    merged = True
                    break

            if not merged:
                components.append([x1, y, x2, y])

    # A second merge pass handles fragmented anti-aliased rows.
    changed = True

    while changed:
        changed = False

        for i in range(len(components)):
            if changed:
                break

            a = components[i]

            for j in range(i + 1, len(components)):
                b = components[j]

                ax1, ay1, ax2, ay2 = a
                bx1, by1, bx2, by2 = b

                overlap_x = (
                    ax1 <= bx2 + 4
                    and
                    ax2 >= bx1 - 4
                )

                overlap_y = (
                    ay1 <= by2 + 2
                    and
                    ay2 >= by1 - 2
                )

                if overlap_x and overlap_y:
                    components[i] = [
                        min(ax1, bx1),
                        min(ay1, by1),
                        max(ax2, bx2),
                        max(ay2, by2)
                    ]
                    del components[j]
                    changed = True
                    break

    candidates = []

    for x1, y1, x2, y2 in components:
        bar_width = x2 - x1 + 1
        bar_height = y2 - y1 + 1

        # Health bars are wide and short; icons are much more square.
        if bar_width < 25:
            continue

        if bar_height < 2 or bar_height > 18:
            continue

        if bar_width / max(1, bar_height) < 2.5:
            continue

        rect = pygame.Rect(
            max(0, x1 - 1),
            max(0, y1 - 1),
            min(width - max(0, x1 - 1), bar_width + 2),
            min(height - max(0, y1 - 1), bar_height + 2)
        )

        # Measure the amount of the requested colour inside the candidate.
        colored_pixels = 0
        total_pixels = rect.width * rect.height

        for px in range(rect.left, rect.right):
            for py in range(rect.top, rect.bottom):
                r, g, b, a = sheet.get_at((px, py))

                if (
                    a > 0
                    and
                    _health_bar_color_match(
                        (r, g, b),
                        color_name
                    )
                ):
                    colored_pixels += 1

        coverage = (
            colored_pixels / total_pixels
            if total_pixels > 0
            else 0.0
        )

        candidates.append(
            {
                "rect": rect,
                "coverage": coverage
            }
        )

    # Remove near-duplicate detections.
    unique = []

    for candidate in candidates:
        rect = candidate["rect"]

        duplicate = False

        for existing in unique:
            other = existing["rect"]

            if (
                abs(rect.centerx - other.centerx) <= 3
                and
                abs(rect.centery - other.centery) <= 3
                and
                abs(rect.width - other.width) <= 4
                and
                abs(rect.height - other.height) <= 3
            ):
                duplicate = True
                break

        if not duplicate:
            unique.append(candidate)

    # Keep the candidates that look most like actual UI bars.
    # Sorting by coverage lets us retain the different fill states.
    unique.sort(
        key=lambda item: (
            item["coverage"],
            item["rect"].width
        )
    )

    return unique


def _isolate_largest_health_bar_component(image, color_name):
    """Keep only the largest requested-colour bar inside a candidate.

    Some UI sprite sheets place two bars/variants close together. The
    previous extractor could select a candidate containing more than
    one coloured element. We isolate the largest connected component
    of the requested colour and keep a tiny one-pixel border around it.
    """

    width, height = image.get_size()

    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            r, g, b, a = image.get_at((x, y))
            row.append(
                a > 0
                and _health_bar_color_match(
                    (r, g, b),
                    color_name,
                )
            )
        pixels.append(row)

    visited = [
        [False] * width
        for _ in range(height)
    ]

    components = []

    for y in range(height):
        for x in range(width):
            if not pixels[y][x] or visited[y][x]:
                continue

            stack = [(x, y)]
            visited[y][x] = True
            component = []

            while stack:
                cx, cy = stack.pop()
                component.append((cx, cy))

                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if (
                            nx < 0
                            or nx >= width
                            or ny < 0
                            or ny >= height
                        ):
                            continue

                        if visited[ny][nx] or not pixels[ny][nx]:
                            continue

                        visited[ny][nx] = True
                        stack.append((nx, ny))

            components.append(component)

    if not components:
        return image

    # Prefer the largest bar-like component.
    component = max(
        components,
        key=len,
    )

    xs = [point[0] for point in component]
    ys = [point[1] for point in component]

    left = max(0, min(xs) - 1)
    top = max(0, min(ys) - 1)
    right = min(width - 1, max(xs) + 1)
    bottom = min(height - 1, max(ys) + 1)

    cropped = image.subsurface(
        pygame.Rect(
            left,
            top,
            right - left + 1,
            bottom - top + 1,
        )
    ).copy()

    # Remove coloured components that are not part of the selected
    # component. Keep pixels inside the one-pixel border around it.
    selected = set(component)

    for y in range(cropped.get_height()):
        for x in range(cropped.get_width()):
            original_x = left + x
            original_y = top + y

            # Keep pixels that are close to the selected component.
            keep = False
            for nx in range(
                max(0, original_x - 1),
                min(width, original_x + 2),
            ):
                for ny in range(
                    max(0, original_y - 1),
                    min(height, original_y + 2),
                ):
                    if (nx, ny) in selected:
                        keep = True
                        break
                if keep:
                    break

            if not keep:
                r, g, b, a = cropped.get_at((x, y))
                cropped.set_at(
                    (x, y),
                    (r, g, b, 0),
                )

    return cropped


def load_health_bar_sprite_sets():
    """Load and automatically extract red, green and purple bar frames."""

    sprite_sets = {
        "red": [],
        "green": [],
        "purple": []
    }

    if not os.path.exists(HEALTH_BAR_SPRITE_SHEET_PATH):
        print(
            "WARNING: Health-bar sprite sheet not found:",
            os.path.abspath(HEALTH_BAR_SPRITE_SHEET_PATH)
        )
        print(
            "Place the supplied sprite sheet at "
            "assets/ui/health_bars.png"
        )
        return sprite_sets

    try:
        sheet = pygame.image.load(
            HEALTH_BAR_SPRITE_SHEET_PATH
        ).convert_alpha()
    except Exception as exc:
        print(
            "WARNING: Could not load health-bar sprite sheet:",
            exc
        )
        return sprite_sets

    for color_name in sprite_sets:
        candidates = _extract_health_bar_candidates(
            sheet,
            color_name
        )

        for candidate in candidates:
            sprite = sheet.subsurface(
                candidate["rect"]
            ).copy()

            sprite = _make_black_transparent(sprite)

            # A sprite candidate can contain multiple coloured UI
            # elements. Keep only the requested bar colour/component.
            sprite = _isolate_largest_health_bar_component(
                sprite,
                color_name,
            )

            sprite_sets[color_name].append(
                {
                    "image": sprite,
                    "coverage": candidate["coverage"]
                }
            )

        print(
            f"Health-bar sprites loaded: "
            f"{color_name.upper()} = "
            f"{len(sprite_sets[color_name])} frame(s)"
        )

    return sprite_sets


health_bar_sprite_sets = load_health_bar_sprite_sets()


def _select_health_bar_frame(color_name, health_ratio):
    """
    Select the sprite-sheet frame whose coloured coverage is
    closest to the current health ratio.
    """

    frames = health_bar_sprite_sets.get(
        color_name,
        []
    )

    if not frames:
        return None

    health_ratio = max(
        0.0,
        min(1.0, float(health_ratio))
    )

    # The coverage values contain border/glow pixels, so normalize
    # relative to the detected minimum and maximum.
    coverages = [
        frame["coverage"]
        for frame in frames
    ]

    minimum = min(coverages)
    maximum = max(coverages)

    if maximum > minimum:
        target_coverage = (
            minimum +
            health_ratio * (maximum - minimum)
        )
    else:
        target_coverage = maximum

    return min(
        frames,
        key=lambda frame: abs(
            frame["coverage"] -
            target_coverage
        )
    )["image"]


def draw_sprite_health_bar(
    surface,
    color_name,
    health,
    max_health,
    center_x,
    top_y,
    display_width,
    display_height
):
    """Draw a clear, continuously decreasing health bar.

    The previous implementation selected one of the sprite-sheet
    frames based on health ratio.  That made health appear to stay
    unchanged between frames and could also show the wrong amount.

    This version always uses the fullest matching sprite as the
    visual source and clips it continuously according to the exact
    health ratio.  Therefore every small health change is visible.

    RED    -> normal enemies
    GREEN  -> player
    PURPLE -> RL bots
    """

    if max_health is None or max_health <= 0:
        return False

    ratio = max(
        0.0,
        min(1.0, float(health) / float(max_health))
    )

    frames = health_bar_sprite_sets.get(
        color_name,
        []
    )

    if not frames:
        return False

    # IMPORTANT: always use the fullest detected sprite.
    # We do NOT switch between discrete sprite frames anymore.
    # The actual health percentage is represented by clipping this
    # full bar, giving smooth/continuous health reduction.
    full_frame = max(
        frames,
        key=lambda frame: frame.get("coverage", 0)
    )

    sprite = full_frame["image"]

    sprite = pygame.transform.smoothscale(
        sprite,
        (
            max(1, int(display_width)),
            max(1, int(display_height))
        )
    )

    rect = sprite.get_rect(
        midtop=(
            int(center_x),
            int(top_y)
        )
    )

    # ---------------------------------------------------------
    # FULL EMPTY TRACK
    # ---------------------------------------------------------
    # This makes the missing-health portion clearly visible even
    # when the character has only a small amount of HP left.
    track_rect = pygame.Rect(
        rect.left,
        rect.top,
        rect.width,
        rect.height
    )

    pygame.draw.rect(
        surface,
        (18, 18, 18),
        track_rect
    )

    pygame.draw.rect(
        surface,
        (115, 115, 115),
        track_rect,
        1
    )

    # ---------------------------------------------------------
    # CURRENT HEALTH
    # ---------------------------------------------------------
    if ratio > 0.0:
        fill_width = int(round(rect.width * ratio))
        fill_width = max(1, min(rect.width, fill_width))

        old_clip = surface.get_clip()

        surface.set_clip(
            pygame.Rect(
                rect.left,
                rect.top,
                fill_width,
                rect.height
            )
        )

        surface.blit(
            sprite,
            rect.topleft
        )

        surface.set_clip(old_clip)

    # ---------------------------------------------------------
    # STRONG OUTLINE
    # ---------------------------------------------------------
    # Keeps the bar readable against bright and dark parts of the
    # dungeon map.
    pygame.draw.rect(
        surface,
        (220, 220, 220),
        track_rect,
        1
    )

    return True


# =====================================================
# LOAD PICKUP POSITIONS FROM TILED
# =====================================================

def load_pickup_points(layer_name):

    pickup_points = []

    try:

        pickup_layer = (
            tmx_data.get_layer_by_name(
                layer_name
            )
        )

    except ValueError:

        print(
            f"WARNING: {layer_name} layer not found!"
        )

        return pickup_points

    offset_x, offset_y = (
        get_map_offset()
    )

    for obj in pickup_layer:

        pickup_x = (
            offset_x +
            obj.x *
            TILE_SCALE
        )

        pickup_y = (
            offset_y +
            obj.y *
            TILE_SCALE
        )

        pickup_points.append(
            (
                pickup_x,
                pickup_y
            )
        )

    print(
        f"{layer_name} loaded:",
        len(pickup_points)
    )

    return pickup_points


health_pickup_positions = (
    load_pickup_points(
        "health_pickups"
    )
)

ammo_pickup_positions = (
    load_pickup_points(
        "ammo_pickups"
    )
)


# =====================================================
# CREATE ACTIVE PICKUPS
# =====================================================

health_pickups = []

for x, y in health_pickup_positions:

    health_pickups.append(
        {
            "x": x,
            "y": y,
            "collected": False
        }
    )


ammo_pickups = []

for x, y in ammo_pickup_positions:

    ammo_pickups.append(
        {
            "x": x,
            "y": y,
            "collected": False
        }
    )


# =====================================================
# DRAW PICKUPS
# =====================================================

def draw_pickups(screen):

    if health_pack_image is not None:

        for pickup in health_pickups:

            if pickup["collected"]:
                continue

            screen.blit(
                health_pack_image,
                (
                    int(pickup["x"]),
                    int(pickup["y"])
                )
            )

    if ammo_pack_image is not None:

        for pickup in ammo_pickups:

            if pickup["collected"]:
                continue

            screen.blit(
                ammo_pack_image,
                (
                    int(pickup["x"]),
                    int(pickup["y"])
                )
            )


# =====================================================
# CHECK PLAYER PICKUPS
# =====================================================

def update_pickups():

    player_rect = pygame.Rect(
        int(player.x),
        int(player.y),
        player.width,
        player.height
    )

    # ---------------------------------------------
    # HEALTH PICKUPS
    # ---------------------------------------------

    if player.health < 30:

        for pickup in health_pickups:

            if pickup["collected"]:
                continue

            pickup_rect = pygame.Rect(
                int(pickup["x"]),
                int(pickup["y"]),
                max(
                    1,
                    int(PICKUP_SOURCE_SIZE * TILE_SCALE)
                ),
                max(
                    1,
                    int(PICKUP_SOURCE_SIZE * TILE_SCALE)
                )
            )

            if player_rect.colliderect(
                pickup_rect
            ):

                old_health = player.health

                player.health = min(
                    30,
                    player.health +
                    HEALTH_PACK_AMOUNT
                )

                pickup["collected"] = True

                print(
                    "Health pickup collected:",
                    f"{old_health} -> {player.health}"
                )

                # Only collect one pickup per update.
                break


    # ---------------------------------------------
    # AMMO PICKUPS
    # ---------------------------------------------

    if player.current_weapon != "knife":

        for pickup in ammo_pickups:

            if pickup["collected"]:
                continue

            pickup_rect = pygame.Rect(
                int(pickup["x"]),
                int(pickup["y"]),
                max(
                    1,
                    int(PICKUP_SOURCE_SIZE * TILE_SCALE)
                ),
                max(
                    1,
                    int(PICKUP_SOURCE_SIZE * TILE_SCALE)
                )
            )

            if player_rect.colliderect(
                pickup_rect
            ):

                old_ammo = player.ammo

                player.ammo = player.max_ammo

                pickup["collected"] = True

                print(
                    "Ammo pickup collected:",
                    f"{old_ammo} -> {player.ammo}"
                )

                # Only collect one pickup per update.
                break


# =====================================================
# LOAD ENEMY SPAWN POINTS FROM TILED
# =====================================================

def load_enemy_spawn_points():

    spawn_points = []


    try:

        spawn_layer = (
            tmx_data.get_layer_by_name(
                "enemy_spawns"
            )
        )


    except ValueError:

        print(
            "WARNING: enemy_spawns layer not found!"
        )

        return spawn_points


    offset_x, offset_y = (
        get_map_offset()
    )


    for obj in spawn_layer:


        # Convert Tiled coordinates
        # into the same screen coordinates
        # used by the scaled map.

        spawn_x = (
            offset_x +
            obj.x *
            TILE_SCALE
        )

        spawn_y = (
            offset_y +
            obj.y *
            TILE_SCALE
        )


        spawn_points.append(

            (
                spawn_x,
                spawn_y
            )
        )


    print(
        "Enemy spawn points loaded:",
        len(spawn_points)
    )


    return spawn_points


# =====================================================
# LOAD RL BOT SPAWN POINT
# =====================================================
#
# We load it so it is ready for later,
# but DO NOT spawn anything there yet.
#
# =====================================================

def load_rl_bot_spawns():

    spawn_points = []


    try:

        spawn_layer = (
            tmx_data.get_layer_by_name(
                "rl_bot_spawn"
            )
        )


    except ValueError:

        print(
            "WARNING: rl_bot_spawn layer not found!"
        )

        return spawn_points


    offset_x, offset_y = (
        get_map_offset()
    )


    for obj in spawn_layer:

        spawn_x = (
            offset_x +
            obj.x *
            TILE_SCALE
        )

        spawn_y = (
            offset_y +
            obj.y *
            TILE_SCALE
        )


        spawn_points.append(
            (
                spawn_x,
                spawn_y
            )
        )


        print(
            "RL bot spawn point loaded:",
            len(spawn_points),
            ":",
            spawn_x,
            spawn_y
        )


    print(
        "Total RL bot spawn points:",
        len(spawn_points)
    )


    return spawn_points


# =====================================================
# LOAD SPAWN POINTS
# =====================================================

enemy_spawn_points = (
    load_enemy_spawn_points()
)

rl_bot_spawn_points = (
    load_rl_bot_spawns()
)

# Reserved RL bot spawn points.
# RL Bot 1 will use the first point.
# RL Bot 2 will use the second point later.
rl_bot_1_spawn_point = (
    rl_bot_spawn_points[1]
    if len(rl_bot_spawn_points) > 1
    else None
)

rl_bot_2_spawn_point = (
    rl_bot_spawn_points[0]
    if len(rl_bot_spawn_points) > 0
    else None
)


# =====================================================
# FIND VALID ENEMY SPAWN POSITION
# =====================================================

def find_valid_enemy_spawn(
    spawn_x,
    spawn_y,
    existing_enemies
):

    enemy_width = 40
    enemy_height = 40

    # Tiled spawn points represent the top-left position
    # used by Enemy(), so test the same 40x40 body.
    def is_valid_position(x, y):

        test_rect = pygame.Rect(
            int(x),
            int(y),
            enemy_width,
            enemy_height
        )

        # Keep the complete enemy body inside the map.
        if (
            test_rect.left < map_left
            or test_rect.top < map_top
            or test_rect.right > map_right
            or test_rect.bottom > map_bottom
        ):

            return False

        # Enemy must not overlap any obstacle.
        for obstacle in obstacles:

            if test_rect.colliderect(
                obstacle.rect
            ):

                return False

        # Enemy must not spawn on top of another enemy.
        for other in existing_enemies:

            if not other.alive:
                continue

            other_rect = pygame.Rect(
                int(other.x),
                int(other.y),
                other.width,
                other.height
            )

            if test_rect.colliderect(
                other_rect
            ):

                return False

        return True


    # First try the exact Tiled spawn position.
    if is_valid_position(
        spawn_x,
        spawn_y
    ):

        return (
            spawn_x,
            spawn_y
        )


    # If the Tiled point is blocked, search outward
    # in increasing distances for the nearest free spot.
    search_step = 16
    max_search_radius = 256

    for radius in range(
        search_step,
        max_search_radius + search_step,
        search_step
    ):

        # Check points around the original spawn.
        offsets = [
            (0, -radius),
            (radius, 0),
            (0, radius),
            (-radius, 0),

            (radius, -radius),
            (radius, radius),
            (-radius, radius),
            (-radius, -radius)
        ]

        for offset_x, offset_y in offsets:

            candidate_x = (
                spawn_x +
                offset_x
            )

            candidate_y = (
                spawn_y +
                offset_y
            )

            if is_valid_position(
                candidate_x,
                candidate_y
            ):

                print(
                    "Spawn point blocked. "
                    "Moved enemy to nearest valid position:",
                    int(candidate_x),
                    int(candidate_y)
                )

                return (
                    candidate_x,
                    candidate_y
                )


    # No nearby valid position was found.
    print(
        "WARNING: No valid spawn position found near:",
        int(spawn_x),
        int(spawn_y)
    )

    return None


# =====================================================
# SPAWN ENEMIES
# =====================================================

def spawn_wave_enemies(
    enemy_amount
):

    new_enemies = []


    # -------------------------------------------------
    # If there are no Tiled spawn points,
    # use fallback positions, but validate them too.
    # -------------------------------------------------

    if len(enemy_spawn_points) == 0:

        print(
            "No enemy spawn points found."
        )

        attempts = 0
        max_attempts = enemy_amount * 50

        while (
            len(new_enemies) < enemy_amount
            and
            attempts < max_attempts
        ):

            attempts += 1

            fallback_x = random.randint(
                int(map_left),
                int(map_right - 40)
            )

            fallback_y = random.randint(
                int(map_top),
                int(map_bottom - 40)
            )

            valid_position = (
                find_valid_enemy_spawn(
                    fallback_x,
                    fallback_y,
                    new_enemies
                )
            )

            if valid_position is None:
                continue

            spawn_x, spawn_y = valid_position

            new_enemies.append(
                Enemy(
                    spawn_x,
                    spawn_y
                )
            )


        return new_enemies


    # -------------------------------------------------
    # RANDOMLY SELECT SPAWN POINTS
    # -------------------------------------------------

    if (
        enemy_amount <=
        len(enemy_spawn_points)
    ):

        selected_spawns = (
            random.sample(
                enemy_spawn_points,
                enemy_amount
            )
        )


    else:

        # If there are fewer Tiled spawn points than
        # enemies, reuse spawn points.
        selected_spawns = []

        for i in range(
            enemy_amount
        ):

            selected_spawns.append(
                random.choice(
                    enemy_spawn_points
                )
            )


    # -------------------------------------------------
    # CREATE ENEMIES AT VALID POSITIONS
    # -------------------------------------------------

    for spawn_x, spawn_y in selected_spawns:

        valid_position = (
            find_valid_enemy_spawn(
                spawn_x,
                spawn_y,
                new_enemies
            )
        )

        if valid_position is None:
            continue

        valid_x, valid_y = valid_position

        enemy = Enemy(
            valid_x,
            valid_y
        )

        new_enemies.append(
            enemy
        )


    return new_enemies


# =====================================================
# WAVE SYSTEM
# =====================================================

wave = 1


# Exact number of NORMAL enemies
# for each wave.
#
# RL bots are not implemented yet,
# so rl_bot_spawn is NOT used.

WAVE_ENEMY_COUNTS = {

    1: 4,
    2: 5,
    3: 6
}


enemy_count = (
    WAVE_ENEMY_COUNTS[
        wave
    ]
)


# Enemies are spawned after the obstacle layer is loaded
# so their complete 40x40 body can be checked against it.
enemies = []


# =====================================================
# DOOR ANIMATION SYSTEM
# =====================================================
#
# IMPORTANT:
# We do NOT use manually guessed door coordinates anymore.
# A door is identified directly from the Tiled Walls layer:
# if a Walls tile has animation frames, it is treated as a door.
#
# This avoids coordinate/scale/offset mismatches between
# Tiled coordinates and the actual screen coordinates.
# =====================================================

DOOR_ANIMATION_DISTANCE = 70
DOOR_RESET_DISTANCE = 100

# One state per detected door group.
door_states = {}

# Detected animated-door groups are built once after the map loads.
door_groups = []


def get_tile_animation_frames(tmx_data, gid):
    """Return Tiled animation frames for a tile, or None."""

    properties = tmx_data.get_tile_properties_by_gid(gid)

    if not properties:
        return None

    frames = properties.get("frames")

    if not frames:
        return None

    return frames


def get_first_animation_frame(tmx_data, gid):
    """Return the first frame of a Tiled animated tile."""

    frames = get_tile_animation_frames(
        tmx_data,
        gid
    )

    if not frames:
        return tmx_data.get_tile_image_by_gid(gid)

    return tmx_data.get_tile_image_by_gid(
        frames[0].gid
    )


def get_animation_frame(
    tmx_data,
    gid,
    start_time
):
    """Play a Tiled animation once and hold its final frame."""

    frames = get_tile_animation_frames(
        tmx_data,
        gid
    )

    if not frames:
        return tmx_data.get_tile_image_by_gid(gid)

    total_duration = sum(
        frame.duration
        for frame in frames
    )

    if total_duration <= 0:
        return tmx_data.get_tile_image_by_gid(
            frames[-1].gid
        )

    elapsed_time = max(
        0,
        pygame.time.get_ticks() -
        start_time
    )

    current_time = min(
        elapsed_time,
        total_duration - 1
    )

    elapsed = 0

    for frame in frames:

        elapsed += frame.duration

        if current_time < elapsed:

            return tmx_data.get_tile_image_by_gid(
                frame.gid
            )

    return tmx_data.get_tile_image_by_gid(
        frames[-1].gid
    )


def build_door_groups(tmx_data):
    """
    Find all animated tiles on the Walls layer and group
    neighbouring animated tiles into individual doors.

    No hard-coded door coordinates are required.
    """

    groups = []

    try:

        walls_layer = (
            tmx_data.get_layer_by_name(
                "Walls"
            )
        )

    except ValueError:

        print(
            "WARNING: Walls layer not found!"
        )

        return groups

    animated_tiles = []

    for x, y, image in walls_layer.tiles():

        gid = walls_layer.data[y][x]

        frames = get_tile_animation_frames(
            tmx_data,
            gid
        )

        if frames:

            animated_tiles.append(
                {
                    "x": x,
                    "y": y,
                    "gid": gid
                }
            )

    # Group tiles that touch/are immediately beside each other.
    # This handles doors made from several animated tiles.
    remaining = set(
        range(len(animated_tiles))
    )

    while remaining:

        seed_index = remaining.pop()

        group_indices = [
            seed_index
        ]

        queue = [
            seed_index
        ]

        while queue:

            current_index = queue.pop()

            current = animated_tiles[
                current_index
            ]

            for other_index in list(
                remaining
            ):

                other = animated_tiles[
                    other_index
                ]

                dx = abs(
                    current["x"] -
                    other["x"]
                )

                dy = abs(
                    current["y"] -
                    other["y"]
                )

                # Adjacent horizontally, vertically, or diagonally.
                if (
                    dx <= 1
                    and
                    dy <= 1
                ):

                    remaining.remove(
                        other_index
                    )

                    group_indices.append(
                        other_index
                    )

                    queue.append(
                        other_index
                    )

        groups.append(
            [
                animated_tiles[index]
                for index in group_indices
            ]
        )

    print(
        "Animated door groups detected:",
        len(groups)
    )

    for index, group in enumerate(groups):

        print(
            f"  Door {index + 1}:",
            len(group),
            "animated tile(s)"
        )

    return groups


# =====================================================
# DRAW TILED MAP
# =====================================================

def draw_tiled_map(
    screen,
    tmx_data
):

    tile_scale = TILE_SCALE

    map_width = (
        tmx_data.width *
        tmx_data.tilewidth
    )

    map_height = (
        tmx_data.height *
        tmx_data.tileheight
    )

    map_surface = pygame.Surface(
        (
            map_width,
            map_height
        ),
        pygame.SRCALPHA
    )

    for layer in tmx_data.visible_layers:

        if layer.name == "traps":
            continue

        if hasattr(
            layer,
            "tiles"
        ):

            for x, y, image in layer.tiles():

                gid = layer.data[y][x]

                # -----------------------------------------
                # WALLS
                # -----------------------------------------
                #
                # Animated Walls tiles are doors.
                # Draw their FIRST frame here.
                #
                # This is critical: never use the global
                # pygame clock for doors.
                # -----------------------------------------

                if layer.name == "Walls":

                    frames = get_tile_animation_frames(
                        tmx_data,
                        gid
                    )

                    if frames:

                        # DO NOT draw animated door tiles in the
                        # base map. draw_door_foreground() is the
                        # only place that draws them. Otherwise the
                        # closed door remains underneath the opening
                        # animation and the door appears to still be
                        # there after it opens.
                        continue

                # -----------------------------------------
                # OTHER ANIMATED MAP TILES
                # -----------------------------------------

                else:

                    properties = (
                        tmx_data.get_tile_properties_by_gid(
                            gid
                        )
                    )

                    if (
                        properties
                        and
                        properties.get("frames")
                    ):

                        frames = properties["frames"]

                        total_duration = sum(
                            frame.duration
                            for frame in frames
                        )

                        if total_duration > 0:

                            current_time = (
                                pygame.time.get_ticks()
                                % total_duration
                            )

                            elapsed = 0

                            for frame in frames:

                                elapsed += frame.duration

                                if current_time < elapsed:

                                    animated_image = (
                                        tmx_data.get_tile_image_by_gid(
                                            frame.gid
                                        )
                                    )

                                    if animated_image is not None:

                                        image = animated_image

                                    break

                map_surface.blit(
                    image,
                    (
                        x * tmx_data.tilewidth,
                        y * tmx_data.tileheight
                    )
                )

    enlarged_width = int(
        map_width *
        tile_scale
    )

    enlarged_height = int(
        map_height *
        tile_scale
    )

    map_surface = pygame.transform.scale(
        map_surface,
        (
            enlarged_width,
            enlarged_height
        )
    )

    offset_x, offset_y = (
        get_map_offset()
    )

    screen.blit(
        map_surface,
        (
            offset_x,
            offset_y
        )
    )

# =====================================================
# CHECK IF ACTOR IS NEAR DOOR
# =====================================================

def is_actor_near_door(door_rect):

    actors = []

    # Player
    actors.append(player)

    # Normal enemies
    for enemy in enemies:

        if enemy.alive:
            actors.append(enemy)

    # RL Bot 1
    if rl_bot_1 is not None and rl_bot_1.alive:
        actors.append(rl_bot_1)

    # RL Bot 2
    if rl_bot_2 is not None and rl_bot_2.alive:
        actors.append(rl_bot_2)

    door_center_x, door_center_y = (
        door_rect.center
    )

    for actor in actors:

        actor_center_x = (
            actor.x +
            actor.width / 2
        )

        actor_center_y = (
            actor.y +
            actor.height / 2
        )

        dx = (
            actor_center_x -
            door_center_x
        )

        dy = (
            actor_center_y -
            door_center_y
        )

        distance = math.sqrt(
            dx * dx +
            dy * dy
        )

        if distance <= DOOR_ANIMATION_DISTANCE:

            return True

    return False
# =====================================================
# DRAW DOORS
# =====================================================

def draw_door_foreground(screen, tmx_data):

    # -------------------------------------------------
    # Keep the existing 13 doorway positions.
    # These are screen-space areas and are used only to
    # identify which Walls tiles belong to a doorway.
    # -------------------------------------------------

    tile_scale = TILE_SCALE

    map_width = (
        tmx_data.width *
        tmx_data.tilewidth
    )

    map_height = (
        tmx_data.height *
        tmx_data.tileheight
    )

    enlarged_width = int(
        map_width *
        tile_scale
    )

    enlarged_height = int(
        map_height *
        tile_scale
    )

    screen_width, screen_height = (
        screen.get_size()
    )

    offset_x = (
        screen_width -
        enlarged_width
    ) // 2

    # Keep the same -30 vertical correction used by the
    # existing map/obstacle positioning.
    offset_y = (
        screen_height -
        enlarged_height
    ) // 2

    walls_layer = tmx_data.get_layer_by_name(
        "Walls"
    )

    door_areas = [

        # 1. Top-left door
        pygame.Rect(55, 30, 30, 80),

        # 2. Upper-middle wooden door
        pygame.Rect(433, 60, 30, 80),

        # 3. Top-center gate
        pygame.Rect(643, 0, 30, 80),

        # 4. Top-right gate
        pygame.Rect(903, 35, 30, 80),

        # 5. Left-middle wooden door
        pygame.Rect(65, 270, 30, 80),

        # 6. Center-left gate
        pygame.Rect(197, 380, 30, 80),

        # 7. Center gate
        pygame.Rect(433, 270, 30, 80),

        # 8. Right-middle gate
        pygame.Rect(642, 350, 30, 80),

        # 9. Lower-center gate
        pygame.Rect(540, 450, 30, 80),

        # 10. Lower-center wooden door
        pygame.Rect(408, 530, 30, 80),

        # 11. Lower-left gate
        pygame.Rect(223, 530, 30, 80),

        # 12. Right-side wooden door
        pygame.Rect(903, 480, 30, 80),

        # 13. Bottom-right gate
        pygame.Rect(903, 600, 30, 80),
    ]

    # -------------------------------------------------
    # Find which doorway an actor is nearest to.
    # We calculate using the complete doorway rectangle,
    # not one individual wall tile.
    # -------------------------------------------------

    actors = [player]

    for enemy in enemies:

        if enemy.alive:
            actors.append(enemy)

    if (
        rl_bot_1 is not None
        and rl_bot_1.alive
    ):
        actors.append(rl_bot_1)

    if (
        rl_bot_2 is not None
        and rl_bot_2.alive
    ):
        actors.append(rl_bot_2)

    current_time = pygame.time.get_ticks()

    # -------------------------------------------------
    # UPDATE EACH DOOR STATE FIRST.
    #
    # This is separate from drawing so every tile
    # belonging to the same door gets the same state.
    # -------------------------------------------------

    for door_index, door_area in enumerate(
        door_areas
    ):

        actor_near = False

        # Use the nearest point on the doorway rectangle
        # to the actor center. This gives cleaner opening
        # behavior when the actor approaches from any side.
        for actor in actors:

            actor_center = pygame.Vector2(
                actor.x + actor.width / 2,
                actor.y + actor.height / 2
            )

            closest_x = max(
                door_area.left,
                min(
                    actor_center.x,
                    door_area.right
                )
            )

            closest_y = max(
                door_area.top,
                min(
                    actor_center.y,
                    door_area.bottom
                )
            )

            dx = (
                actor_center.x -
                closest_x
            )

            dy = (
                actor_center.y -
                closest_y
            )

            distance = math.sqrt(
                dx * dx +
                dy * dy
            )

            if distance <= DOOR_ANIMATION_DISTANCE:

                actor_near = True
                break

        # Create state once.
        if door_index not in door_states:

            door_states[door_index] = {
                "open": False,
                "start_time": 0
            }

        state = door_states[
            door_index
        ]

        # ---------------------------------------------
        # OPEN
        # ---------------------------------------------

        if actor_near:

            if not state["open"]:

                state["open"] = True

                state["start_time"] = current_time

        # ---------------------------------------------
        # CLOSE
        # ---------------------------------------------

        else:

            # Keep it open until every actor is beyond
            # the larger reset distance.
            actor_still_near = False

            for actor in actors:

                actor_center = pygame.Vector2(
                    actor.x + actor.width / 2,
                    actor.y + actor.height / 2
                )

                closest_x = max(
                    door_area.left,
                    min(
                        actor_center.x,
                        door_area.right
                    )
                )

                closest_y = max(
                    door_area.top,
                    min(
                        actor_center.y,
                        door_area.bottom
                    )
                )

                dx = (
                    actor_center.x -
                    closest_x
                )

                dy = (
                    actor_center.y -
                    closest_y
                )

                distance = math.sqrt(
                    dx * dx +
                    dy * dy
                )

                if distance <= DOOR_RESET_DISTANCE:

                    actor_still_near = True
                    break

            if not actor_still_near:

                state["open"] = False
                state["start_time"] = 0

    # -------------------------------------------------
    # DRAW THE DOOR TILES.
    #
    # Animated Walls tiles were skipped by
    # draw_tiled_map(), so they are drawn here.
    # -------------------------------------------------

    for x, y, original_image in walls_layer.tiles():

        wall_x = int(
            offset_x +
            x *
            tmx_data.tilewidth *
            tile_scale
        )

        wall_y = int(
            offset_y - 30 +
            y *
            tmx_data.tileheight *
            tile_scale
        )

        wall_width = int(
            original_image.get_width() *
            tile_scale
        )

        wall_height = int(
            original_image.get_height() *
            tile_scale
        )

        wall_rect = pygame.Rect(
            wall_x,
            wall_y,
            wall_width,
            wall_height
        )

        # Find the doorway containing this tile.
        door_index = None

        for index, door_area in enumerate(
            door_areas
        ):

            if door_area.colliderect(
                wall_rect
            ):

                door_index = index
                break

        if door_index is None:
            continue

        # Get the actual Tiled tile GID.
        gid = walls_layer.data[y][x]

        # Ignore empty/invalid GIDs.
        if gid == 0:
            continue

        state = door_states.get(
            door_index,
            {
                "open": False,
                "start_time": 0
            }
        )

        image = original_image

        # -------------------------------------------------
        # ONLY ANIMATED TILES USE THE DOOR ANIMATION.
        # -------------------------------------------------

        frames = get_tile_animation_frames(
            tmx_data,
            gid
        )

        if frames:

            if state["open"]:

                animated_image = get_animation_frame(
                    tmx_data,
                    gid,
                    state["start_time"]
                )

                if animated_image is not None:

                    image = animated_image

            else:

                closed_image = get_first_animation_frame(
                    tmx_data,
                    gid
                )

                if closed_image is not None:

                    image = closed_image

        # -------------------------------------------------
        # DRAW
        # -------------------------------------------------

        scaled_image = pygame.transform.scale(
            image,
            (
                wall_width,
                wall_height
            )
        )

        screen.blit(
            scaled_image,
            (
                wall_x,
                wall_y
            )
        )


# =====================================================
# =====================================================
# LOAD OBSTACLES
# =====================================================

def load_obstacles(
    tmx_data
):

    tile_scale = TILE_SCALE


    map_width = (
        tmx_data.width *
        tmx_data.tilewidth
    )

    map_height = (
        tmx_data.height *
        tmx_data.tileheight
    )


    enlarged_width = int(
        map_width *
        tile_scale
    )

    enlarged_height = int(
        map_height *
        tile_scale
    )


    screen_width, screen_height = (
        screen.get_size()
    )


    offset_x = (
        screen_width -
        enlarged_width
    ) // 2


    offset_y = (
        (
            screen_height -
            enlarged_height
        ) // 2
    ) - 30


    loaded_obstacles = []


    obstacle_layer = (
        tmx_data.get_layer_by_name(
            "obstacle"
        )
    )


    for obj in obstacle_layer:

        x = (
            offset_x +
            obj.x *
            tile_scale
        )

        y = (
            offset_y +
            obj.y *
            tile_scale
        )


        width = (
            obj.width *
            tile_scale
        )

        height = (
            obj.height *
            tile_scale
        )


        loaded_obstacles.append(

            Obstacle(
                int(x),
                int(y),
                int(width),
                int(height)
            )
        )


    return loaded_obstacles


# =====================================================
# LOAD OBSTACLES
# =====================================================

obstacles = load_obstacles(
    tmx_data
)


# Detect animated door tiles directly from the Tiled Walls layer.
door_groups = build_door_groups(tmx_data)


# =====================================================
# SET ACTUAL MAP BOUNDS FOR ALL ENEMIES
# =====================================================

map_left, map_top, map_right, map_bottom = (
    get_map_bounds()
)

# =====================================================
# RL BOT WORLD INTEGRATION
# =====================================================
#
# Bot decision-making is implemented inside RLBot.
# main.py only connects the bot to the game world:
#   - spawning
#   - drawing
#   - creating bullets
#   - exposing pickups/obstacles to the bot
#
# This keeps the game engine separate from the bot's policy.
# =====================================================

rl_bot_1 = None
rl_bot_2 = None
# Last melee time for each RL bot
rl_bot_last_melee = {}
RL_BOT_MELEE_COOLDOWN = 500


# Gymnasium environments connected to the real game objects.
# They do not create a second/fake game world.
rl_env_1 = TacticalShooterEnv()
rl_env_2 = TacticalShooterEnv()

# -----------------------------------------------------
# TRAINED DQN FOR RL BOT 1
# -----------------------------------------------------
# The game uses the trained 34-observation / 9-action
# DQN model for both RL bots. A single loaded network is
# shared for inference; each bot has its own environment,
# observation, action and timing state.
#
# There is NO fallback to the old temporary rule-based policy.

RL_BOT_1_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "models",
    "rl_bot_1_dqn_final.pt"
)

rl_bot_1_dqn = None


def load_rl_bot_1_dqn():
    global rl_bot_1_dqn

    if not os.path.exists(RL_BOT_1_MODEL_PATH):
        raise FileNotFoundError(
            "RL Bot 1 DQN model was not found: "
            f"{os.path.abspath(RL_BOT_1_MODEL_PATH)}"
        )

    # Final model contract:
    #   state_size = 34
    #   action_size = 9
    rl_bot_1_dqn = DQNAgent(
        state_size=34,
        action_size=9,
        batch_size=64
    )

    try:
        rl_bot_1_dqn.load(
            RL_BOT_1_MODEL_PATH,
            training=False
        )
    except Exception as exc:
        rl_bot_1_dqn = None
        raise RuntimeError(
            "RL Bot 1 DQN model could not be loaded. "
            "The model must be the 34-state / 9-action model. "
            f"Original error: {exc}"
        ) from exc

    # Deterministic inference in the actual game.
    rl_bot_1_dqn.epsilon = 0.0

    print(
        "RL Bot 1 DQN loaded:",
        os.path.abspath(RL_BOT_1_MODEL_PATH)
    )
    print(
        "RL Bot 1 DQN device:",
        rl_bot_1_dqn.device
    )
    print(
        "RL Bot 1 DQN contract: 34 observations / 9 actions"
    )


# Load the trained 34-state model immediately at startup.
load_rl_bot_1_dqn()


def create_rl_bot(
    spawn_point,
    bot_number
):

    if spawn_point is None:

        print(
            f"WARNING: RL Bot {bot_number} has no spawn point."
        )

        return None

    bot = RLBot(
        spawn_point[0],
        spawn_point[1]
    )

    bot.bot_number = bot_number

    if hasattr(
        bot,
        "set_navigation_bounds"
    ):

        bot.set_navigation_bounds(
            map_left,
            map_top,
            map_right,
            map_bottom
        )

    print(
        f"RL Bot {bot_number} spawned at:",
        int(spawn_point[0]),
        int(spawn_point[1])
    )

    return bot


# =====================================================
# RL BOT HEALTH BAR
# =====================================================

def draw_rl_bot_health_bar(
    screen,
    bot
):

    if bot is None or not bot.alive:
        return

    # Cover the old 50x6 rectangle drawn by the previous
    # health-bar implementation inside RL rendering.
    old_bar_rect = pygame.Rect(
        int(bot.x + bot.width / 2 - 31),
        int(bot.y - 14),
        62,
        12
    )

    pygame.draw.rect(
        screen,
        (0, 0, 0),
        old_bar_rect
    )

    draw_sprite_health_bar(
        screen,
        "purple",
        bot.health,
        bot.max_health,
        bot.x + bot.width / 2,
        bot.y - 14,
        64,
        11
    )


# =====================================================
# CREATE RL BOT BULLET
# =====================================================

def create_rl_bot_bullet(
    bot
):

    if bot is None or not bot.alive:
        return

    # IMPORTANT:
    # TacticalShooterEnv already calls bot.shoot() and only
    # invokes this callback when that shot was successfully
    # fired. Calling bot.shoot() again here would consume a
    # second round / fail because of the cooldown and could
    # prevent the actual bullet from being created.
    #
    # This callback ONLY creates the real PyGame bullet.

    if bot.current_weapon == "knife":
        return

    bot_center_x, bot_center_y = (
        bot.get_center()
    )

    target_x = (
        bot_center_x +
        bot.facing_x *
        1000
    )

    target_y = (
        bot_center_y +
        bot.facing_y *
        1000
    )

    muzzle_distance = 35

    muzzle_x = (
        bot_center_x +
        bot.facing_x *
        muzzle_distance
    )

    muzzle_y = (
        bot_center_y +
        bot.facing_y *
        muzzle_distance
    )

    enemy_bullets.append(
        Bullet(
            muzzle_x,
            muzzle_y,
            target_x,
            target_y,
            damage=bot.get_damage(),
            owner="rl_bot"
        )
    )


# =====================================================
# RL BOT MELEE WORLD EFFECT
# =====================================================

def rl_bot_melee_attack(
    bot
):

    if bot is None or not bot.alive:
        return False

    current_time = pygame.time.get_ticks()

    bot_number = getattr(
        bot,
        "bot_number",
        1
    )

    last_time = rl_bot_last_melee.get(
        bot_number,
        0
    )

    if (
        current_time -
        last_time
        <
        RL_BOT_MELEE_COOLDOWN
    ):
        return False

    # TacticalShooterEnv already executed bot.melee()
    # before calling this callback. Do NOT call melee_attack()
    # again here because that would trigger the action twice.
    rl_bot_last_melee[
        bot_number
    ] = current_time

    bot_center_x, bot_center_y = (
        bot.get_center()
    )

    player_center_x = (
        player.x +
        player.width / 2
    )

    player_center_y = (
        player.y +
        player.height / 2
    )

    dx = (
        player_center_x -
        bot_center_x
    )

    dy = (
        player_center_y -
        bot_center_y
    )

    distance = math.sqrt(
        dx * dx +
        dy * dy
    )

    if distance > bot.RL_MELEE_RANGE:
        return True

    if distance <= 0:
        return True

    direction_x = dx / distance
    direction_y = dy / distance

    bot_angle = math.degrees(
        math.atan2(
            bot.facing_y,
            bot.facing_x
        )
    )

    player_angle = math.degrees(
        math.atan2(
            direction_y,
            direction_x
        )
    )

    angle_difference = (
        (
            player_angle -
            bot_angle +
            180
        )
        % 360
        - 180
    )

    if abs(angle_difference) <= 45:

        melee_damage = bot.get_melee_damage()

        if melee_damage is not None:

            player.health -= melee_damage

            player.health = max(
                0,
                player.health
            )

            print(
                f"RL Bot {bot_number} melee hit! "
                f"Damage: {melee_damage} | "
                f"Player health: {player.health}"
            )

    return True


# =====================================================
# UPDATE ONE RL BOT
# =====================================================

def update_rl_bot(
    bot,
    env
):

    if bot is None or not bot.alive:
        return

    env.set_game_state(
        player=player,
        bot=bot,
        obstacles=obstacles,
        health_pickups=health_pickups,
        ammo_pickups=ammo_pickups,
        shoot_callback=create_rl_bot_bullet,
        melee_callback=rl_bot_melee_attack
    )

    bot_number = getattr(bot, "bot_number", 1)

    # -------------------------------------------------
    # DQN DECISION
    # -------------------------------------------------
    #
    # BOTH RL bots use the trained 34-observation / 9-action
    # DQN during actual gameplay.
    #
    # We intentionally do NOT call RLBot.choose_action()
    # here. That function is the older temporary rule-based
    # controller and expects a different Player interface.
    #
    # Each bot keeps its own observation/action state even
    # though both bots use the same trained network for inference.
    # -------------------------------------------------

    if rl_bot_1_dqn is None:
        raise RuntimeError(
            "RL DQN is not loaded. "
            "Both RL bots require the trained 34-state / 9-action model."
        )

    if not hasattr(bot, "last_rl_observation"):
        observation, _ = env.reset()
        bot.last_rl_observation = observation
        bot.last_rl_action = 0

    # The game renders at 60 FPS, while the RL environment
    # makes one decision every 0.1 s = 6 frames.
    if env.needs_new_action():

        action = rl_bot_1_dqn.choose_action(
            bot.last_rl_observation,
            training=False
        )

        bot.last_rl_action = int(action)

        try:
            debug_distance = env._distance_to_player()
        except Exception:
            debug_distance = float("nan")

        debug_action_names = {
            0: "IDLE",
            1: "FORWARD",
            2: "BACKWARD",
            3: "LEFT",
            4: "RIGHT",
            5: "SPRINT",
            6: "SHOOT",
            7: "RELOAD",
            8: "MELEE"
        }

        debug_action_name = debug_action_names.get(
            int(action),
            "UNKNOWN"
        )

        print(
            f"RL BOT {bot_number} DECISION | "
            f"distance={debug_distance:.1f} | "
            f"action={int(action)} "
            f"({debug_action_name}) | "
            f"weapon={bot.current_weapon} | "
            f"health={bot.health:.1f} | "
            f"player_health={player.health:.1f}"
        )

    else:
        action = getattr(
            bot,
            "last_rl_action",
            0
        )

    # Advance the RL bot's own timers once per rendered frame.
    # main.py previously did not call RLBot.update(), so a
    # successful shot could leave shoot_cooldown/reload_timer
    # stuck forever.
    bot.update(1.0 / 60.0)

    (
        observation,
        reward,
        terminated,
        truncated,
        info
    ) = env.step(action)

    bot.last_rl_action = int(action)
    bot.last_rl_reward = reward
    bot.last_rl_observation = observation

    if terminated or truncated:

        if bot.alive and player.health > 0:
            reset_observation, _ = env.reset()
            bot.last_rl_observation = reset_observation


# =====================================================
# UPDATE ALL RL BOTS
# =====================================================

def update_rl_bots():

    if rl_bot_1 is not None:

        update_rl_bot(
            rl_bot_1,
            rl_env_1
        )

    if rl_bot_2 is not None:

        update_rl_bot(
            rl_bot_2,
            rl_env_2
        )


# =====================================================
# DRAW ALL RL BOTS
# =====================================================

def draw_rl_bots():

    if rl_bot_1 is not None:

        rl_bot_1.draw(
            screen
        )

        draw_rl_bot_health_bar(
            screen,
            rl_bot_1
        )

    if rl_bot_2 is not None:

        rl_bot_2.draw(
            screen
        )

        draw_rl_bot_health_bar(
            screen,
            rl_bot_2
        )


# =====================================================
# NORMAL ENEMY HEALTH BAR
# =====================================================

def draw_enemy_health_bar(
    screen,
    enemy
):

    if enemy is None or not enemy.alive:
        return

    # The current Enemy.draw() implementation already draws its
    # old 40x6 rectangle.  Cover that small area before drawing
    # the new RED sprite so enemy.py does not need to be changed.
    old_bar_rect = pygame.Rect(
        int(enemy.x - 2),
        int(enemy.y - 14),
        int(enemy.width + 4),
        12
    )

    pygame.draw.rect(
        screen,
        (0, 0, 0),
        old_bar_rect
    )

    draw_sprite_health_bar(
        screen,
        "red",
        enemy.health,
        30,
        enemy.x + enemy.width / 2,
        enemy.y - 14,
        50,
        9
    )


# =====================================================
# SPAWN WAVE 1
# =====================================================

enemies = spawn_wave_enemies(
    enemy_count
)


for enemy in enemies:

    enemy.set_navigation_bounds(
        map_left,
        map_top,
        map_right,
        map_bottom
    )


# =====================================================
# FIND THE ONE ACTIVE ENEMY
# =====================================================

def update_active_enemy():

    global active_enemy

    # -------------------------------------------------
    # If the current active enemy died, release it.
    # -------------------------------------------------

    if (
        active_enemy is not None
        and not active_enemy.alive
    ):

        active_enemy.set_active(False)
        active_enemy = None


    # -------------------------------------------------
    # If the current active enemy is still close
    # enough, keep it active.
    # -------------------------------------------------

    if active_enemy is not None:

        enemy_center_x = (
            active_enemy.x +
            active_enemy.width / 2
        )

        enemy_center_y = (
            active_enemy.y +
            active_enemy.height / 2
        )

        player_center_x = (
            player.x +
            player.width / 2
        )

        player_center_y = (
            player.y +
            player.height / 2
        )

        dx = (
            enemy_center_x -
            player_center_x
        )

        dy = (
            enemy_center_y -
            player_center_y
        )

        distance = math.sqrt(
            dx ** 2 +
            dy ** 2
        )

        # Keep the active enemy while the player remains
        # within the activation distance.
        if distance <= ENEMY_DEACTIVATION_DISTANCE:

            return

        # Player moved away, so release this enemy.
        active_enemy.set_active(False)
        active_enemy = None


    # -------------------------------------------------
    # Find the closest eligible enemy.
    # -------------------------------------------------

    closest_enemy = None
    closest_distance = float("inf")

    player_center_x = (
        player.x +
        player.width / 2
    )

    player_center_y = (
        player.y +
        player.height / 2
    )

    for enemy in enemies:

        if not enemy.alive:
            continue

        enemy_center_x = (
            enemy.x +
            enemy.width / 2
        )

        enemy_center_y = (
            enemy.y +
            enemy.height / 2
        )

        dx = (
            enemy_center_x -
            player_center_x
        )

        dy = (
            enemy_center_y -
            player_center_y
        )

        distance = math.sqrt(
            dx ** 2 +
            dy ** 2
        )

        if (
            distance <= ENEMY_ACTIVATION_DISTANCE
            and
            distance < closest_distance
        ):

            closest_enemy = enemy
            closest_distance = distance


    # -------------------------------------------------
    # Activate ONLY the closest enemy.
    # -------------------------------------------------

    if closest_enemy is not None:

        active_enemy = closest_enemy

        active_enemy.set_active(True)


# =====================================================
# RESET GAME FOR A NEW SESSION
# =====================================================

def reset_game():
    """
    Reset the normal game session when the player starts again
    from the main menu.

    This only resets game-session state.  The RL model,
    TacticalShooterEnv class, RL action/state definitions,
    scripted enemy behaviour, and training code are untouched.
    """
    global player
    global bullets, enemy_bullets
    global score
    global wave, enemy_count, enemies, active_enemy
    global rl_bot_1, rl_bot_2
    global rl_bot_last_melee
    global last_melee_time

    player = Player()

    bullets.clear()
    enemy_bullets.clear()

    score = 0
    wave = 1
    enemy_count = WAVE_ENEMY_COUNTS[wave]
    active_enemy = None

    # RL bots only enter during Waves 2 and 3.
    rl_bot_1 = None
    rl_bot_2 = None
    rl_bot_last_melee.clear()

    last_melee_time = 0

    # Restore every pickup for the new run.
    for pickup in health_pickups:
        pickup["collected"] = False

    for pickup in ammo_pickups:
        pickup["collected"] = False

    # Reset door animation state.
    for state in door_states.values():
        state["open"] = False
        state["start_time"] = 0

    # Spawn a fresh Wave 1.
    enemies = spawn_wave_enemies(enemy_count)

    for enemy in enemies:
        enemy.set_navigation_bounds(
            map_left,
            map_top,
            map_right,
            map_bottom
        )


# =====================================================
# MAIN LOOP
# =====================================================

running = True


while running:


    # =================================================
    # EVENTS
    # =================================================

    for event in pygame.event.get():


        # ---------------------------------------------
        # QUIT
        # ---------------------------------------------

        if event.type == pygame.QUIT:

            running = False


        # ---------------------------------------------
        # KEYBOARD
        # ---------------------------------------------

        if event.type == pygame.KEYDOWN:


            # -----------------------------------------
            # ESC
            # -----------------------------------------

            if event.key == pygame.K_ESCAPE:

                if game_state == "PLAYING":
                    game_state = "PAUSED"

                elif game_state == "PAUSED":
                    game_state = "PLAYING"

                elif game_state in (
                    "GAME_OVER",
                    "LEVEL_COMPLETE"
                ):
                    game_state = "MENU"


            # -----------------------------------------
            # ENTER → START / RESUME
            # -----------------------------------------

            if event.key == pygame.K_RETURN:

                if game_state == "MENU":
                    reset_game()
                    game_state = "PLAYING"

                elif game_state == "PAUSED":
                    game_state = "PLAYING"


            # -----------------------------------------
            # Q → SWITCH WEAPON
            # -----------------------------------------

            if (
                event.key == pygame.K_q
                and
                game_state == "PLAYING"
            ):

                player.switch_weapon()


            # -----------------------------------------
            # R → RELOAD
            # -----------------------------------------

            if (
                event.key == pygame.K_r
                and
                game_state == "PLAYING"
            ):

                player.reload()


            # -----------------------------------------
            # SPACE → PLAYER MELEE
            # -----------------------------------------

            if (
                event.key == pygame.K_SPACE
                and
                game_state == "PLAYING"
            ):

                current_time = (
                    pygame.time.get_ticks()
                )


                if (
                    current_time -
                    last_melee_time
                    >=
                    MELEE_COOLDOWN
                ):

                    melee_started = (
                        player.melee_attack()
                    )


                    if melee_started:

                        last_melee_time = (
                            current_time
                        )


                        player_center_x = (
                            player.x +
                            player.width // 2
                        )

                        player_center_y = (
                            player.y +
                            player.height // 2
                        )


                        mouse_x, mouse_y = (
                            pygame.mouse.get_pos()
                        )


                        direction_x = (
                            mouse_x -
                            player_center_x
                        )

                        direction_y = (
                            mouse_y -
                            player_center_y
                        )


                        player_angle = (
                            math.degrees(
                                math.atan2(
                                    direction_y,
                                    direction_x
                                )
                            )
                        )


                        for enemy in enemies:

                            if not enemy.alive:

                                continue


                            enemy_center_x = (
                                enemy.x +
                                enemy.width // 2
                            )

                            enemy_center_y = (
                                enemy.y +
                                enemy.height // 2
                            )


                            dx = (
                                enemy_center_x -
                                player_center_x
                            )

                            dy = (
                                enemy_center_y -
                                player_center_y
                            )


                            distance = (
                                math.sqrt(
                                    dx ** 2 +
                                    dy ** 2
                                )
                            )


                            if (
                                distance >
                                MELEE_RANGE
                            ):

                                continue


                            enemy_angle = (
                                math.degrees(
                                    math.atan2(
                                        dy,
                                        dx
                                    )
                                )
                            )


                            angle_difference = (
                                (
                                    enemy_angle -
                                    player_angle +
                                    180
                                )
                                % 360
                                - 180
                            )


                            if (
                                abs(
                                    angle_difference
                                )
                                <=
                                MELEE_ANGLE / 2
                            ):

                                melee_damage = (
                                    player.get_melee_damage()
                                )


                                enemy.health -= (
                                    melee_damage
                                )


                                print(
                                    f"{player.current_weapon} "
                                    f"melee hit! Damage: "
                                    f"{melee_damage} | "
                                    f"Enemy health: "
                                    f"{enemy.health}"
                                )


                                if (
                                    enemy.health <= 0
                                ):

                                    enemy.health = 0

                                    enemy.alive = False

                                    score += 10


        # =============================================
        # MENU / PAUSE BUTTON CLICKS
        # =============================================

        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and
            event.button == 1
        ):

            mouse_position = event.pos

            if game_state == "MENU":

                if main_menu_start_button.rect.collidepoint(
                    mouse_position
                ):
                    reset_game()
                    game_state = "PLAYING"

                elif main_menu_exit_button.rect.collidepoint(
                    mouse_position
                ):
                    running = False

            elif game_state == "PAUSED":

                if pause_resume_button.rect.collidepoint(
                    mouse_position
                ):
                    game_state = "PLAYING"

                elif pause_exit_button.rect.collidepoint(
                    mouse_position
                ):
                    game_state = "MENU"

            elif game_state == "GAME_OVER":

                if death_back_button.rect.collidepoint(
                    mouse_position
                ):
                    game_state = "MENU"

            elif game_state == "LEVEL_COMPLETE":

                if victory_back_button.rect.collidepoint(
                    mouse_position
                ):
                    game_state = "MENU"


        # =============================================
        # LEFT MOUSE → PLAYER SHOOT
        # =============================================

        if (
            game_state == "PLAYING"
            and
            event.type == pygame.MOUSEBUTTONDOWN
            and
            event.button == 1
        ):

            mouse_x, mouse_y = (
                pygame.mouse.get_pos()
            )


            shoot_started = (
                player.shoot()
            )


            if shoot_started:

                center_x = (
                    player.x +
                    player.width // 2
                )

                center_y = (
                    player.y +
                    player.height // 2
                )


                dx = (
                    mouse_x -
                    center_x
                )

                dy = (
                    mouse_y -
                    center_y
                )


                distance = (
                    math.sqrt(
                        dx ** 2 +
                        dy ** 2
                    )
                )


                if distance != 0:

                    direction_x = (
                        dx /
                        distance
                    )

                    direction_y = (
                        dy /
                        distance
                    )


                    muzzle_distance = 35


                    muzzle_x = (
                        center_x +
                        direction_x *
                        muzzle_distance
                    )

                    muzzle_y = (
                        center_y +
                        direction_y *
                        muzzle_distance
                    )


                    bullets.append(

                        Bullet(
                            muzzle_x,
                            muzzle_y,
                            mouse_x,
                            mouse_y,
                            damage=(
                                player.get_damage()
                            ),
                            owner="player"
                        )
                    )


    # =================================================
    # DRAW MAP
    # =================================================

    draw_tiled_map(
        screen,
        tmx_data
    )

    # Pickups are visual/gameplay objects only.
    # They are never passed to enemy navigation.
    draw_pickups(
        screen
    )


    # =================================================
    # PLAYING
    # =================================================

    if game_state == "PLAYING":


        # =============================================
        # PLAYER MOVEMENT
        # =============================================

        player.move(
            obstacles
        )

        # Pickups interact only with the player.
        # They do not modify obstacles or enemy navigation.
        update_pickups()

        # RL bots act independently from the normal
        # enemy wave system.
        update_rl_bots()


        # =============================================
        # CHECK PLAYER HEALTH
        # =============================================

        if player.health <= 0:

            player.health = 0

            game_state = "GAME_OVER"


        # =============================================
        # DRAW PLAYER
        # =============================================

        player.draw(
            screen
        )

        # Draw RL bots separately from normal enemies.
        draw_rl_bots()



        # =============================================
        # UPDATE THE ONE ACTIVE NORMAL ENEMY
        # =============================================

        update_active_enemy()


        # =============================================
        # ENEMIES
        # =============================================

        for enemy in enemies:

            if not enemy.alive:

                continue


            # Only the active enemy is allowed to
            # navigate and attack.
            if enemy is active_enemy:

                enemy.update_combat(
                    player,
                    obstacles
                )


                enemy.move(
                    player,
                    enemies,
                    obstacles
                )


                pending_shots = (
                    enemy.get_pending_shots()
                )


                for shot in pending_shots:

                    enemy_bullets.append(

                        Bullet(
                            shot["x"],
                            shot["y"],
                            shot["target_x"],
                            shot["target_y"],
                            damage=shot["damage"],
                            owner="enemy"
                        )
                    )

            else:

                # Keep inactive enemies completely idle.
                enemy.set_active(False)


            enemy.draw(
                screen,
                player
            )

            # Normal enemies use the RED sprite health bar.
            draw_enemy_health_bar(
                screen,
                enemy
            )


        # =============================================
        # DRAW FOREGROUND DOORS
        # =============================================

        draw_door_foreground(
            screen,
            tmx_data
        )


        # =============================================
        # PLAYER BULLETS
        # =============================================

        for bullet in bullets[:]:

            bullet.move()


            bullet_rect = pygame.Rect(
                int(bullet.x - bullet.radius),
                int(bullet.y - bullet.radius),
                bullet.radius * 2,
                bullet.radius * 2
            )


            hit_obstacle = False


            for obstacle in obstacles:

                if bullet_rect.colliderect(
                    obstacle.rect
                ):

                    hit_obstacle = True

                    break


            if hit_obstacle:

                bullets.remove(
                    bullet
                )

                continue


            if (

                bullet.x < 0
                or bullet.x > WIDTH
                or bullet.y < 0
                or bullet.y > HEIGHT

            ):

                bullets.remove(
                    bullet
                )

                continue


            bullet_hit = False


            for enemy in enemies:

                if (
                    enemy.alive
                    and enemy.check_collision(
                        bullet
                    )
                ):

                    enemy.take_damage(
                        bullet.damage
                    )


                    print(
                        f"{player.current_weapon} "
                        f"hit! Damage: "
                        f"{bullet.damage} | "
                        f"Enemy health: "
                        f"{enemy.health}"
                    )


                    if not enemy.alive:

                        score += 10


                    bullet_hit = True

                    break


            # -------------------------------------------------
            # PLAYER BULLET -> RL BOTS
            # -------------------------------------------------

            if not bullet_hit:

                for rl_bot in (
                    [rl_bot_1, rl_bot_2]
                ):

                    if (
                        rl_bot is not None
                        and rl_bot.alive
                        and bullet_rect.colliderect(
                            rl_bot.get_rect()
                        )
                    ):

                        rl_bot.take_damage(
                            bullet.damage
                        )

                        print(
                            f"Player bullet hit RL Bot "
                            f"{rl_bot.bot_number}! "
                            f"Damage: {bullet.damage} | "
                            f"Bot health: {rl_bot.health}"
                        )

                        if not rl_bot.alive:

                            print(
                                f"RL Bot "
                                f"{rl_bot.bot_number} "
                                f"eliminated."
                            )

                        bullet_hit = True
                        break


            if bullet_hit:

                bullets.remove(
                    bullet
                )


        # =============================================
        # ENEMY BULLETS
        # =============================================

        for bullet in enemy_bullets[:]:

            bullet.move()


            bullet_rect = pygame.Rect(
                int(bullet.x - bullet.radius),
                int(bullet.y - bullet.radius),
                bullet.radius * 2,
                bullet.radius * 2
            )


            hit_obstacle = False


            for obstacle in obstacles:

                if bullet_rect.colliderect(
                    obstacle.rect
                ):

                    hit_obstacle = True

                    break


            if hit_obstacle:

                enemy_bullets.remove(
                    bullet
                )

                continue


            if (

                bullet.x < 0
                or bullet.x > WIDTH
                or bullet.y < 0
                or bullet.y > HEIGHT

            ):

                enemy_bullets.remove(
                    bullet
                )

                continue


            player_rect = pygame.Rect(
                int(player.x),
                int(player.y),
                player.width,
                player.height
            )


            if player_rect.collidepoint(
                bullet.x,
                bullet.y
            ):

                player.health -= (
                    bullet.damage
                )


                print(
                    f"Enemy bullet hit! "
                    f"Damage: {bullet.damage} | "
                    f"Player health: "
                    f"{player.health}"
                )


                enemy_bullets.remove(
                    bullet
                )

                continue


        # =============================================
        # CHECK PLAYER HEALTH AGAIN
        # =============================================

        if player.health <= 0:

            player.health = 0

            game_state = "GAME_OVER"


        # =============================================
        # WAVE SYSTEM
        # =============================================

        alive_enemies = 0


        for enemy in enemies:

            if enemy.alive:

                alive_enemies += 1


        if alive_enemies == 0:


            # -----------------------------------------
            # MORE WAVES
            # -----------------------------------------

            if wave < 3:

                wave += 1


                enemy_count = (
                    WAVE_ENEMY_COUNTS[
                        wave
                    ]
                )


                enemies = []

                enemy_bullets.clear()

                active_enemy = None


                enemies = (
                    spawn_wave_enemies(
                        enemy_count
                    )
                )


                # Give the new wave the actual scaled
                # Tiled map bounds.
                for new_enemy in enemies:

                    new_enemy.set_navigation_bounds(
                        map_left,
                        map_top,
                        map_right,
                        map_bottom
                    )

                # -----------------------------------------
                # RL BOT 1 STARTS IN WAVE 2
                # -----------------------------------------

                if (
                    wave == 2
                    and
                    rl_bot_1 is None
                ):

                    rl_bot_1 = create_rl_bot(
                        rl_bot_1_spawn_point,
                        1
                    )

                    if rl_bot_1 is not None:
                        rl_env_1.set_game_state(
                            player=player,
                            bot=rl_bot_1,
                            obstacles=obstacles,
                            health_pickups=health_pickups,
                            ammo_pickups=ammo_pickups,
                            shoot_callback=create_rl_bot_bullet,
                            melee_callback=rl_bot_melee_attack
                        )
                        reset_observation, _ = rl_env_1.reset()
                        rl_bot_1.last_rl_observation = reset_observation

                # -----------------------------------------
                # WAVE 3: RL BOT 1 + RL BOT 2
                # -----------------------------------------
                #
                # Bot 1 should be present in Wave 3.
                # If Bot 1 survived Wave 2, keep the same bot.
                # If Bot 1 died during Wave 2, spawn a NEW Bot 1
                # at its original spawn point.
                #
                # Bot 2 always joins for the first time in Wave 3.
                # -----------------------------------------

                if wave == 3:

                    # -----------------------------------------
                    # ENSURE RL BOT 1 IS PRESENT IN WAVE 3
                    # -----------------------------------------

                    if (
                        rl_bot_1 is None
                        or
                        not rl_bot_1.alive
                    ):

                        rl_bot_1 = create_rl_bot(
                            rl_bot_1_spawn_point,
                            1
                        )

                        if rl_bot_1 is not None:
                            rl_env_1.set_game_state(
                                player=player,
                                bot=rl_bot_1,
                                obstacles=obstacles,
                                health_pickups=health_pickups,
                                ammo_pickups=ammo_pickups,
                                shoot_callback=create_rl_bot_bullet,
                                melee_callback=rl_bot_melee_attack
                            )
                            reset_observation, _ = rl_env_1.reset()
                            rl_bot_1.last_rl_observation = reset_observation

                    # -----------------------------------------
                    # SPAWN RL BOT 2 FOR THE FIRST TIME
                    # -----------------------------------------

                    if rl_bot_2 is None:

                        rl_bot_2 = create_rl_bot(
                            rl_bot_2_spawn_point,
                            2
                        )

                        if rl_bot_2 is not None:
                            rl_env_2.set_game_state(
                                player=player,
                                bot=rl_bot_2,
                                obstacles=obstacles,
                                health_pickups=health_pickups,
                                ammo_pickups=ammo_pickups,
                                shoot_callback=create_rl_bot_bullet,
                                melee_callback=rl_bot_melee_attack
                            )
                            reset_observation, _ = rl_env_2.reset()
                            rl_bot_2.last_rl_observation = reset_observation


            # -----------------------------------------
            # FINAL WAVE COMPLETE
            # -----------------------------------------

            else:

                game_state = (
                    "LEVEL_COMPLETE"
                )


        # =============================================
        # DRAW PLAYER BULLETS
        # =============================================

        for bullet in bullets:

            bullet.draw(
                screen
            )


        # =============================================
        # DRAW ENEMY BULLETS
        # =============================================

        for bullet in enemy_bullets:

            bullet.draw(
                screen
            )


    # =================================================
    # FINAL HUD OVERLAY
    # =================================================
    # IMPORTANT:
    # The HUD is drawn LAST so map tiles, foreground doors,
    # enemies, and bullets can never cover it.

    if game_state == "PLAYING":

        # Solid/semi-opaque HUD panel for readability.
        hud_bg = pygame.Surface((270, 165), pygame.SRCALPHA)
        hud_bg.fill((0, 0, 0, 210))
        screen.blit(
            hud_bg,
            (10, 10)
        )

        # PLAYER HEALTH BAR
        # Player uses the GREEN sprite health bar.
        player_bar_drawn = draw_sprite_health_bar(
            screen,
            "green",
            player.health,
            30,
            120,
            18,
            220,
            24
        )

        # Safe fallback if the supplied sprite sheet is not present.
        if not player_bar_drawn:
            pygame.draw.rect(
                screen,
                (80, 80, 80),
                (20, 20, 200, 20)
            )

            health_width = max(
                0,
                min(
                    200,
                    (player.health / 30.0) * 200
                )
            )

            pygame.draw.rect(
                screen,
                (0, 255, 0),
                (
                    20,
                    20,
                    int(health_width),
                    20
                )
            )

        # WAVE
        wave_text = font.render(
            f"Wave: {wave}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            wave_text,
            (20, 52)
        )

        # AMMO
        if player.current_weapon != "knife":

            ammo_text = font.render(
                f"Ammo: {player.ammo} / {player.max_ammo}",
                True,
                (255, 255, 255)
            )

            screen.blit(
                ammo_text,
                (20, 94)
            )

        # WEAPON
        weapon_text = font.render(
            f"Weapon: {player.current_weapon.upper()}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            weapon_text,
            (20, 130)
        )


    # =================================================
    # DEATH / VICTORY SCREENS
    # =================================================

    elif game_state == "GAME_OVER":
        draw_death_screen(screen)

    elif game_state == "LEVEL_COMPLETE":
        draw_victory_screen(screen)


    # =================================================
    # UPDATE DISPLAY
    # =================================================
    
    # =================================================
    # DUNGEON OPS GUI MENUS
    # =================================================

    if game_state == "MENU":
        draw_main_menu(screen)

    elif game_state == "PAUSED":
        draw_pause_menu(screen)


    pygame.display.flip()


    # =================================================
    # FPS
    # =================================================

    clock.tick(
        60
    )


# =====================================================
# QUIT
# =====================================================

pygame.quit()