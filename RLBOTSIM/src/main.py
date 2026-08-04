import pygame
from player import Player
from bullet import Bullet
from enemy import Enemy

# Initialize PyGame
pygame.init()

# Screen settings
WIDTH = 1000
HEIGHT = 700

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RL SURVIVAL")

clock = pygame.time.Clock()

# Font
font = pygame.font.SysFont(None, 36)

player = Player()
bullets = []

# ---------------- Wave System ----------------

wave = 1
enemy_count = 5

enemies = []

for i in range(enemy_count):
    enemies.append(Enemy())

running = True

while running:

    # ---------------- Events ----------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                mouse_x, mouse_y = pygame.mouse.get_pos()

                bullets.append(
                    Bullet(
                        player.x + player.width // 2,
                        player.y + player.height // 2,
                        mouse_x,
                        mouse_y
                    )
                )

    # ---------------- Background ----------------

    screen.fill((40, 40, 40))

    # ---------------- Player Health Bar ----------------

    pygame.draw.rect(
        screen,
        (100, 100, 100),
        (20, 20, 200, 20)
    )

    pygame.draw.rect(
        screen,
        (0, 255, 0),
        (20, 20, (player.health / 10) * 200, 20)
    )

    # ---------------- Wave Text ----------------

    wave_text = font.render(f"Wave: {wave}", True, (255, 255, 255))
    screen.blit(wave_text, (20, 50))

    # ---------------- Player ----------------

    player.move()

    if player.health <= 0:
        running = False

    player.draw(screen)
    player.aim(screen)

    # ---------------- Enemies ----------------

    for enemy in enemies:

        enemy.move(player, enemies)

        if enemy.check_player_collision(player):
            enemy.attack(player)

        enemy.draw(screen)

    # ---------------- Bullets ----------------

    for bullet in bullets[:]:

        bullet.move()

        # Remove bullets outside screen
        if (
            bullet.x < 0 or
            bullet.x > WIDTH or
            bullet.y < 0 or
            bullet.y > HEIGHT
        ):
            bullets.remove(bullet)
            continue

        bullet_hit = False

        for enemy in enemies:

            if enemy.alive and enemy.check_collision(bullet):

                enemy.health -= 1

                if enemy.health <= 0:
                    enemy.alive = False

                bullet_hit = True
                break

        if bullet_hit:
            bullets.remove(bullet)

    # ---------------- Wave System ----------------

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
            running = False

    # ---------------- Draw Bullets ----------------

    for bullet in bullets:
        bullet.draw(screen)

    # ---------------- Update Screen ----------------

    pygame.display.flip()

    # ---------------- FPS ----------------

    clock.tick(60)

pygame.quit()