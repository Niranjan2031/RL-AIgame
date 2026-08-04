import pygame
import math

class Enemy:

    def __init__(self):

        self.x = 700
        self.y = 300

        self.width = 40
        self.height = 40

        self.color = (255, 0, 0)
        self.speed = 2
        self.alive = True

    def draw(self, screen):

        if self.alive:

            pygame.draw.rect(
            screen,
            self.color,
            (self.x, self.y, self.width, self.height)
          )
    def move(self, player):
       if not self.alive:
            return
       dx = player.x - self.x
       dy = player.y - self.y

       distance = math.sqrt(dx**2 + dy**2)

       if distance != 0:
          self.x += (dx / distance) * self.speed
          self.y += (dy / distance) * self.speed
    def check_collision(self, bullet):

       if (
          bullet.x > self.x and
          bullet.x < self.x + self.width and
          bullet.y > self.y and
          bullet.y < self.y + self.height
          ):
        return True

       return False