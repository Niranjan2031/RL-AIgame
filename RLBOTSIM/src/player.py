import pygame
import math
import os


class Player:

    def __init__(self):

        # =====================================================
        # POSITION
        # =====================================================

        self.x = 150
        self.y = 155

        self.width = 40
        self.height = 40

        self.rect = pygame.Rect(
        self.x,
        self.y,
        self.width,
        self.height
        )
        self.speed = 5
        self.run_speed = 8

        self.health = 30

        # =====================================================
        # ACTION STATES
        # =====================================================

        self.is_shooting = False
        self.is_reloading = False
        self.is_melee = False

        # =====================================================
        # WEAPONS
        # =====================================================

        self.available_weapons = [
            "handgun",
            "shotgun",
            "rifle",
            "knife"
        ]

        self.current_weapon = "handgun"

        # =====================================================
        # WEAPON STATS
        # =====================================================
        #
        # damage       = bullet damage
        # melee_damage = melee damage
        # reload_speed = animation speed during reload
        #
        # Higher reload_speed = faster reload
        #
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

        self.max_ammo = 12

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
        # ANIMATION SPEEDS
        # =====================================================

        # Normal weapon animation speed
        self.animation_speed = 0.20

        # Faster melee animation
        self.melee_animation_speed = 0.38

        # Feet animation speed
        self.feet_animation_speed = 0.25

        # Current reload speed
        self.reload_animation_speed = 0.20

        # =====================================================
        # FEET CURRENT ANIMATION
        # =====================================================

        self.feet_animation = []

        self.current_feet_animation = []

        # =====================================================
        # ANIMATION FRAME
        # =====================================================

        self.current_frame = 0

        self.feet_frame = 0

        # =====================================================
        # MOVEMENT STATES
        # =====================================================

        self.moving_left = False

        self.moving_right = False

        self.moving_forward = False

        self.moving_backward = False

        # =====================================================
        # PATHS
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
                    "WARNING: Folder not found:",
                    folder
                )

                return frames

            files = sorted(
                os.listdir(folder)
            )

            for file in files:

                if file.lower().endswith(".png"):

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
        # LOAD FEET ANIMATIONS
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
        # LOAD HANDGUN
        # =====================================================

        handgun_folder = os.path.join(
            player_folder,
            "handgun"
        )

        self.handgun_idle_frames = load_frames(
            os.path.join(
                handgun_folder,
                "idle"
            )
        )

        self.handgun_move_frames = load_frames(
            os.path.join(
                handgun_folder,
                "move"
            )
        )

        self.handgun_shoot_frames = load_frames(
            os.path.join(
                handgun_folder,
                "shoot"
            )
        )

        self.handgun_reload_frames = load_frames(
            os.path.join(
                handgun_folder,
                "reload"
            )
        )

        self.handgun_melee_frames = load_frames(
            os.path.join(
                handgun_folder,
                "meleeattack"
            )
        )

        # =====================================================
        # LOAD SHOTGUN
        # =====================================================

        shotgun_folder = os.path.join(
            player_folder,
            "shotgun"
        )

        self.shotgun_idle_frames = load_frames(
            os.path.join(
                shotgun_folder,
                "idle"
            )
        )

        self.shotgun_move_frames = load_frames(
            os.path.join(
                shotgun_folder,
                "move"
            )
        )

        self.shotgun_shoot_frames = load_frames(
            os.path.join(
                shotgun_folder,
                "shoot"
            )
        )

        self.shotgun_reload_frames = load_frames(
            os.path.join(
                shotgun_folder,
                "reload"
            )
        )

        self.shotgun_melee_frames = load_frames(
            os.path.join(
                shotgun_folder,
                "meleeattack"
            )
        )

        # =====================================================
        # LOAD RIFLE
        # =====================================================

        rifle_folder = os.path.join(
            player_folder,
            "rifle"
        )

        self.rifle_idle_frames = load_frames(
            os.path.join(
                rifle_folder,
                "idle"
            )
        )

        self.rifle_move_frames = load_frames(
            os.path.join(
                rifle_folder,
                "move"
            )
        )

        self.rifle_shoot_frames = load_frames(
            os.path.join(
                rifle_folder,
                "shoot"
            )
        )

        self.rifle_reload_frames = load_frames(
            os.path.join(
                rifle_folder,
                "reload"
            )
        )

        self.rifle_melee_frames = load_frames(
            os.path.join(
                rifle_folder,
                "meleeattack"
            )
        )

        # =====================================================
        # LOAD KNIFE
        # =====================================================

        knife_folder = os.path.join(
            player_folder,
            "knife"
        )

        self.knife_idle_frames = load_frames(
            os.path.join(
                knife_folder,
                "idle"
            )
        )

        self.knife_move_frames = load_frames(
            os.path.join(
                knife_folder,
                "move"
            )
        )

        self.knife_melee_frames = load_frames(
            os.path.join(
                knife_folder,
                "meleeattack"
            )
        )

        # =====================================================
        # FEET INITIAL STATE
        # =====================================================

        self.feet_animation = (
            self.feet_idle_frames
        )

        self.current_feet_animation = (
            self.feet_idle_frames
        )

        # =====================================================
        # INITIAL WEAPON
        # =====================================================

        self.set_weapon("handgun")

        # =====================================================
        # WARNINGS
        # =====================================================

        if len(self.feet_idle_frames) == 0:

            print(
                "WARNING: No feet idle animation!"
            )

        if len(self.handgun_idle_frames) == 0:

            print(
                "WARNING: No handgun idle animation!"
            )

        if len(self.shotgun_idle_frames) == 0:

            print(
                "WARNING: No shotgun idle animation!"
            )

        if len(self.rifle_idle_frames) == 0:

            print(
                "WARNING: No rifle idle animation!"
            )

        if len(self.knife_idle_frames) == 0:

            print(
                "WARNING: No knife idle animation!"
            )

    # =========================================================
    # SET WEAPON
    # =========================================================

    def set_weapon(self, weapon):

        # Don't switch during an action

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):

            return False

        if weapon not in self.available_weapons:

            print(
                "Unknown weapon:",
                weapon
            )

            return False

        # =====================================================
        # HANDGUN
        # =====================================================

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

        # =====================================================
        # SHOTGUN
        # =====================================================

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

        # =====================================================
        # RIFLE
        # =====================================================

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

        # =====================================================
        # KNIFE
        # =====================================================

        elif weapon == "knife":

            self.weapon_idle_frames = (
                self.knife_idle_frames
            )

            self.weapon_move_frames = (
                self.knife_move_frames
            )

            # Knife cannot shoot
            self.weapon_shoot_frames = []

            # Knife cannot reload
            self.weapon_reload_frames = []

            # Knife melee
            self.weapon_melee_frames = (
                self.knife_melee_frames
            )

        # =====================================================
        # UPDATE CURRENT WEAPON
        # =====================================================

        self.current_weapon = weapon

        # =====================================================
        # UPDATE AMMO
        # =====================================================

        if weapon == "knife":

            self.max_ammo = None

            self.ammo = None

        else:

            self.max_ammo = (
                self.weapon_max_ammo[
                    weapon
                ]
            )

            # Give full magazine when switching gun
            self.ammo = self.max_ammo

        # =====================================================
        # UPDATE RELOAD SPEED
        # =====================================================

        reload_speed = self.weapon_stats[
            weapon
        ][
            "reload_speed"
        ]

        if reload_speed is not None:

            self.reload_animation_speed = (
                reload_speed
            )

        # =====================================================
        # RESET ANIMATION
        # =====================================================

        self.current_frame = 0

        self.weapon_animation = (
            self.weapon_idle_frames
        )

        print(
            "Weapon switched to:",
            self.current_weapon
        )

        return True

    # =========================================================
    # SWITCH WEAPON
    # =========================================================

    def switch_weapon(self):

        if self.current_weapon == "handgun":

            self.set_weapon("shotgun")

        elif self.current_weapon == "shotgun":

            self.set_weapon("rifle")

        elif self.current_weapon == "rifle":

            self.set_weapon("knife")

        else:

            self.set_weapon("handgun")

    # =========================================================
    # GET BULLET DAMAGE
    # =========================================================

    def get_damage(self):

        return self.weapon_stats[
            self.current_weapon
        ][
            "damage"
        ]

    # =========================================================
    # GET MELEE DAMAGE
    # =========================================================

    def get_melee_damage(self):

        return self.weapon_stats[
            self.current_weapon
        ][
            "melee_damage"
        ]

    # =========================================================
    # GET RELOAD SPEED
    # =========================================================

    def get_reload_speed(self):

        return self.weapon_stats[
            self.current_weapon
        ][
            "reload_speed"
        ]

    # =========================================================
    # DAMAGE
    # =========================================================

    def take_damage(self, damage):

        self.health -= damage

        if self.health < 0:

            self.health = 0

        print(
            "Player Health:",
            self.health
        )

    # =========================================================
    # SHOOT
    # =========================================================

    def shoot(self):

        # Knife cannot shoot

        if self.current_weapon == "knife":

            return False

        if self.is_shooting:

            return False

        if self.is_reloading:

            return False

        if self.is_melee:

            return False

        if self.ammo <= 0:

            print(
                "OUT OF AMMO!"
            )

            return False

        if len(self.weapon_shoot_frames) == 0:

            return False

        # Consume ammo

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

        # Knife cannot reload

        if self.current_weapon == "knife":

            return False

        if self.is_shooting:

            return False

        if self.is_reloading:

            return False

        if self.is_melee:

            return False

        if self.ammo >= self.max_ammo:

            print(
                "Magazine already full."
            )

            return False

        if len(self.weapon_reload_frames) == 0:

            return False

        self.is_reloading = True

        self.weapon_animation = (
            self.weapon_reload_frames
        )

        self.current_frame = 0

        print(
            "Reloading:",
            self.current_weapon
        )

        return True

    # =========================================================
    # MELEE
    # =========================================================

    def melee_attack(self):

        if self.is_shooting:

            return False

        if self.is_reloading:

            return False

        if self.is_melee:

            return False

        if len(self.weapon_melee_frames) == 0:

            return False

        self.is_melee = True

        self.weapon_animation = (
            self.weapon_melee_frames
        )

        self.current_frame = 0

        return True

    # =========================================================
    # SET MOVEMENT ANIMATION
    # =========================================================

    def set_movement_animation(
        self,
        feet_animation,
        weapon_animation
    ):

        if len(feet_animation) > 0:

            if (
                self.feet_animation
                != feet_animation
            ):

                self.feet_animation = (
                    feet_animation
                )

                self.current_feet_animation = (
                    feet_animation
                )

                self.feet_frame = 0

        if len(weapon_animation) > 0:

            if (
                self.weapon_animation
                != weapon_animation
            ):

                self.weapon_animation = (
                    weapon_animation
                )

    # =========================================================
    # UPDATE WEAPON ANIMATION
    # =========================================================

    def update_weapon_animation(self):

        if len(self.weapon_animation) == 0:

            return

        # =================================================
        # MELEE SPEED
        # =================================================

        if self.is_melee:

            self.current_frame += (
                self.melee_animation_speed
            )

        # =================================================
        # RELOAD SPEED
        # =================================================

        elif self.is_reloading:

            self.current_frame += (
                self.reload_animation_speed
            )

        # =================================================
        # NORMAL SPEED
        # =================================================

        else:

            self.current_frame += (
                self.animation_speed
            )

        # =================================================
        # ANIMATION FINISHED
        # =================================================

        if (
            self.current_frame
            >= len(self.weapon_animation)
        ):

            # ---------------------------------------------
            # SHOOT FINISHED
            # ---------------------------------------------

            if self.is_shooting:

                self.is_shooting = False

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

            # ---------------------------------------------
            # RELOAD FINISHED
            # ---------------------------------------------

            elif self.is_reloading:

                self.is_reloading = False

                self.current_frame = 0

                # Refill magazine
                self.ammo = self.max_ammo

                print(
                    "Reload complete:",
                    self.ammo,
                    "/",
                    self.max_ammo
                )

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

            # ---------------------------------------------
            # MELEE FINISHED
            # ---------------------------------------------

            elif self.is_melee:

                self.is_melee = False

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

            # ---------------------------------------------
            # NORMAL ANIMATION
            # ---------------------------------------------

            else:

                self.current_frame = 0

        # =================================================
        # SAFETY
        # =================================================

        if len(self.weapon_animation) > 0:

            frame_index = int(
                self.current_frame
            )

            if (
                frame_index
                >= len(self.weapon_animation)
            ):

                frame_index = 0

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

        # ---------------------------------------------
        # Animate feet
        # ---------------------------------------------

        if not (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):

            self.feet_frame += (
                self.feet_animation_speed
            )

        # ---------------------------------------------
        # Loop animation
        # ---------------------------------------------

        if (
            self.feet_frame
            >= len(self.current_feet_animation)
        ):

            self.feet_frame = 0

        # Safety
        if len(
            self.current_feet_animation
        ) > 0:

            self.original_feet_image = (
                self.current_feet_animation[
                    int(self.feet_frame)
                    % len(self.current_feet_animation)
                ]
            )

    # =========================================================
    # UPDATE ANIMATIONS
    # =========================================================

    def update_animation(self):

        self.update_weapon_animation()

        self.update_feet_animation()

    # =========================================================
    # DRAW
    # =========================================================

    def draw(self, screen):

        self.update_animation()

        # =================================================
        # PLAYER CENTER
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
        # AIM DIRECTION
        # =================================================

        mouse_x, mouse_y = (
            pygame.mouse.get_pos()
        )

        dx = mouse_x - center_x

        dy = mouse_y - center_y

        angle = math.degrees(
            math.atan2(
                -dy,
                dx
            )
        )

        # =================================================
        # FEET LAYER
        # =================================================

        if len(
            self.current_feet_animation
        ) > 0:

            feet_index = (
                int(self.feet_frame)
                % len(
                    self.current_feet_animation
                )
            )

            feet_image = (
                self.current_feet_animation[
                    feet_index
                ]
            )

            rotated_feet = (
                pygame.transform.rotate(
                    feet_image,
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
        # WEAPON / UPPER BODY LAYER
        # =================================================

        if len(
            self.weapon_animation
        ) > 0:

            weapon_index = (
                int(self.current_frame)
                % len(self.weapon_animation)
            )

            weapon_image = (
                self.weapon_animation[
                    weapon_index
                ]
            )

            rotated_weapon = (
                pygame.transform.rotate(
                    weapon_image,
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

    # =========================================================
    # MOVEMENT
    # =========================================================

    def move(self,obstacles=None):

        keys = pygame.key.get_pressed()

        # Reset movement states

        self.moving_left = False

        self.moving_right = False

        self.moving_forward = False

        self.moving_backward = False

        # =================================================
        # SPEED
        # =================================================

        current_speed = self.speed

        if (
            keys[pygame.K_w]
            and keys[pygame.K_LSHIFT]
        ):

            current_speed = self.run_speed

        # =================================================
        # FORWARD
        # =================================================
        dx = 0
        dy = 0
        if keys[pygame.K_w]:

            dy -= current_speed

            self.moving_forward = True

        # =================================================
        # BACKWARD
        # =================================================

        if keys[pygame.K_s]:

            dy += self.speed

            self.moving_backward = True

        # =================================================
        # STRAFE LEFT
        # =================================================

        if keys[pygame.K_a]:

            dx -= self.speed

            self.moving_left = True

        # =================================================
        # STRAFE RIGHT
        # =================================================

        if keys[pygame.K_d]:

            dx += self.speed

            self.moving_right = True

        # Current player rectangle
        self.rect.topleft = (self.x, self.y)

        # Try horizontal movement
        new_rect = self.rect.copy()
        new_rect.x += dx

        collision = False

        if obstacles:
            for obstacle in obstacles:
                if new_rect.colliderect(obstacle.rect):
                    collision = True
                    break

        if not collision:
            self.x += dx

        # Try vertical movement
        new_rect = self.rect.copy()
        new_rect.y += dy

        collision = False

        if obstacles:
            for obstacle in obstacles:
                if new_rect.colliderect(obstacle.rect):
                    collision = True
                    break

        if not collision:
            self.y += dy

        # Update rectangle
        self.rect.topleft = (self.x, self.y)
        # =================================================
        # FEET ANIMATION
        # =================================================

        # Don't change feet animation during actions

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):

            return

        # ---------------------------------------------
        # LEFT STRAFE
        # ---------------------------------------------

        if (
            self.moving_left
            and not self.moving_right
        ):

            if len(
                self.feet_strafe_left_frames
            ) > 0:

                self.current_feet_animation = (
                    self.feet_strafe_left_frames
                )

                self.feet_animation = (
                    self.feet_strafe_left_frames
                )

        # ---------------------------------------------
        # RIGHT STRAFE
        # ---------------------------------------------

        elif (
            self.moving_right
            and not self.moving_left
        ):

            if len(
                self.feet_strafe_right_frames
            ) > 0:

                self.current_feet_animation = (
                    self.feet_strafe_right_frames
                )

                self.feet_animation = (
                    self.feet_strafe_right_frames
                )

        # ---------------------------------------------
        # FORWARD / RUN
        # ---------------------------------------------

        elif self.moving_forward:

            if (
                keys[pygame.K_LSHIFT]
                and len(
                    self.feet_run_frames
                ) > 0
            ):

                self.current_feet_animation = (
                    self.feet_run_frames
                )

                self.feet_animation = (
                    self.feet_run_frames
                )

            elif len(
                self.feet_walk_frames
            ) > 0:

                self.current_feet_animation = (
                    self.feet_walk_frames
                )

                self.feet_animation = (
                    self.feet_walk_frames
                )

        # ---------------------------------------------
        # BACKWARD
        # ---------------------------------------------

        elif self.moving_backward:

            if len(
                self.feet_walk_frames
            ) > 0:

                self.current_feet_animation = (
                    self.feet_walk_frames
                )

                self.feet_animation = (
                    self.feet_walk_frames
                )

        # ---------------------------------------------
        # IDLE
        # ---------------------------------------------

        else:

            if len(
                self.feet_idle_frames
            ) > 0:

                self.current_feet_animation = (
                    self.feet_idle_frames
                )

                self.feet_animation = (
                    self.feet_idle_frames
                )

    # =========================================================
    # AIM LINE
    # =========================================================

    def aim(self, screen):

        mouse_x, mouse_y = (
            pygame.mouse.get_pos()
        )

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