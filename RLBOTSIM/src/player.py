import pygame
import math

class Player:

    def __init__(self):
        self.x = 100
        self.y = 100

        self.width = 50
        self.height = 50

        self.speed = 5

        self.color = (0, 255, 0)   # Green

    def draw(self, screen):
        pygame.draw.rect(
            screen,
            self.color,
            (self.x, self.y, self.width, self.height)
        )
    def move(self):
         keys = pygame.key.get_pressed()

         if keys[pygame.K_w]:
          self.y -= self.speed

         if keys[pygame.K_s]:
          self.y += self.speed

         if keys[pygame.K_a]:
          self.x -= self.speed

         if keys[pygame.K_d]:
          self.x += self.speed    
    def aim(self, screen):

         mouse_x, mouse_y = pygame.mouse.get_pos()

         player_center_x = self.x + self.width // 2
         player_center_y = self.y + self.height // 2

         pygame.draw.line(
         screen,
         (255, 0, 0),
          (player_center_x, player_center_y),
         (mouse_x, mouse_y),
            3
       )      