import pygame
import math
import random
import time
import os



class Enemy:

    def __init__(self):

        # Spawn at a random position
        self.x = random.randint(50, 950)
        self.y = random.randint(50, 650)

        self.width = 40
        self.height = 40

        self.rect = pygame.Rect(
        self.x,
        self.y,
        self.width,
        self.height
        )

        self.speed = 2

        self.alive = True
        self.health = 3

        # ---------------- Load Enemy Sprite ----------------

        current_dir = os.path.dirname(__file__)

        enemy_path = os.path.join(
            current_dir,
            "..",
            "assets",
            "enemy",
            "enemy.png"
        )

        self.image = pygame.image.load(enemy_path).convert_alpha()

        self.image = pygame.transform.scale(
            self.image,
            (self.width, self.height)
        )

        # ---------------- Attack ----------------

        self.attack_damage = 1
        self.attack_cooldown = 1.0
        self.last_attack_time = 0

    def draw(self, screen):

        if not self.alive:
            return

        # Draw enemy sprite
        screen.blit(
            self.image,
            (self.x, self.y)
        )

        # Health bar background
        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (self.x, self.y - 12, self.width, 6)
        )

        # Current health
        pygame.draw.rect(
            screen,
            (0, 255, 0),
            (
                self.x,
                self.y - 12,
                (self.health / 3) * self.width,
                6
            )
        )

    def move(self, player, enemies, obstacles=None):

        if not self.alive:
            return

        dx = player.x - self.x
        dy = player.y - self.y

        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:
            return

        move_x = (dx / distance) * self.speed
        move_y = (dy / distance) * self.speed

        # Current position
        self.rect.topleft = (
            int(self.x),
            int(self.y)
        )

        # ==========================================
        # HORIZONTAL MOVEMENT
        # ==========================================

        new_rect = self.rect.copy()
        new_rect.x += int(move_x)

        collision = False

        # Check obstacles
        if obstacles:

            for obstacle in obstacles:

                if new_rect.colliderect(
                    obstacle.rect
                ):
                    collision = True
                    break

        # Check other enemies
        if not collision:

            for other in enemies:

                if other is self:
                    continue

                if not other.alive:
                    continue

                if new_rect.colliderect(
                    pygame.Rect(
                        other.x,
                        other.y,
                        other.width,
                        other.height
                    )
                ):
                    collision = True
                    break

        if not collision:
            self.x += move_x

        # ==========================================
        # VERTICAL MOVEMENT
        # ==========================================

        self.rect.topleft = (
            int(self.x),
            int(self.y)
        )

        new_rect = self.rect.copy()
        new_rect.y += int(move_y)

        collision = False

        # Check obstacles
        if obstacles:

            for obstacle in obstacles:

                if new_rect.colliderect(
                    obstacle.rect
                ):
                    collision = True
                    break

        # Check other enemies
        if not collision:

            for other in enemies:

                if other is self:
                    continue

                if not other.alive:
                    continue

                if new_rect.colliderect(
                    pygame.Rect(
                        other.x,
                        other.y,
                        other.width,
                        other.height
                    )
                ):
                    collision = True
                    break

        if not collision:
            self.y += move_y

        # Update rectangle
        self.rect.topleft = (
            int(self.x),
            int(self.y)
        )

    def check_collision(self, bullet):

        if not self.alive:
            return False

        return (
            bullet.x > self.x and
            bullet.x < self.x + self.width and
            bullet.y > self.y and
            bullet.y < self.y + self.height
        )

    def check_player_collision(self, player):

        if not self.alive:
            return False

        return (
            self.x < player.x + player.width and
            self.x + self.width > player.x and
            self.y < player.y + player.height and
            self.y + self.height > player.y
        )

    def attack(self, player):

        if not self.alive:
            return

        current_time = time.time()

        if current_time - self.last_attack_time >= self.attack_cooldown:

            player.health -= self.attack_damage
            self.last_attack_time = current_time