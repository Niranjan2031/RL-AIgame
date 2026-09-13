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
# SPAWN ENEMIES
# =====================================================

def spawn_wave_enemies(
    enemy_amount
):

    new_enemies = []


    # -------------------------------------------------
    # If there are no Tiled spawn points,
    # use the Enemy fallback random spawn.
    # -------------------------------------------------

    if len(enemy_spawn_points) == 0:

        print(
            "No enemy spawn points found."
        )

        for i in range(
            enemy_amount
        ):

            new_enemies.append(
                Enemy()
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

        # If more enemies than spawn points,
        # reuse spawn points.

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
    # CREATE ENEMIES
    # -------------------------------------------------

    for spawn_x, spawn_y in (
        selected_spawns
    ):

        enemy = Enemy(
            spawn_x,
            spawn_y
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


# Spawn Wave 1

enemies = (
    spawn_wave_enemies(
        enemy_count
    )
)


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

        player.aim(
            screen
        )


        # =============================================
        # ENEMIES
        # =============================================

        for enemy in enemies:

            if not enemy.alive:

                continue


            enemy.update_combat(
                player,obstacles
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


                enemies = (
                    spawn_wave_enemies(
                        enemy_count
                    )
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