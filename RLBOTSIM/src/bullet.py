import pygame
import math

class Bullet:

    def __init__(self, x, y, target_x, target_y):

        self.x = x
        self.y = y

        self.radius = 5
        self.speed = 10
        self.color = (255, 255, 0)

        dx = target_x - x
        dy = target_y - y

        distance = math.sqrt(dx**2 + dy**2)

        self.dx = dx / distance
        self.dy = dy / distance

    def move(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

    def draw(self, screen):
        pygame.draw.circle(
            screen,
            self.color,
            (int(self.x), int(self.y)),
            self.radius
        )
    