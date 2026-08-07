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

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RL SURVIVAL")


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

font = pygame.font.SysFont(None, 36)
big_font = pygame.font.SysFont(None, 72)


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

    enemies.append(Enemy())


# =====================================================
# MELEE SETTINGS
# =====================================================

MELEE_RANGE = 100
MELEE_DAMAGE = 1


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


            # -----------------------------------------
            # R → RELOAD
            # -----------------------------------------

            if (
                event.key == pygame.K_r
                and game_state == "PLAYING"
            ):

                player.reload()


            # -----------------------------------------
            # SPACE → MELEE
            # -----------------------------------------

            if (
                event.key == pygame.K_SPACE
                and game_state == "PLAYING"
            ):

                # Start melee animation
                melee_started = player.melee_attack()

                # Only deal damage if melee actually started
                if melee_started:

                    player_center_x = (
                        player.x +
                        player.width // 2
                    )

                    player_center_y = (
                        player.y +
                        player.height // 2
                    )

                    # Check every enemy
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

                        distance = math.sqrt(
                            (
                                enemy_center_x -
                                player_center_x
                            ) ** 2
                            +
                            (
                                enemy_center_y -
                                player_center_y
                            ) ** 2
                        )

                        # Enemy is within melee range
                        if distance <= MELEE_RANGE:

                            enemy.health -= MELEE_DAMAGE

                            print("Melee hit!")

                            # Enemy killed
                            if enemy.health <= 0:

                                enemy.alive = False

                                score += 10


        # ---------------------------------------------
        # LEFT MOUSE BUTTON → SHOOT
        # ---------------------------------------------

        if (
            game_state == "PLAYING"
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):

            mouse_x, mouse_y = pygame.mouse.get_pos()

            # Play shooting animation
            shoot_started = player.shoot()

            # Only create bullet if shooting was allowed
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
        # HEALTH BAR BACKGROUND
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
        # HEALTH BAR
        # ---------------------------------------------

        pygame.draw.rect(
            screen,
            (0, 255, 0),
            (
                20,
                20,
                (player.health / 30) * 200,
                20
            )
        )


        # ---------------------------------------------
        # WAVE
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
        # SCORE
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


        # =================================================
        # PLAYER
        # =================================================

        player.move()

        if player.health <= 0:

            game_state = "GAME_OVER"


        player.draw(screen)

        player.aim(screen)


        # =================================================
        # ENEMIES
        # =================================================

        for enemy in enemies:

            enemy.move(
                player,
                enemies
            )

            if enemy.check_player_collision(player):

                enemy.attack(player)

            enemy.draw(screen)


        # =================================================
        # BULLETS
        # =================================================

        for bullet in bullets[:]:

            bullet.move()


            # ---------------------------------------------
            # BULLET OUTSIDE SCREEN
            # ---------------------------------------------

            if (
                bullet.x < 0
                or bullet.x > WIDTH
                or bullet.y < 0
                or bullet.y > HEIGHT
            ):

                bullets.remove(bullet)

                continue


            bullet_hit = False


            # ---------------------------------------------
            # BULLET COLLISION
            # ---------------------------------------------

            for enemy in enemies:

                if (
                    enemy.alive
                    and enemy.check_collision(bullet)
                ):

                    enemy.health -= 1


                    if enemy.health <= 0:

                        enemy.alive = False

                        score += 10


                    bullet_hit = True

                    break


            if bullet_hit:

                bullets.remove(bullet)


        # =================================================
        # WAVE SYSTEM
        # =================================================

        alive_enemies = 0

        for enemy in enemies:

            if enemy.alive:

                alive_enemies += 1


        if alive_enemies == 0:

            if wave < 3:

                wave += 1

                enemy_count += 3

                enemies = []

                for i in range(enemy_count):

                    enemies.append(Enemy())

            else:

                game_state = "LEVEL_COMPLETE"


        # =================================================
        # DRAW BULLETS
        # =================================================

        for bullet in bullets:

            bullet.draw(screen)


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