import pygame
import os
import math

from player import Player
from bullet import Bullet
from enemy import Enemy


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
# BACKGROUND
# =====================================================

current_dir = os.path.dirname(__file__)

background_path = os.path.join(
    current_dir,
    "..",
    "assets",
    "background",
    "backgr1.png"
)

background = pygame.image.load(
    background_path
).convert()

background = pygame.transform.scale(
    background,
    (WIDTH, HEIGHT)
)


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

bullets = []


# =====================================================
# SCORE
# =====================================================

score = 0


# =====================================================
# GAME STATE
# =====================================================

game_state = "PLAYING"


# =====================================================
# WAVE SYSTEM
# =====================================================

wave = 1

enemy_count = 5

enemies = []

for i in range(enemy_count):

    enemies.append(
        Enemy()
    )


# =====================================================
# MELEE SETTINGS
# =====================================================

# Maximum distance for melee attack
MELEE_RANGE = 100


# Attack cone in degrees
#
# 90 degrees means:
# 45 degrees left
# 45 degrees right
#
MELEE_ANGLE = 90


# Melee cooldown
#
# 500 milliseconds = 0.5 seconds
#
MELEE_COOLDOWN = 500


# Time when last melee attack happened
last_melee_time = 0


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
            # ESC → EXIT
            # -----------------------------------------

            if event.key == pygame.K_ESCAPE:

                running = False


            # =========================================
            # WEAPON SWITCHING
            # =========================================

            # 1 → HANDGUN
            if (
                event.key == pygame.K_1
                and game_state == "PLAYING"
            ):

                player.set_weapon(
                    "handgun"
                )


            # 2 → SHOTGUN
            elif (
                event.key == pygame.K_2
                and game_state == "PLAYING"
            ):

                player.set_weapon(
                    "shotgun"
                )


            # 3 → RIFLE
            elif (
                event.key == pygame.K_3
                and game_state == "PLAYING"
            ):

                player.set_weapon(
                    "rifle"
                )


            # 4 → KNIFE
            elif (
                event.key == pygame.K_4
                and game_state == "PLAYING"
            ):

                player.set_weapon(
                    "knife"
                )


            # =========================================
            # R → RELOAD
            # =========================================

            if (
                event.key == pygame.K_r
                and game_state == "PLAYING"
            ):

                player.reload()


            # =========================================
            # SPACE → MELEE ATTACK
            # =========================================

            if (
                event.key == pygame.K_SPACE
                and game_state == "PLAYING"
            ):

                # -------------------------------------
                # CURRENT TIME
                # -------------------------------------

                current_time = (
                    pygame.time.get_ticks()
                )


                # -------------------------------------
                # CHECK COOLDOWN
                # -------------------------------------

                if (
                    current_time -
                    last_melee_time
                    >= MELEE_COOLDOWN
                ):

                    # ---------------------------------
                    # START MELEE ANIMATION
                    # ---------------------------------

                    melee_started = (
                        player.melee_attack()
                    )


                    # Only attack if animation
                    # successfully started
                    if melee_started:

                        # -----------------------------
                        # UPDATE COOLDOWN
                        # -----------------------------

                        last_melee_time = (
                            current_time
                        )


                        # -----------------------------
                        # PLAYER CENTER
                        # -----------------------------

                        player_center_x = (
                            player.x +
                            player.width // 2
                        )

                        player_center_y = (
                            player.y +
                            player.height // 2
                        )


                        # -----------------------------
                        # MOUSE POSITION
                        # -----------------------------

                        mouse_x, mouse_y = (
                            pygame.mouse.get_pos()
                        )


                        # -----------------------------
                        # DIRECTION TO MOUSE
                        # -----------------------------

                        direction_x = (
                            mouse_x -
                            player_center_x
                        )

                        direction_y = (
                            mouse_y -
                            player_center_y
                        )


                        # -----------------------------
                        # PLAYER AIM ANGLE
                        # -----------------------------

                        player_angle = (
                            math.degrees(
                                math.atan2(
                                    direction_y,
                                    direction_x
                                )
                            )
                        )


                        # -----------------------------
                        # GET CURRENT WEAPON
                        # -----------------------------

                        melee_damage = (
                            player.get_melee_damage()
                        )


                        # -----------------------------
                        # CHECK ALL ENEMIES
                        # -----------------------------

                        for enemy in enemies:

                            # Ignore dead enemies
                            if not enemy.alive:

                                continue


                            # -------------------------
                            # ENEMY CENTER
                            # -------------------------

                            enemy_center_x = (
                                enemy.x +
                                enemy.width // 2
                            )

                            enemy_center_y = (
                                enemy.y +
                                enemy.height // 2
                            )


                            # -------------------------
                            # DISTANCE
                            # -------------------------

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


                            # -------------------------
                            # RANGE CHECK
                            # -------------------------

                            if (
                                distance >
                                MELEE_RANGE
                            ):

                                continue


                            # -------------------------
                            # ANGLE TO ENEMY
                            # -------------------------

                            enemy_angle = (
                                math.degrees(
                                    math.atan2(
                                        dy,
                                        dx
                                    )
                                )
                            )


                            # -------------------------
                            # ANGLE DIFFERENCE
                            # -------------------------

                            angle_difference = (
                                enemy_angle -
                                player_angle
                            )


                            # Keep angle between
                            # -180 and +180

                            angle_difference = (
                                angle_difference +
                                180
                            ) % 360 - 180


                            # -------------------------
                            # ATTACK DIRECTION CHECK
                            # -------------------------

                            if (
                                abs(
                                    angle_difference
                                )
                                <=
                                MELEE_ANGLE / 2
                            ):

                                # Enemy is:
                                #
                                # 1. Alive
                                # 2. In range
                                # 3. In front of player
                                #
                                # Therefore hit it.

                                enemy.health -= (
                                    melee_damage
                                )


                                print(
                                    f"{player.current_weapon} "
                                    f"melee hit! "
                                    f"Damage: "
                                    f"{melee_damage} | "
                                    f"Enemy health: "
                                    f"{enemy.health}"
                                )


                                # ---------------------
                                # ENEMY KILLED
                                # ---------------------

                                if (
                                    enemy.health <= 0
                                ):

                                    enemy.alive = False

                                    score += 10


        # =============================================
        # LEFT MOUSE BUTTON → SHOOT
        # =============================================

        if (
            game_state == "PLAYING"
            and event.type ==
            pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):

            # -----------------------------------------
            # MOUSE POSITION
            # -----------------------------------------

            mouse_x, mouse_y = (
                pygame.mouse.get_pos()
            )


            # -----------------------------------------
            # TRY TO SHOOT
            # -----------------------------------------

            shoot_started = (
                player.shoot()
            )


            # -----------------------------------------
            # CREATE BULLET
            # -----------------------------------------

            if shoot_started:

                bullets.append(
                    Bullet(
                        player.x +
                        player.width // 2,

                        player.y +
                        player.height // 2,

                        mouse_x,
                        mouse_y
                    )
                )


    # =================================================
    # BACKGROUND
    # =================================================

    screen.blit(
        background,
        (0, 0)
    )


    # =================================================
    # PLAYING
    # =================================================

    if game_state == "PLAYING":

        # ---------------------------------------------
        # PLAYER HEALTH BAR BACKGROUND
        # ---------------------------------------------

        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (
                20,
                20,
                200,
                20
            )
        )


        # ---------------------------------------------
        # PLAYER HEALTH BAR
        # ---------------------------------------------

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


        # ---------------------------------------------
        # WAVE TEXT
        # ---------------------------------------------

        wave_text = font.render(
            f"Wave: {wave}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            wave_text,
            (20, 50)
        )


        # ---------------------------------------------
        # SCORE TEXT
        # ---------------------------------------------

        score_text = font.render(
            f"Score: {score}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            score_text,
            (20, 80)
        )


        # ---------------------------------------------
        # AMMO
        # ---------------------------------------------

        # Knife has no ammo system

        if (
            player.current_weapon !=
            "knife"
        ):

            ammo_text = font.render(
                f"Ammo: {player.ammo} / "
                f"{player.max_ammo}",
                True,
                (255, 255, 255)
            )

            screen.blit(
                ammo_text,
                (20, 110)
            )


        # ---------------------------------------------
        # CURRENT WEAPON
        # ---------------------------------------------

        weapon_text = font.render(
            f"Weapon: "
            f"{player.current_weapon.upper()}",
            True,
            (255, 255, 255)
        )

        screen.blit(
            weapon_text,
            (20, 145)
        )


        # =================================================
        # PLAYER
        # =================================================

        player.move()


        # ---------------------------------------------
        # CHECK PLAYER HEALTH
        # ---------------------------------------------

        if player.health <= 0:

            game_state = "GAME_OVER"


        # ---------------------------------------------
        # DRAW PLAYER
        # ---------------------------------------------

        player.draw(
            screen
        )


        # ---------------------------------------------
        # AIM LINE
        # ---------------------------------------------

        player.aim(
            screen
        )


        # =================================================
        # ENEMIES
        # =================================================

        for enemy in enemies:

            # -----------------------------------------
            # ENEMY MOVEMENT
            # -----------------------------------------

            enemy.move(
                player,
                enemies
            )


            # -----------------------------------------
            # ENEMY ATTACK
            # -----------------------------------------

            if enemy.check_player_collision(
                player
            ):

                enemy.attack(
                    player
                )


            # -----------------------------------------
            # DRAW ENEMY
            # -----------------------------------------

            enemy.draw(
                screen
            )


        # =================================================
        # BULLETS
        # =================================================

        for bullet in bullets[:]:

            # -----------------------------------------
            # MOVE BULLET
            # -----------------------------------------

            bullet.move()


            # -----------------------------------------
            # BULLET OUTSIDE SCREEN
            # -----------------------------------------

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


            # -----------------------------------------
            # GET CURRENT WEAPON DAMAGE
            # -----------------------------------------

            bullet_damage = (
                player.get_damage()
            )


            # -----------------------------------------
            # BULLET COLLISION
            # -----------------------------------------

            for enemy in enemies:

                if (
                    enemy.alive
                    and enemy.check_collision(
                        bullet
                    )
                ):

                    # ---------------------------------
                    # APPLY WEAPON-SPECIFIC DAMAGE
                    # ---------------------------------

                    enemy.health -= (
                        bullet_damage
                    )


                    print(
                        f"{player.current_weapon} "
                        f"hit! Damage: "
                        f"{bullet_damage} | "
                        f"Enemy health: "
                        f"{enemy.health}"
                    )


                    # ---------------------------------
                    # ENEMY KILLED
                    # ---------------------------------

                    if (
                        enemy.health <= 0
                    ):

                        enemy.alive = False

                        score += 10


                    bullet_hit = True

                    break


            # -----------------------------------------
            # REMOVE BULLET AFTER HIT
            # -----------------------------------------

            if bullet_hit:

                bullets.remove(
                    bullet
                )


        # =================================================
        # WAVE SYSTEM
        # =================================================

        alive_enemies = 0


        # ---------------------------------------------
        # COUNT LIVING ENEMIES
        # ---------------------------------------------

        for enemy in enemies:

            if enemy.alive:

                alive_enemies += 1


        # ---------------------------------------------
        # ALL ENEMIES DEFEATED
        # ---------------------------------------------

        if alive_enemies == 0:

            # -----------------------------------------
            # MORE WAVES
            # -----------------------------------------

            if wave < 3:

                wave += 1

                enemy_count += 3

                enemies = []


                # Spawn new enemies

                for i in range(
                    enemy_count
                ):

                    enemies.append(
                        Enemy()
                    )


            # -----------------------------------------
            # FINAL WAVE COMPLETE
            # -----------------------------------------

            else:

                game_state = (
                    "LEVEL_COMPLETE"
                )


        # =================================================
        # DRAW BULLETS
        # =================================================

        for bullet in bullets:

            bullet.draw(
                screen
            )


    # =====================================================
    # GAME OVER
    # =====================================================

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


    # =====================================================
    # LEVEL COMPLETE
    # =====================================================

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


    # =====================================================
    # UPDATE SCREEN
    # =====================================================

    pygame.display.flip()


    # =====================================================
    # FPS
    # =====================================================

    clock.tick(60)


# =====================================================
# QUIT PYGAME
# =====================================================

pygame.quit()