import pygame
import os
import math
import random
import pytmx

from player import Player
from bullet import Bullet
from enemy import Enemy
from obstacle import Obstacle


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
    "RL SURVIVAL"
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
# FONTS
# =====================================================

font = pygame.font.SysFont(
    None,
    36
)

big_font = pygame.font.SysFont(
    None,
    72
)


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

game_state = "PLAYING"


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

def load_rl_bot_spawn():

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

        return None


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


        print(
            "RL bot spawn point loaded:",
            spawn_x,
            spawn_y
        )


        return (
            spawn_x,
            spawn_y
        )


    return None


# =====================================================
# LOAD SPAWN POINTS
# =====================================================

enemy_spawn_points = (
    load_enemy_spawn_points()
)

rl_bot_spawn_point = (
    load_rl_bot_spawn()
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
# DRAW TILED MAP
# =====================================================

def draw_tiled_map(
    screen,
    tmx_data
):

    tile_scale = TILE_SCALE


    # -------------------------------------------------
    # ORIGINAL MAP SIZE
    # -------------------------------------------------

    map_width = (
        tmx_data.width *
        tmx_data.tilewidth
    )

    map_height = (
        tmx_data.height *
        tmx_data.tileheight
    )


    # -------------------------------------------------
    # CREATE MAP SURFACE
    # -------------------------------------------------

    map_surface = pygame.Surface(
        (
            map_width,
            map_height
        ),
        pygame.SRCALPHA
    )


    # -------------------------------------------------
    # DRAW ALL TILED LAYERS
    # -------------------------------------------------

    for layer in tmx_data.visible_layers:

        if hasattr(
            layer,
            "tiles"
        ):

            for x, y, image in layer.tiles():

                map_surface.blit(
                    image,
                    (
                        x *
                        tmx_data.tilewidth,

                        y *
                        tmx_data.tileheight
                    )
                )


    # -------------------------------------------------
    # SCALE MAP
    # -------------------------------------------------

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


    # -------------------------------------------------
    # CENTER MAP
    # -------------------------------------------------

    screen_width, screen_height = (
        screen.get_size()
    )


    offset_x = (
        screen_width -
        enlarged_width
    ) // 2


    offset_y = (
        screen_height -
        enlarged_height
    ) // 2


    # -------------------------------------------------
    # DRAW MAP
    # -------------------------------------------------

    screen.blit(
        map_surface,
        (
            offset_x,
            offset_y - 30
        )
    )


# =====================================================
# DRAW FOREGROUND DOORS
# =====================================================

def draw_door_foreground(
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
        screen_height -
        enlarged_height
    ) // 2


    walls_layer = (
        tmx_data.get_layer_by_name(
            "Walls"
        )
    )


    # =================================================
    # DOOR AREAS
    # =================================================

    door_areas = [

        pygame.Rect(
            55,
            30,
            30,
            80
        ),

        pygame.Rect(
            433,
            60,
            30,
            80
        ),

        pygame.Rect(
            643,
            0,
            30,
            80
        ),

        pygame.Rect(
            903,
            35,
            30,
            80
        ),

        pygame.Rect(
            65,
            270,
            30,
            80
        ),

        pygame.Rect(
            197,
            380,
            30,
            80
        ),

        pygame.Rect(
            433,
            270,
            30,
            80
        ),

        pygame.Rect(
            642,
            350,
            30,
            80
        ),

        pygame.Rect(
            540,
            450,
            30,
            80
        ),

        pygame.Rect(
            408,
            530,
            30,
            80
        ),

        pygame.Rect(
            223,
            530,
            30,
            80
        ),

        pygame.Rect(
            903,
            480,
            30,
            80
        ),

        pygame.Rect(
            903,
            600,
            30,
            80
        )
    ]


    # =================================================
    # DRAW DOOR TILES AGAIN IN FOREGROUND
    # =================================================

    for x, y, image in walls_layer.tiles():

        wall_x = int(
            offset_x +
            x *
            tmx_data.tilewidth *
            tile_scale
        )

        wall_y = int(
            offset_y -
            30 +
            y *
            tmx_data.tileheight *
            tile_scale
        )


        wall_width = int(
            image.get_width() *
            tile_scale
        )

        wall_height = int(
            image.get_height() *
            tile_scale
        )


        wall_rect = pygame.Rect(
            wall_x,
            wall_y,
            wall_width,
            wall_height
        )


        is_door = False


        for door_area in door_areas:

            if door_area.colliderect(
                wall_rect
            ):

                is_door = True

                break


        if is_door:

            scaled_image = (
                pygame.transform.scale(
                    image,
                    (
                        wall_width,
                        wall_height
                    )
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


# =====================================================
# SET ACTUAL MAP BOUNDS FOR ALL ENEMIES
# =====================================================

map_left, map_top, map_right, map_bottom = (
    get_map_bounds()
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

                running = False


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
                                    player.get_damage()
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
        # PLAYER HEALTH BAR
        # =============================================

        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (20, 20, 200, 20)
        )

        health_width = (
            player.health / 30
        ) * 200

        health_width = max(
            0,
            health_width
        )

        pygame.draw.rect(
            screen,
            (0, 255, 0),
            (
                20,
                20,
                health_width,
                20
            )
        )


        # =============================================
        # WAVE
        # =============================================

        wave_text = font.render(
            f"Wave: {wave}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            wave_text,
            (20, 50)
        )


        # =============================================
        # SCORE
        # =============================================

        score_text = font.render(
            f"Score: {score}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            score_text,
            (20, 80)
        )


        # =============================================
        # AMMO
        # =============================================

        if player.current_weapon != "knife":

            ammo_text = font.render(
                f"Ammo: {player.ammo} / {player.max_ammo}",
                True,
                (255, 255, 255)
            )

            screen.blit(
                ammo_text,
                (20, 110)
            )


        # =============================================
        # WEAPON TEXT
        # =============================================

        weapon_text = font.render(
            f"Weapon: {player.current_weapon.upper()}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            weapon_text,
            (20, 145)
        )


        # =============================================
        # PLAYER MOVEMENT
        # =============================================

        player.move(
            obstacles
        )

        # Pickups interact only with the player.
        # They do not modify obstacles or enemy navigation.
        update_pickups()


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
    # GAME OVER
    # =================================================

    elif game_state == "GAME_OVER":

        title = big_font.render(
            "GAME OVER",
            True,
            (255, 0, 0)
        )

        score_text = font.render(
            f"Final Score: {score}",
            True,
            (255, 255, 255)
        )

        exit_text = font.render(
            "Press ESC to Exit",
            True,
            (255, 255, 255)
        )

        screen.blit(
            title,
            (300, 220)
        )

        screen.blit(
            score_text,
            (370, 320)
        )

        screen.blit(
            exit_text,
            (340, 380)
        )


    # =================================================
    # LEVEL COMPLETE
    # =================================================

    elif game_state == "LEVEL_COMPLETE":

        title = big_font.render(
            "LEVEL COMPLETE",
            True,
            (0, 255, 0)
        )

        score_text = font.render(
            f"Final Score: {score}",
            True,
            (255, 255, 255)
        )

        exit_text = font.render(
            "Press ESC to Exit",
            True,
            (255, 255, 255)
        )

        screen.blit(
            title,
            (220, 220)
        )

        screen.blit(
            score_text,
            (370, 320)
        )

        screen.blit(
            exit_text,
            (340, 380)
        )


    # =================================================
    # UPDATE DISPLAY
    # =================================================

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