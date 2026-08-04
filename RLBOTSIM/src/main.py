import pygame
import time
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
player=Player()
bullets = []
enemy = Enemy()
enemy_resptime = None

running = True

while running:

    # Check events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:

                mouse_x, mouse_y = pygame.mouse.get_pos()

                bullet = Bullet(
                  player.x + player.width // 2,
                  player.y + player.height // 2,
                  mouse_x,
                  mouse_y
           )

                bullets.append(bullet)

    # Background color (dark gray)
    screen.fill((40, 40, 40))
    player.move()
    enemy.move(player)
    if not enemy.alive and enemy_resptime is not None:
        if time.time() - enemy_resptime >= 2:
           enemy = Enemy()
           enemy_resptime = None 
    for bullet in bullets[:]:
       bullet.move()
       
       if (
        bullet.x < 0 or
        bullet.x > WIDTH or
        bullet.y < 0 or
        bullet.y > HEIGHT
          ):
            bullets.remove(bullet)
            continue
       if enemy.check_collision(bullet):
            bullets.remove(bullet)
            enemy.alive = False
            enemy_resptime = time.time()
    player.draw(screen)
    for bullet in bullets:
       bullet.draw(screen)
    player.aim(screen)
    enemy.draw(screen)

    # Update display
    pygame.display.flip()

    # FPS
    clock.tick(60)

pygame.quit()