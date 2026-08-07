import pygame
import math
import os


class Player:

    def __init__(self):

        self.x = 100
        self.y = 100

        self.width = 80
        self.height = 80

        self.speed = 5
        self.health = 30

        # =====================================================
        # WEAPON
        # =====================================================

        self.current_weapon = "handgun"

        # =====================================================
        # ANIMATION FRAME LISTS
        # =====================================================

        self.idle_frames = []
        self.move_frames = []
        self.shoot_frames = []
        self.reload_frames = []
        self.melee_frames = []

        current_dir = os.path.dirname(__file__)

        # =====================================================
        # LOAD ANIMATION FUNCTION
        # =====================================================

        def load_frames(folder_name):

            folder = os.path.join(
                current_dir,
                "..",
                "assets",
                "player",
                self.current_weapon,
                folder_name
            )

            frames = []

            for file in sorted(os.listdir(folder)):

                if file.endswith(".png"):

                    image = pygame.image.load(
                        os.path.join(folder, file)
                    ).convert_alpha()

                    image = pygame.transform.scale(
                        image,
                        (self.width, self.height)
                    )

                    frames.append(image)

            return frames

        # =====================================================
        # LOAD ALL ANIMATIONS
        # =====================================================

        self.idle_frames = load_frames("idle")
        self.move_frames = load_frames("move")
        self.shoot_frames = load_frames("shoot")
        self.reload_frames = load_frames("reload")

        # Your folder is called meleeattack
        self.melee_frames = load_frames("meleeattack")

        # =====================================================
        # ANIMATION VARIABLES
        # =====================================================

        self.current_animation = self.idle_frames

        self.current_frame = 0

        # Normal animation speed
        self.animation_speed = 0.20

        # Slower melee animation
        self.melee_animation_speed = 0.12

        self.is_shooting = False
        self.is_reloading = False
        self.is_melee = False

        self.original_image = self.current_animation[0]

    # =====================================================
    # DAMAGE
    # =====================================================

    def take_damage(self, damage):

        self.health -= damage

        print("Player Health:", self.health)

    # =====================================================
    # SHOOT
    # =====================================================

    def shoot(self):

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):
            return False

        if len(self.shoot_frames) == 0:
            return False

        self.is_shooting = True

        self.current_animation = self.shoot_frames
        self.current_frame = 0

        return True

    # =====================================================
    # RELOAD
    # =====================================================

    def reload(self):

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):
            return False

        if len(self.reload_frames) == 0:
            return False

        self.is_reloading = True

        self.current_animation = self.reload_frames
        self.current_frame = 0

        return True

    # =====================================================
    # MELEE ATTACK
    # =====================================================

    def melee_attack(self):

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):
            return False

        if len(self.melee_frames) == 0:
            return False

        self.is_melee = True

        self.current_animation = self.melee_frames
        self.current_frame = 0

        return True

    # =====================================================
    # ANIMATION UPDATE
    # =====================================================

    def update_animation(self):

        # Use slower speed for melee
        if self.is_melee:

            self.current_frame += self.melee_animation_speed

        else:

            self.current_frame += self.animation_speed

        # Check if animation has finished
        if self.current_frame >= len(self.current_animation):

            # ---------------------------------------------
            # SHOOT FINISHED
            # ---------------------------------------------

            if self.is_shooting:

                self.is_shooting = False

                self.current_frame = 0

                self.current_animation = self.idle_frames

            # ---------------------------------------------
            # RELOAD FINISHED
            # ---------------------------------------------

            elif self.is_reloading:

                self.is_reloading = False

                self.current_frame = 0

                self.current_animation = self.idle_frames

            # ---------------------------------------------
            # MELEE FINISHED
            # ---------------------------------------------

            elif self.is_melee:

                self.is_melee = False

                self.current_frame = 0

                self.current_animation = self.idle_frames

            # ---------------------------------------------
            # IDLE / MOVE
            # ---------------------------------------------

            else:

                self.current_frame = 0

        self.original_image = self.current_animation[
            int(self.current_frame)
        ]

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen):

        self.update_animation()

        mouse_x, mouse_y = pygame.mouse.get_pos()

        player_center_x = (
            self.x +
            self.width // 2
        )

        player_center_y = (
            self.y +
            self.height // 2
        )

        # Distance from player to mouse
        dx = mouse_x - player_center_x
        dy = mouse_y - player_center_y

        # Calculate rotation
        angle = math.degrees(
            math.atan2(-dy, dx)
        )

        # Rotate current animation frame
        rotated_image = pygame.transform.rotate(
            self.original_image,
            angle
        )

        # Keep player centered
        rotated_rect = rotated_image.get_rect(
            center=(
                player_center_x,
                player_center_y
            )
        )

        screen.blit(
            rotated_image,
            rotated_rect.topleft
        )

    # =====================================================
    # MOVEMENT
    # =====================================================

    def move(self):

        # Cannot move during action animations
        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):
            return

        keys = pygame.key.get_pressed()

        moving = False

        # W
        if keys[pygame.K_w]:

            self.y -= self.speed
            moving = True

        # S
        if keys[pygame.K_s]:

            self.y += self.speed
            moving = True

        # A
        if keys[pygame.K_a]:

            self.x -= self.speed
            moving = True

        # D
        if keys[pygame.K_d]:

            self.x += self.speed
            moving = True

        # ---------------------------------------------
        # MOVING
        # ---------------------------------------------

        if moving:

            if self.current_animation != self.move_frames:

                self.current_animation = self.move_frames
                self.current_frame = 0

        # ---------------------------------------------
        # NOT MOVING
        # ---------------------------------------------

        else:

            if self.current_animation != self.idle_frames:

                self.current_animation = self.idle_frames
                self.current_frame = 0

    # =====================================================
    # AIM LINE
    # =====================================================

    def aim(self, screen):

        mouse_x, mouse_y = pygame.mouse.get_pos()

        player_center_x = (
            self.x +
            self.width // 2
        )

        player_center_y = (
            self.y +
            self.height // 2
        )

        pygame.draw.line(
            screen,
            (255, 0, 0),
            (
                player_center_x,
                player_center_y
            ),
            (
                mouse_x,
                mouse_y
            ),
            3
        )