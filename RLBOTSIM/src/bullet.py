import pygame
import math


class Bullet:

    def __init__(
        self,
        x,
        y,
        target_x,
        target_y,
        damage=10,
        owner="player"
    ):

        self.x = x
        self.y = y

        self.radius = 5
        self.speed = 10

        self.damage = damage
        self.owner = owner

        # Different colour depending on who fired
        if self.owner == "enemy":
            self.color = (255, 60, 60)
        else:
            self.color = (255, 255, 0)

        dx = target_x - x
        dy = target_y - y

        distance = math.sqrt(
            dx ** 2 + dy ** 2
        )

        # Prevent division by zero
        if distance == 0:
            self.dx = 0
            self.dy = 0
        else:
            self.dx = dx / distance
            self.dy = dy / distance


    def move(self):

        self.x += self.dx * self.speed
        self.y += self.dy * self.speed


    def draw(self, screen):

        pygame.draw.circle(
            screen,
            self.color,
            (
                int(self.x),
                int(self.y)
            ),
            self.radius
        )