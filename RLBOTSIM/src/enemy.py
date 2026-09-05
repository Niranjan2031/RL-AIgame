import pygame
import math
import random
import time
import os


class Enemy:

    def __init__(self):

        # =====================================================
        # POSITION
        # =====================================================

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
        self.health = 30


        # =====================================================
        # ACTION STATES
        # =====================================================

        self.is_shooting = False
        self.is_reloading = False
        self.is_melee = False


        # =====================================================
        # RANDOM WEAPON
        # =====================================================

        self.available_weapons = [
            "handgun",
            "shotgun",
            "rifle",
            "knife"
        ]

        self.current_weapon = random.choice(
            self.available_weapons
        )


        # =====================================================
        # WEAPON STATS
        # =====================================================

        self.weapon_stats = {

            "handgun": {
                "damage": 5,
                "melee_damage": 5,
                "reload_speed": 0.28
            },

            "shotgun": {
                "damage": 12,
                "melee_damage": 10,
                "reload_speed": 0.16
            },

            "rifle": {
                "damage": 4,
                "melee_damage": 6,
                "reload_speed": 0.22
            },

            "knife": {
                "damage": None,
                "melee_damage": 15,
                "reload_speed": None
            }
        }


        # =====================================================
        # AMMO
        # =====================================================

        self.weapon_max_ammo = {

            "handgun": 12,
            "shotgun": 6,
            "rifle": 30
        }

        if self.current_weapon == "knife":

            self.max_ammo = None
            self.ammo = None

        else:

            self.max_ammo = (
                self.weapon_max_ammo[
                    self.current_weapon
                ]
            )

            self.ammo = self.max_ammo


        # =====================================================
        # FEET ANIMATIONS
        # =====================================================

        self.feet_idle_frames = []

        self.feet_walk_frames = []

        self.feet_run_frames = []

        self.feet_strafe_left_frames = []

        self.feet_strafe_right_frames = []


        # =====================================================
        # HANDGUN ANIMATIONS
        # =====================================================

        self.handgun_idle_frames = []
        self.handgun_move_frames = []
        self.handgun_shoot_frames = []
        self.handgun_reload_frames = []
        self.handgun_melee_frames = []


        # =====================================================
        # SHOTGUN ANIMATIONS
        # =====================================================

        self.shotgun_idle_frames = []
        self.shotgun_move_frames = []
        self.shotgun_shoot_frames = []
        self.shotgun_reload_frames = []
        self.shotgun_melee_frames = []


        # =====================================================
        # RIFLE ANIMATIONS
        # =====================================================

        self.rifle_idle_frames = []
        self.rifle_move_frames = []
        self.rifle_shoot_frames = []
        self.rifle_reload_frames = []
        self.rifle_melee_frames = []


        # =====================================================
        # KNIFE ANIMATIONS
        # =====================================================

        self.knife_idle_frames = []
        self.knife_move_frames = []
        self.knife_melee_frames = []


        # =====================================================
        # CURRENT WEAPON ANIMATIONS
        # =====================================================

        self.weapon_idle_frames = []

        self.weapon_move_frames = []

        self.weapon_shoot_frames = []

        self.weapon_reload_frames = []

        self.weapon_melee_frames = []

        self.weapon_animation = []


        # =====================================================
        # ANIMATION SETTINGS
        # =====================================================

        self.animation_speed = 0.20

        self.melee_animation_speed = 0.38

        self.feet_animation_speed = 0.25

        self.reload_animation_speed = 0.20


        # =====================================================
        # CURRENT ANIMATION STATE
        # =====================================================

        self.current_frame = 0

        self.feet_frame = 0

        self.current_feet_animation = []

        self.feet_animation = []


        # =====================================================
        # LOAD ASSETS
        # =====================================================

        current_dir = os.path.dirname(__file__)

        player_folder = os.path.join(
            current_dir,
            "..",
            "assets",
            "player"
        )

        feet_folder = os.path.join(
            player_folder,
            "feet"
        )


        # =====================================================
        # LOAD FRAME FUNCTION
        # =====================================================

        def load_frames(folder):

            frames = []

            if not os.path.exists(folder):

                print(
                    "WARNING: Animation folder not found:",
                    folder
                )

                return frames

            files = sorted(
                [
                    file
                    for file in os.listdir(folder)
                    if file.lower().endswith(".png")
                ]
            )

            for file in files:

                image_path = os.path.join(
                    folder,
                    file
                )

                image = pygame.image.load(
                    image_path
                ).convert_alpha()

                image = pygame.transform.scale(
                    image,
                    (
                        self.width,
                        self.height
                    )
                )

                frames.append(image)

            return frames


        # =====================================================
        # LOAD FEET
        # =====================================================

        self.feet_idle_frames = load_frames(
            os.path.join(
                feet_folder,
                "idle"
            )
        )

        self.feet_walk_frames = load_frames(
            os.path.join(
                feet_folder,
                "walk"
            )
        )

        self.feet_run_frames = load_frames(
            os.path.join(
                feet_folder,
                "run"
            )
        )

        self.feet_strafe_left_frames = load_frames(
            os.path.join(
                feet_folder,
                "strafe_left"
            )
        )

        self.feet_strafe_right_frames = load_frames(
            os.path.join(
                feet_folder,
                "strafe_right"
            )
        )


        # =====================================================
        # LOAD ALL WEAPON ANIMATIONS
        # =====================================================

        def load_weapon(
            weapon,
            animation
        ):

            return load_frames(
                os.path.join(
                    player_folder,
                    weapon,
                    animation
                )
            )


        # =====================================================
        # HANDGUN
        # =====================================================

        self.handgun_idle_frames = (
            load_weapon("handgun", "idle")
        )

        self.handgun_move_frames = (
            load_weapon("handgun", "move")
        )

        self.handgun_shoot_frames = (
            load_weapon("handgun", "shoot")
        )

        self.handgun_reload_frames = (
            load_weapon("handgun", "reload")
        )

        self.handgun_melee_frames = (
            load_weapon(
                "handgun",
                "meleeattack"
            )
        )


        # =====================================================
        # SHOTGUN
        # =====================================================

        self.shotgun_idle_frames = (
            load_weapon("shotgun", "idle")
        )

        self.shotgun_move_frames = (
            load_weapon("shotgun", "move")
        )

        self.shotgun_shoot_frames = (
            load_weapon("shotgun", "shoot")
        )

        self.shotgun_reload_frames = (
            load_weapon("shotgun", "reload")
        )

        self.shotgun_melee_frames = (
            load_weapon(
                "shotgun",
                "meleeattack"
            )
        )


        # =====================================================
        # RIFLE
        # =====================================================

        self.rifle_idle_frames = (
            load_weapon("rifle", "idle")
        )

        self.rifle_move_frames = (
            load_weapon("rifle", "move")
        )

        self.rifle_shoot_frames = (
            load_weapon("rifle", "shoot")
        )

        self.rifle_reload_frames = (
            load_weapon("rifle", "reload")
        )

        self.rifle_melee_frames = (
            load_weapon(
                "rifle",
                "meleeattack"
            )
        )


        # =====================================================
        # KNIFE
        # =====================================================

        self.knife_idle_frames = (
            load_weapon("knife", "idle")
        )

        self.knife_move_frames = (
            load_weapon("knife", "move")
        )

        self.knife_melee_frames = (
            load_weapon(
                "knife",
                "meleeattack"
            )
        )


        # =====================================================
        # SET CURRENT WEAPON
        # =====================================================

        self.set_weapon(
            self.current_weapon
        )


        # =====================================================
        # SET DEFAULT FEET
        # =====================================================

        self.current_feet_animation = (
            self.feet_idle_frames
        )

        self.feet_animation = (
            self.feet_idle_frames
        )


        # =====================================================
        # DEFAULT IMAGES
        # =====================================================

        if len(
            self.current_feet_animation
        ) > 0:

            self.original_feet_image = (
                self.current_feet_animation[0]
            )

        else:

            self.original_feet_image = None


        if len(
            self.weapon_animation
        ) > 0:

            self.original_image = (
                self.weapon_animation[0]
            )

        else:

            self.original_image = None


        # =====================================================
        # ATTACK
        # =====================================================

        self.attack_cooldown = 1.0

        self.last_attack_time = 0


    # =========================================================
    # SET WEAPON
    # =========================================================

    def set_weapon(self, weapon):

        if weapon not in self.available_weapons:

            return False


        # -----------------------------------------------------
        # HANDGUN
        # -----------------------------------------------------

        if weapon == "handgun":

            self.weapon_idle_frames = (
                self.handgun_idle_frames
            )

            self.weapon_move_frames = (
                self.handgun_move_frames
            )

            self.weapon_shoot_frames = (
                self.handgun_shoot_frames
            )

            self.weapon_reload_frames = (
                self.handgun_reload_frames
            )

            self.weapon_melee_frames = (
                self.handgun_melee_frames
            )


        # -----------------------------------------------------
        # SHOTGUN
        # -----------------------------------------------------

        elif weapon == "shotgun":

            self.weapon_idle_frames = (
                self.shotgun_idle_frames
            )

            self.weapon_move_frames = (
                self.shotgun_move_frames
            )

            self.weapon_shoot_frames = (
                self.shotgun_shoot_frames
            )

            self.weapon_reload_frames = (
                self.shotgun_reload_frames
            )

            self.weapon_melee_frames = (
                self.shotgun_melee_frames
            )


        # -----------------------------------------------------
        # RIFLE
        # -----------------------------------------------------

        elif weapon == "rifle":

            self.weapon_idle_frames = (
                self.rifle_idle_frames
            )

            self.weapon_move_frames = (
                self.rifle_move_frames
            )

            self.weapon_shoot_frames = (
                self.rifle_shoot_frames
            )

            self.weapon_reload_frames = (
                self.rifle_reload_frames
            )

            self.weapon_melee_frames = (
                self.rifle_melee_frames
            )


        # -----------------------------------------------------
        # KNIFE
        # -----------------------------------------------------

        elif weapon == "knife":

            self.weapon_idle_frames = (
                self.knife_idle_frames
            )

            self.weapon_move_frames = (
                self.knife_move_frames
            )

            self.weapon_shoot_frames = []

            self.weapon_reload_frames = []

            self.weapon_melee_frames = (
                self.knife_melee_frames
            )


        self.current_weapon = weapon


        # -----------------------------------------------------
        # AMMO
        # -----------------------------------------------------

        if weapon == "knife":

            self.max_ammo = None
            self.ammo = None

        else:

            self.max_ammo = (
                self.weapon_max_ammo[
                    weapon
                ]
            )

            self.ammo = self.max_ammo


        # -----------------------------------------------------
        # DEFAULT ANIMATION
        # -----------------------------------------------------

        self.current_frame = 0

        self.weapon_animation = (
            self.weapon_idle_frames
        )

        return True


    # =========================================================
    # DAMAGE
    # =========================================================

    def take_damage(self, damage):

        self.health -= damage

        if self.health <= 0:

            self.health = 0

            self.alive = False


    # =========================================================
    # SHOOT ANIMATION
    # =========================================================

    def shoot(self):

        if self.current_weapon == "knife":

            return False

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):

            return False

        if self.ammo <= 0:

            self.reload()

            return False

        if len(
            self.weapon_shoot_frames
        ) == 0:

            return False

        self.ammo -= 1

        self.is_shooting = True

        self.weapon_animation = (
            self.weapon_shoot_frames
        )

        self.current_frame = 0

        return True


    # =========================================================
    # RELOAD
    # =========================================================

    def reload(self):

        if self.current_weapon == "knife":

            return False

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):

            return False

        if len(
            self.weapon_reload_frames
        ) == 0:

            self.ammo = self.max_ammo

            return True

        self.is_reloading = True

        self.weapon_animation = (
            self.weapon_reload_frames
        )

        self.current_frame = 0

        return True


    # =========================================================
    # MELEE ATTACK
    # =========================================================

    def melee_attack(self):

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):

            return False

        if len(
            self.weapon_melee_frames
        ) == 0:

            return False

        self.is_melee = True

        self.weapon_animation = (
            self.weapon_melee_frames
        )

        self.current_frame = 0

        return True


    # =========================================================
    # UPDATE WEAPON ANIMATION
    # =========================================================

    def update_weapon_animation(self):

        if len(
            self.weapon_animation
        ) == 0:

            return


        if self.is_melee:

            self.current_frame += (
                self.melee_animation_speed
            )

        elif self.is_reloading:

            self.current_frame += (
                self.reload_animation_speed
            )

        else:

            self.current_frame += (
                self.animation_speed
            )


        if (
            self.current_frame
            >= len(self.weapon_animation)
        ):

            if self.is_shooting:

                self.is_shooting = False

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )


            elif self.is_reloading:

                self.is_reloading = False

                self.current_frame = 0

                self.ammo = self.max_ammo

                self.weapon_animation = (
                    self.weapon_idle_frames
                )


            elif self.is_melee:

                self.is_melee = False

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )


            else:

                self.current_frame = 0


        frame_index = (
            int(self.current_frame)
            % len(self.weapon_animation)
        )

        self.original_image = (
            self.weapon_animation[
                frame_index
            ]
        )


    # =========================================================
    # UPDATE FEET ANIMATION
    # =========================================================

    def update_feet_animation(self):

        if len(
            self.current_feet_animation
        ) == 0:

            return


        self.feet_frame += (
            self.feet_animation_speed
        )


        if (
            self.feet_frame
            >= len(
                self.current_feet_animation
            )
        ):

            self.feet_frame = 0


        frame_index = (
            int(self.feet_frame)
            % len(
                self.current_feet_animation
            )
        )

        self.original_feet_image = (
            self.current_feet_animation[
                frame_index
            ]
        )


    # =========================================================
    # MOVE
    # =========================================================

    def move(
        self,
        player,
        enemies,
        obstacles=None
    ):

        if not self.alive:

            return


        # Direction toward player

        dx = player.x - self.x

        dy = player.y - self.y


        distance = math.sqrt(
            dx ** 2 +
            dy ** 2
        )


        if distance == 0:

            return


        move_x = (
            dx / distance
        ) * self.speed

        move_y = (
            dy / distance
        ) * self.speed


        # =================================================
        # MOVING ANIMATION
        # =================================================

        if (
            not self.is_shooting
            and not self.is_reloading
            and not self.is_melee
        ):

            self.current_feet_animation = (
                self.feet_walk_frames
            )

            self.weapon_animation = (
                self.weapon_move_frames
            )


        # =================================================
        # HORIZONTAL MOVEMENT
        # =================================================

        self.rect.topleft = (
            int(self.x),
            int(self.y)
        )


        new_rect = self.rect.copy()

        new_rect.x += int(move_x)

        collision = False


        if obstacles:

            for obstacle in obstacles:

                if new_rect.colliderect(
                    obstacle.rect
                ):

                    collision = True

                    break


        if not collision:

            for other in enemies:

                if other is self:

                    continue

                if not other.alive:

                    continue

                other_rect = pygame.Rect(
                    other.x,
                    other.y,
                    other.width,
                    other.height
                )

                if new_rect.colliderect(
                    other_rect
                ):

                    collision = True

                    break


        if not collision:

            self.x += move_x


        # =================================================
        # VERTICAL MOVEMENT
        # =================================================

        self.rect.topleft = (
            int(self.x),
            int(self.y)
        )


        new_rect = self.rect.copy()

        new_rect.y += int(move_y)

        collision = False


        if obstacles:

            for obstacle in obstacles:

                if new_rect.colliderect(
                    obstacle.rect
                ):

                    collision = True

                    break


        if not collision:

            for other in enemies:

                if other is self:

                    continue

                if not other.alive:

                    continue

                other_rect = pygame.Rect(
                    other.x,
                    other.y,
                    other.width,
                    other.height
                )

                if new_rect.colliderect(
                    other_rect
                ):

                    collision = True

                    break


        if not collision:

            self.y += move_y


        self.rect.topleft = (
            int(self.x),
            int(self.y)
        )


    # =========================================================
    # DRAW
    # =========================================================

    def draw(
        self,
        screen,
        player
    ):

        if not self.alive:

            return


        self.update_weapon_animation()

        self.update_feet_animation()


        # =================================================
        # ENEMY CENTER
        # =================================================

        center_x = (
            self.x +
            self.width // 2
        )

        center_y = (
            self.y +
            self.height // 2
        )


        # =================================================
        # FACE PLAYER
        # =================================================

        player_center_x = (
            player.x +
            player.width // 2
        )

        player_center_y = (
            player.y +
            player.height // 2
        )


        dx = (
            player_center_x -
            center_x
        )

        dy = (
            player_center_y -
            center_y
        )


        angle = math.degrees(
            math.atan2(
                -dy,
                dx
            )
        )


        # =================================================
        # FEET
        # =================================================

        if (
            self.original_feet_image
            is not None
        ):

            rotated_feet = (
                pygame.transform.rotate(
                    self.original_feet_image,
                    angle
                )
            )

            feet_rect = (
                rotated_feet.get_rect(
                    center=(
                        center_x,
                        center_y
                    )
                )
            )

            screen.blit(
                rotated_feet,
                feet_rect.topleft
            )


        # =================================================
        # WEAPON / BODY
        # =================================================

        if (
            self.original_image
            is not None
        ):

            rotated_weapon = (
                pygame.transform.rotate(
                    self.original_image,
                    angle
                )
            )

            weapon_rect = (
                rotated_weapon.get_rect(
                    center=(
                        center_x,
                        center_y
                    )
                )
            )

            screen.blit(
                rotated_weapon,
                weapon_rect.topleft
            )


        # =================================================
        # HEALTH BAR
        # =================================================

        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (
                self.x,
                self.y - 12,
                self.width,
                6
            )
        )


        pygame.draw.rect(
            screen,
            (0, 255, 0),
            (
                self.x,
                self.y - 12,
                (
                    self.health / 30
                ) * self.width,
                6
            )
        )


    # =========================================================
    # BULLET COLLISION
    # =========================================================

    def check_collision(
        self,
        bullet
    ):

        if not self.alive:

            return False


        return self.rect.collidepoint(
            bullet.x,
            bullet.y
        )


    # =========================================================
    # PLAYER COLLISION
    # =========================================================

    def check_player_collision(
        self,
        player
    ):

        if not self.alive:

            return False


        return self.rect.colliderect(
            player.rect
        )


    # =========================================================
    # MELEE DAMAGE
    # =========================================================

    def attack(
        self,
        player
    ):

        if not self.alive:

            return


        current_time = time.time()


        if (
            current_time
            -
            self.last_attack_time
            >=
            self.attack_cooldown
        ):

            damage = (
                self.weapon_stats[
                    self.current_weapon
                ][
                    "melee_damage"
                ]
            )


            player.take_damage(
                damage
            )


            self.last_attack_time = (
                current_time
            )