import pygame
import math
import os
import time


class RLBot:

    WIDTH = 40
    HEIGHT = 40

    # =========================================================
    # FINAL RL ACTIONS
    # =========================================================

    ACTION_IDLE = 0
    ACTION_FORWARD = 1
    ACTION_BACKWARD = 2
    ACTION_LEFT = 3
    ACTION_RIGHT = 4
    ACTION_SPRINT = 5
    ACTION_SHOOT = 6
    ACTION_RELOAD = 7
    ACTION_MELEE = 8

    # ---------------------------------------------------------
    # Old weapon-action constants kept only for compatibility.
    # They are NOT part of the final RL action space.
    # ---------------------------------------------------------

    ACTION_HANDGUN = 9
    ACTION_SHOTGUN = 10
    ACTION_RIFLE = 11
    ACTION_KNIFE = 12

    # =========================================================
    # WEAPONS
    # =========================================================

    WEAPON_STATS = {

        "handgun": {
            "damage": 1,
            "melee_damage": 1,
            "reload_time": 0.28,
            "max_ammo": 12,
        },

        "shotgun": {
            "damage": 4,
            "melee_damage": 4,
            "reload_time": 0.16,
            "max_ammo": 6,
        },

        "rifle": {
            "damage": 1,
            "melee_damage": 1,
            "reload_time": 0.22,
            "max_ammo": 30,
        },

        "knife": {
            "damage": 0,
            "melee_damage": 5,
            "reload_time": 0.0,
            "max_ammo": None,
        },
    }

    # Final deterministic weapon-selection ranges.

    WEAPON_RANGES = {
        "knife": 75,
        "shotgun": 110,
        "handgun": 200,
        "rifle": 280,
    }

    def __init__(self, x, y):

        # =====================================================
        # POSITION
        # =====================================================

        self.x = float(x)
        self.y = float(y)

        self.width = self.WIDTH
        self.height = self.HEIGHT

        self.speed = 2.3
        self.run_speed = 3.0

        # =====================================================
        # HEALTH
        # =====================================================

        self.health = 30
        self.max_health = 30

        # =====================================================
        # GAME / RL INTEGRATION STATE
        # =====================================================

        self.alive = True

        self.map_left = None
        self.map_top = None
        self.map_right = None
        self.map_bottom = None

        self.RL_MELEE_RANGE = 75

        self.bot_number = None

        # =====================================================
        # WEAPON
        # =====================================================

        self.weapon = "handgun"

        # Each weapon has its own magazine.

        self.weapon_ammo = {

            "handgun": 12,

            "shotgun": 6,

            "rifle": 30,

            "knife": None,
        }

        self.reload_timer = 0.0

        self.shoot_cooldown = 0.0

        # =====================================================
        # FACING
        # =====================================================

        self.facing_x = 1.0
        self.facing_y = 0.0

        # Weapon the RL system currently considers appropriate.

        self.rl_target_weapon = "handgun"

        # =====================================================
        # ACTION / ANIMATION STATE
        # =====================================================

        self.shooting = False
        self.shoot_animation_timer = 0.0

        self.melee_animation = False
        self.melee_animation_timer = 0.0

        self.reloading = False

        # =====================================================
        # MOVEMENT ANIMATION STATE
        # =====================================================

        self.moving_left = False
        self.moving_right = False
        self.moving_forward = False
        self.moving_backward = False

        self._last_sprite_x = self.x
        self._last_sprite_y = self.y

        self._sprite_sprinting = False

        # =====================================================
        # SPRITE ANIMATIONS
        #
        # Same animation structure as Player.
        # =====================================================

        # -----------------------------------------------------
        # FEET
        # -----------------------------------------------------

        self.feet_idle_frames = []

        self.feet_walk_frames = []

        self.feet_run_frames = []

        self.feet_strafe_left_frames = []

        self.feet_strafe_right_frames = []

        # -----------------------------------------------------
        # HANDGUN
        # -----------------------------------------------------

        self.handgun_idle_frames = []

        self.handgun_move_frames = []

        self.handgun_shoot_frames = []

        self.handgun_reload_frames = []

        self.handgun_melee_frames = []

        # -----------------------------------------------------
        # SHOTGUN
        # -----------------------------------------------------

        self.shotgun_idle_frames = []

        self.shotgun_move_frames = []

        self.shotgun_shoot_frames = []

        self.shotgun_reload_frames = []

        self.shotgun_melee_frames = []

        # -----------------------------------------------------
        # RIFLE
        # -----------------------------------------------------

        self.rifle_idle_frames = []

        self.rifle_move_frames = []

        self.rifle_shoot_frames = []

        self.rifle_reload_frames = []

        self.rifle_melee_frames = []

        # -----------------------------------------------------
        # KNIFE
        # -----------------------------------------------------

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
        #
        # Same values as Player.
        # =====================================================

        self.animation_speed = 0.20

        self.melee_animation_speed = 0.38

        self.feet_animation_speed = 0.25

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
        # SPRITE PATHS
        #
        # Exactly the same base path as Player.
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
                    "WARNING: RLBot folder not found:",
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

                    # EXACT same size as Player.

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
        # INITIAL FEET STATE
        # =====================================================

        self.feet_animation = (
            self.feet_idle_frames
        )

        self.current_feet_animation = (
            self.feet_idle_frames
        )

        # =====================================================
        # INITIAL WEAPON SPRITE
        # =====================================================

        self._configure_weapon_animation(
            "handgun"
        )

        # =====================================================
        # WARNINGS
        # =====================================================

        if len(self.feet_idle_frames) == 0:

            print(
                "WARNING: RLBot has no feet idle animation!"
            )

        if len(self.handgun_idle_frames) == 0:

            print(
                "WARNING: RLBot has no handgun idle animation!"
            )

        if len(self.shotgun_idle_frames) == 0:

            print(
                "WARNING: RLBot has no shotgun idle animation!"
            )

        if len(self.rifle_idle_frames) == 0:

            print(
                "WARNING: RLBot has no rifle idle animation!"
            )

        if len(self.knife_idle_frames) == 0:

            print(
                "WARNING: RLBot has no knife idle animation!"
            )

        # =====================================================
        # REAL-TIME FALLBACK TIMER
        # =====================================================

        self._last_timer_sync = time.perf_counter()

    # =========================================================
    # CONFIGURE WEAPON SPRITES
    # =========================================================

    def _configure_weapon_animation(self, weapon):

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

            self.weapon_shoot_frames = []

            self.weapon_reload_frames = []

            self.weapon_melee_frames = (
                self.knife_melee_frames
            )

        # =====================================================
        # RESET TO IDLE
        # =====================================================

        self.current_frame = 0

        self.weapon_animation = (
            self.weapon_idle_frames
        )

    # =========================================================
    # TIMER SYNCHRONIZATION
    # =========================================================

    def _sync_real_time_timers(self):

        now = time.perf_counter()

        elapsed = (
            now -
            self._last_timer_sync
        )

        self._last_timer_sync = now

        if elapsed <= 0:
            return

        # -----------------------------------------------------
        # Shoot / melee cooldown
        # -----------------------------------------------------

        self.shoot_cooldown = max(
            0.0,
            self.shoot_cooldown - elapsed
        )

        # -----------------------------------------------------
        # Reload
        # -----------------------------------------------------

        if self.reloading:

            self.reload_timer -= elapsed

            if self.reload_timer <= 0:

                self.reload_timer = 0.0
                self.reloading = False

                if self.weapon != "knife":

                    self.weapon_ammo[
                        self.weapon
                    ] = self.max_ammo()

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

                self.current_frame = 0

        else:

            self.reload_timer = max(
                0.0,
                self.reload_timer - elapsed
            )

        # -----------------------------------------------------
        # Shooting animation
        # -----------------------------------------------------

        if self.shooting:

            self.shoot_animation_timer -= elapsed

            if self.shoot_animation_timer <= 0:

                self.shooting = False
                self.shoot_animation_timer = 0.0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

                self.current_frame = 0

        # -----------------------------------------------------
        # Melee animation
        # -----------------------------------------------------

        if self.melee_animation:

            self.melee_animation_timer -= elapsed

            if self.melee_animation_timer <= 0:

                self.melee_animation = False
                self.melee_animation_timer = 0.0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

                self.current_frame = 0

    # =========================================================
    # CENTER
    # =========================================================

    def center(self):

        return (
            self.x + self.width / 2,
            self.y + self.height / 2,
        )

    # =========================================================
    # DISTANCE
    # =========================================================

    def distance_to(self, x, y):

        cx, cy = self.center()

        return math.hypot(
            x - cx,
            y - cy,
        )

    # =========================================================
    # AIM
    # =========================================================

    def aim_at(self, x, y):

        cx, cy = self.center()

        dx = x - cx
        dy = y - cy

        distance = math.hypot(
            dx,
            dy,
        )

        if distance > 0:

            self.facing_x = (
                dx / distance
            )

            self.facing_y = (
                dy / distance
            )

    # =========================================================
    # SET WEAPON
    # =========================================================

    def set_weapon(self, weapon):

        if not self.alive:
            return False

        if weapon not in self.WEAPON_STATS:
            return False

        if self.weapon == weapon:

            # Still make sure the correct sprite is selected.
            self._configure_weapon_animation(
                weapon
            )

            return False

        self.weapon = weapon

        self.reloading = False
        self.reload_timer = 0.0

        self._configure_weapon_animation(
            weapon
        )

        return True

    # =========================================================
    # EQUIP
    # =========================================================

    def equip(self, weapon):

        return self.set_weapon(weapon)

    # =========================================================
    # CURRENT AMMO
    # =========================================================

    def current_ammo(self):

        self._sync_real_time_timers()

        if self.weapon == "knife":

            return None

        return self.weapon_ammo[
            self.weapon
        ]

    # =========================================================
    # MAX AMMO
    # =========================================================

    def max_ammo(self):

        return self.WEAPON_STATS[
            self.weapon
        ]["max_ammo"]

    # =========================================================
    # EMPTY
    # =========================================================

    def is_empty(self):

        self._sync_real_time_timers()

        if self.weapon == "knife":

            return False

        return self.weapon_ammo[
            self.weapon
        ] <= 0

    # =========================================================
    # SHOOT
    # =========================================================

    def shoot(self):

        self._sync_real_time_timers()

        if not self.alive:
            return False

        if self.weapon == "knife":
            return False

        if self.reloading:
            return False

        if self.reload_timer > 0:
            return False

        if self.shoot_cooldown > 0:
            return False

        if self.weapon_ammo[
            self.weapon
        ] <= 0:
            return False

        # Consume one round.

        self.weapon_ammo[
            self.weapon
        ] -= 1

        self.shoot_cooldown = 0.20

        self.shooting = True

        self.shoot_animation_timer = 0.12

        # =====================================================
        # PLAYER-STYLE SHOOT ANIMATION
        # =====================================================

        if len(
            self.weapon_shoot_frames
        ) > 0:

            self.weapon_animation = (
                self.weapon_shoot_frames
            )

            self.current_frame = 0

        return True

    # =========================================================
    # RELOAD
    # =========================================================

    def reload(self):

        self._sync_real_time_timers()

        if not self.alive:
            return False

        if self.weapon == "knife":
            return False

        if self.reloading:
            return False

        if self.weapon_ammo[
            self.weapon
        ] >= self.max_ammo():
            return False

        self.reloading = True

        self.reload_timer = (
            self.WEAPON_STATS[
                self.weapon
            ]["reload_time"]
        )

        # =====================================================
        # PLAYER-STYLE RELOAD ANIMATION
        # =====================================================

        if len(
            self.weapon_reload_frames
        ) > 0:

            self.weapon_animation = (
                self.weapon_reload_frames
            )

            self.current_frame = 0

        return True

    # =========================================================
    # START RELOAD
    # =========================================================

    def start_reload(self):

        return self.reload()

    # =========================================================
    # MELEE
    # =========================================================

    def melee(self):

        self._sync_real_time_timers()

        if not self.alive:
            return False

        if self.reloading:
            return False

        self.melee_animation = True

        self.melee_animation_timer = 0.20

        self.shoot_cooldown = 0.25

        # =====================================================
        # PLAYER-STYLE MELEE ANIMATION
        # =====================================================

        if len(
            self.weapon_melee_frames
        ) > 0:

            self.weapon_animation = (
                self.weapon_melee_frames
            )

            self.current_frame = 0

        return True

    # =========================================================
    # GET MELEE DAMAGE
    # =========================================================

    def get_melee_damage(self):

        return self.WEAPON_STATS[
            self.weapon
        ]["melee_damage"]

    # =========================================================
    # UPDATE
    # =========================================================

    def update(self, dt):

        if not self.alive:
            return

        # Explicit game-loop update path.

        self._last_timer_sync = (
            time.perf_counter()
        )

        # -----------------------------------------------------
        # Shoot cooldown
        # -----------------------------------------------------

        if self.shoot_cooldown > 0:

            self.shoot_cooldown -= dt

            if self.shoot_cooldown < 0:

                self.shoot_cooldown = 0

        # -----------------------------------------------------
        # Shooting animation timer
        # -----------------------------------------------------

        if self.shooting:

            self.shoot_animation_timer -= dt

            if self.shoot_animation_timer <= 0:

                self.shooting = False

                self.shoot_animation_timer = 0

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

        # -----------------------------------------------------
        # Melee animation timer
        # -----------------------------------------------------

        if self.melee_animation:

            self.melee_animation_timer -= dt

            if self.melee_animation_timer <= 0:

                self.melee_animation = False

                self.melee_animation_timer = 0

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

        # -----------------------------------------------------
        # Reload
        # -----------------------------------------------------

        if self.reloading:

            self.reload_timer -= dt

            if self.reload_timer <= 0:

                self.reload_timer = 0

                self.reloading = False

                if self.weapon != "knife":

                    self.weapon_ammo[
                        self.weapon
                    ] = self.max_ammo()

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

    # =========================================================
    # MOVE
    # =========================================================

    def move(
        self,
        dx,
        dy,
        obstacles=None,
        speed=None,
        sprint=False,
    ):

        if not self.alive:
            return

        # =====================================================
        # OLD STRING-BASED MOVEMENT COMPATIBILITY
        # =====================================================

        if isinstance(dx, str):

            direction = dx

            actual_obstacles = dy

            actual_speed = (
                self.run_speed
                if sprint
                else self.speed
            )

            if direction == "forward":

                dx = self.facing_x
                dy = self.facing_y

            elif direction == "backward":

                dx = -self.facing_x
                dy = -self.facing_y

            elif direction == "left":

                dx = -self.facing_y
                dy = self.facing_x

            elif direction == "right":

                dx = self.facing_y
                dy = -self.facing_x

            else:

                return

            obstacles = actual_obstacles

            speed = actual_speed

        # =====================================================
        # DEFAULTS
        # =====================================================

        if obstacles is None:

            obstacles = []

        if speed is None:

            speed = self.speed

        # =====================================================
        # SPRITE SPRINT STATE
        # =====================================================

        self._sprite_sprinting = (
            sprint
            or speed >= self.run_speed
        )

        # =====================================================
        # NORMALIZE MOVEMENT
        # =====================================================

        length = math.hypot(
            dx,
            dy
        )

        if length == 0:

            self.moving_left = False
            self.moving_right = False
            self.moving_forward = False
            self.moving_backward = False

            return

        normalized_dx = dx / length
        normalized_dy = dy / length

        move_x = (
            normalized_dx *
            speed
        )

        move_y = (
            normalized_dy *
            speed
        )

        # =====================================================
        # DETERMINE MOVEMENT ANIMATION
        #
        # Relative to RLBot's facing direction,
        # exactly like Player.
        # =====================================================

        forward_amount = (
            normalized_dx *
            self.facing_x
            +
            normalized_dy *
            self.facing_y
        )

        left_x = self.facing_y
        left_y = -self.facing_x

        left_amount = (
            normalized_dx *
            left_x
            +
            normalized_dy *
            left_y
        )

        self.moving_left = False
        self.moving_right = False
        self.moving_forward = False
        self.moving_backward = False

        if abs(left_amount) > abs(
            forward_amount
        ):

            if left_amount > 0:

                self.moving_left = True

            else:

                self.moving_right = True

        elif forward_amount > 0:

            self.moving_forward = True

        else:

            self.moving_backward = True

        # =====================================================
        # MOVE X
        # =====================================================

        old_x = self.x

        self.x += move_x

        if self.collides_with_obstacles(
            obstacles
        ):

            self.x = old_x

        # =====================================================
        # MOVE Y
        # =====================================================

        old_y = self.y

        self.y += move_y

        if self.collides_with_obstacles(
            obstacles
        ):

            self.y = old_y

        # =====================================================
        # MAP BOUNDS
        # =====================================================

        self._clamp_to_navigation_bounds()

        # =====================================================
        # UPDATE FEET ANIMATION
        # =====================================================

        self._set_feet_movement_animation()

    # =========================================================
    # SET FEET MOVEMENT ANIMATION
    # =========================================================

    def _set_feet_movement_animation(self):

        # Player does not change feet animation during actions.

        if (
            self.shooting
            or self.reloading
            or self.melee_animation
        ):

            return

        # =====================================================
        # LEFT STRAFE
        # =====================================================

        if (
            self.moving_left
            and not self.moving_right
        ):

            if len(
                self.feet_strafe_left_frames
            ) > 0:

                if (
                    self.current_feet_animation
                    !=
                    self.feet_strafe_left_frames
                ):

                    self.current_feet_animation = (
                        self.feet_strafe_left_frames
                    )

                    self.feet_animation = (
                        self.feet_strafe_left_frames
                    )

                    self.feet_frame = 0

            return

        # =====================================================
        # RIGHT STRAFE
        # =====================================================

        if (
            self.moving_right
            and not self.moving_left
        ):

            if len(
                self.feet_strafe_right_frames
            ) > 0:

                if (
                    self.current_feet_animation
                    !=
                    self.feet_strafe_right_frames
                ):

                    self.current_feet_animation = (
                        self.feet_strafe_right_frames
                    )

                    self.feet_animation = (
                        self.feet_strafe_right_frames
                    )

                    self.feet_frame = 0

            return

        # =====================================================
        # FORWARD / RUN
        # =====================================================

        if self.moving_forward:

            if (
                self._sprite_sprinting
                and
                len(
                    self.feet_run_frames
                ) > 0
            ):

                if (
                    self.current_feet_animation
                    !=
                    self.feet_run_frames
                ):

                    self.current_feet_animation = (
                        self.feet_run_frames
                    )

                    self.feet_animation = (
                        self.feet_run_frames
                    )

                    self.feet_frame = 0

            elif len(
                self.feet_walk_frames
            ) > 0:

                if (
                    self.current_feet_animation
                    !=
                    self.feet_walk_frames
                ):

                    self.current_feet_animation = (
                        self.feet_walk_frames
                    )

                    self.feet_animation = (
                        self.feet_walk_frames
                    )

                    self.feet_frame = 0

            return

        # =====================================================
        # BACKWARD
        # =====================================================

        if self.moving_backward:

            if len(
                self.feet_walk_frames
            ) > 0:

                if (
                    self.current_feet_animation
                    !=
                    self.feet_walk_frames
                ):

                    self.current_feet_animation = (
                        self.feet_walk_frames
                    )

                    self.feet_animation = (
                        self.feet_walk_frames
                    )

                    self.feet_frame = 0

            return

        # =====================================================
        # IDLE
        # =====================================================

        if len(
            self.feet_idle_frames
        ) > 0:

            if (
                self.current_feet_animation
                !=
                self.feet_idle_frames
            ):

                self.current_feet_animation = (
                    self.feet_idle_frames
                )

                self.feet_animation = (
                    self.feet_idle_frames
                )

                self.feet_frame = 0

    # =========================================================
    # UPDATE WEAPON ANIMATION
    #
    # Same animation logic as Player.
    # =========================================================

    def update_weapon_animation(self):

        if len(
            self.weapon_animation
        ) == 0:

            return

        # =====================================================
        # MELEE SPEED
        # =====================================================

        if self.melee_animation:

            self.current_frame += (
                self.melee_animation_speed
            )

        # =====================================================
        # RELOAD SPEED
        # =====================================================

        elif self.reloading:

            self.current_frame += (
                self.reload_animation_speed
            )

        # =====================================================
        # NORMAL SPEED
        # =====================================================

        else:

            self.current_frame += (
                self.animation_speed
            )

        # =====================================================
        # ANIMATION FINISHED
        # =====================================================

        if (
            self.current_frame
            >=
            len(self.weapon_animation)
        ):

            # -------------------------------------------------
            # SHOOT
            # -------------------------------------------------

            if self.shooting:

                self.shooting = False

                self.shoot_animation_timer = 0.0

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

            # -------------------------------------------------
            # RELOAD
            # -------------------------------------------------

            elif self.reloading:

                self.reloading = False

                self.reload_timer = 0.0

                self.current_frame = 0

                if self.weapon != "knife":

                    self.weapon_ammo[
                        self.weapon
                    ] = self.max_ammo()

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

            # -------------------------------------------------
            # MELEE
            # -------------------------------------------------

            elif self.melee_animation:

                self.melee_animation = False

                self.melee_animation_timer = 0.0

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

            # -------------------------------------------------
            # NORMAL
            # -------------------------------------------------

            else:

                self.current_frame = 0

        # =====================================================
        # SAFETY
        # =====================================================

        if len(
            self.weapon_animation
        ) > 0:

            frame_index = int(
                self.current_frame
            )

            if (
                frame_index
                >=
                len(self.weapon_animation)
            ):

                frame_index = 0

            self.original_image = (
                self.weapon_animation[
                    frame_index
                ]
            )

    # =========================================================
    # UPDATE FEET ANIMATION
    #
    # Same animation logic as Player.
    # =========================================================

    def update_feet_animation(self):

        if len(
            self.current_feet_animation
        ) == 0:

            return

        # -----------------------------------------------------
        # Animate feet
        # -----------------------------------------------------

        if not (
            self.shooting
            or self.reloading
            or self.melee_animation
        ):

            self.feet_frame += (
                self.feet_animation_speed
            )

        # -----------------------------------------------------
        # Loop animation
        # -----------------------------------------------------

        if (
            self.feet_frame
            >=
            len(
                self.current_feet_animation
            )
        ):

            self.feet_frame = 0

        # -----------------------------------------------------
        # Safety
        # -----------------------------------------------------

        if len(
            self.current_feet_animation
        ) > 0:

            self.original_feet_image = (
                self.current_feet_animation[
                    int(self.feet_frame)
                    %
                    len(
                        self.current_feet_animation
                    )
                ]
            )

    # =========================================================
    # UPDATE ALL ANIMATIONS
    # =========================================================

    def update_animation(self):

        self.update_weapon_animation()

        self.update_feet_animation()

    # =========================================================
    # OBSTACLE RECTANGLE COMPATIBILITY
    # =========================================================

    @staticmethod
    def _get_obstacle_rect(obstacle):

        # -----------------------------------------------------
        # Real game Obstacle -> obstacle.rect
        # -----------------------------------------------------

        rect = getattr(
            obstacle,
            "rect",
            None
        )

        if rect is not None:

            return (
                float(rect.x),
                float(rect.y),
                float(rect.width),
                float(rect.height),
            )

        # -----------------------------------------------------
        # pygame.Rect-like object
        # -----------------------------------------------------

        if all(
            hasattr(
                obstacle,
                attribute
            )
            for attribute in (
                "x",
                "y",
                "width",
                "height",
            )
        ):

            return (
                float(obstacle.x),
                float(obstacle.y),
                float(obstacle.width),
                float(obstacle.height),
            )

        # -----------------------------------------------------
        # Dictionary representation
        # -----------------------------------------------------

        if isinstance(
            obstacle,
            dict
        ):

            return (
                float(obstacle["x"]),
                float(obstacle["y"]),
                float(obstacle["width"]),
                float(obstacle["height"]),
            )

        raise TypeError(
            "Unsupported obstacle type for RLBot: "
            f"{type(obstacle).__name__}. "
            "Expected an Obstacle with .rect, a pygame.Rect, "
            "a dictionary, or an object with x/y/width/height."
        )

    # =========================================================
    # COLLISION
    # =========================================================

    def collides_with_obstacles(
        self,
        obstacles,
    ):

        left = self.x
        right = self.x + self.width

        top = self.y
        bottom = self.y + self.height

        for obstacle in obstacles:

            (
                ox,
                oy,
                ow,
                oh,
            ) = self._get_obstacle_rect(
                obstacle
            )

            if (
                right > ox
                and left < ox + ow
                and bottom > oy
                and top < oy + oh
            ):

                return True

        return False

    # =========================================================
    # TAKE DAMAGE
    # =========================================================

    def take_damage(self, damage):

        if not self.alive:
            return

        self.health -= damage

        if self.health <= 0:

            self.health = 0

            self.alive = False

            self.reloading = False
            self.reload_timer = 0.0

            self.shooting = False
            self.shoot_animation_timer = 0.0

            self.melee_animation = False
            self.melee_animation_timer = 0.0

            self.shoot_cooldown = 0.0

    # =========================================================
    # HEAL
    # =========================================================

    def heal(self, amount):

        self.health += amount

        if self.health > self.max_health:

            self.health = self.max_health

    # =========================================================
    # AMMO PICKUP
    # =========================================================

    def add_ammo(self):

        if self.weapon == "knife":

            return

        self.weapon_ammo[
            self.weapon
        ] = self.max_ammo()

    # =========================================================
    # TARGET WEAPON
    # =========================================================

    def get_target_weapon(
        self,
        distance,
    ):

        if distance <= self.WEAPON_RANGES["knife"]:

            return "knife"

        if distance <= self.WEAPON_RANGES["shotgun"]:

            return "shotgun"

        if distance <= self.WEAPON_RANGES["handgun"]:

            return "handgun"

        return "rifle"

    # =========================================================
    # CHOOSE COMBAT WEAPON
    # =========================================================

    def choose_combat_weapon(
        self,
        distance,
    ):

        preferred = self.get_target_weapon(
            distance
        )

        self.rl_target_weapon = preferred

        # Knife has no ammunition requirement.

        if preferred == "knife":

            return "knife"

        # Preferred weapon has ammo.

        if self.weapon_ammo[
            preferred
        ] > 0:

            return preferred

        # -----------------------------------------------------
        # Fallback firearm
        # -----------------------------------------------------

        available = []

        for weapon in (
            "shotgun",
            "handgun",
            "rifle",
        ):

            if self.weapon_ammo[
                weapon
            ] > 0:

                available.append(
                    weapon
                )

        if not available:

            return preferred

        available.sort(
            key=lambda weapon:
            abs(
                self.WEAPON_RANGES[
                    weapon
                ]
                - distance
            )
        )

        return available[0]

    # =========================================================
    # TEMPORARY RULE-BASED ACTION
    # =========================================================

    def choose_action(
        self,
        player,
        obstacles,
        health_pickups,
        ammo_pickups,
    ):

        if not self.alive:

            return self.ACTION_IDLE

        bot_x, bot_y = self.center()

        player_x, player_y = player.center()

        dx = player_x - bot_x
        dy = player_y - bot_y

        distance = math.hypot(
            dx,
            dy
        )

        # -----------------------------------------------------
        # LOW HEALTH
        # -----------------------------------------------------

        if self.health <= 10:

            nearest_health = None

            nearest_distance = float(
                "inf"
            )

            for pickup in health_pickups:

                if isinstance(
                    pickup,
                    dict
                ):

                    if pickup.get(
                        "collected",
                        False
                    ):

                        continue

                    px = float(
                        pickup["x"]
                    )

                    py = float(
                        pickup["y"]
                    )

                else:

                    px = float(
                        pickup[0]
                    )

                    py = float(
                        pickup[1]
                    )

                d = math.hypot(
                    px - bot_x,
                    py - bot_y,
                )

                if d < nearest_distance:

                    nearest_distance = d

                    nearest_health = (
                        px,
                        py,
                    )

            if nearest_health is not None:

                if nearest_distance > 35:

                    self.aim_at(
                        nearest_health[0],
                        nearest_health[1],
                    )

                    return (
                        self._movement_action_to_target(
                            nearest_health,
                            bot_x,
                            bot_y,
                        )
                    )

        # -----------------------------------------------------
        # LOW AMMO
        # -----------------------------------------------------

        if (
            self.weapon != "knife"
            and
            self.current_ammo() == 0
        ):

            if self.reload():

                return self.ACTION_RELOAD

        # -----------------------------------------------------
        # TARGET PLAYER
        # -----------------------------------------------------

        self.aim_at(
            player_x,
            player_y,
        )

        # -----------------------------------------------------
        # AUTOMATIC WEAPON SELECTION
        # -----------------------------------------------------

        target_weapon = (
            self.choose_combat_weapon(
                distance
            )
        )

        if self.weapon != target_weapon:

            self.set_weapon(
                target_weapon
            )

        # -----------------------------------------------------
        # MELEE RANGE
        # -----------------------------------------------------

        if distance <= 75:

            return self.ACTION_MELEE

        # -----------------------------------------------------
        # SHOOTING RANGE
        # -----------------------------------------------------

        if distance <= 280:

            if self.weapon != "knife":

                if self.current_ammo() <= 0:

                    self.reload()

                    return self.ACTION_RELOAD

                return self.ACTION_SHOOT

        # -----------------------------------------------------
        # FAR FROM PLAYER
        # -----------------------------------------------------

        if distance > 300:

            return self.ACTION_SPRINT

        if distance > 180:

            return self.ACTION_FORWARD

        # -----------------------------------------------------
        # STRAFE
        # -----------------------------------------------------

        if int(
            self.x + self.y
        ) % 2 == 0:

            return self.ACTION_LEFT

        return self.ACTION_RIGHT

    # =========================================================
    # MOVEMENT ACTION TO TARGET
    # =========================================================

    def _movement_action_to_target(
        self,
        target,
        bot_x,
        bot_y,
    ):

        target_x, target_y = target

        dx = target_x - bot_x
        dy = target_y - bot_y

        if abs(dx) > abs(dy):

            if dx > 0:

                return self.ACTION_RIGHT

            return self.ACTION_LEFT

        if dy > 0:

            return self.ACTION_FORWARD

        return self.ACTION_BACKWARD

    # =========================================================
    # RENDERED-GAME / ENVIRONMENT COMPATIBILITY
    # =========================================================

    @property
    def current_weapon(self):

        return self.weapon

    @property
    def ammo(self):

        return self.current_ammo()

    def get_center(self):

        return self.center()

    def get_rect(self):

        return pygame.Rect(
            int(self.x),
            int(self.y),
            int(self.width),
            int(self.height),
        )

    def get_damage(self):

        if self.weapon == "knife":

            return 0

        return self.WEAPON_STATS[
            self.weapon
        ]["damage"]

    def melee_attack(self):

        return self.melee()

    def can_shoot(self):

        self._sync_real_time_timers()

        if not self.alive:

            return False

        if self.weapon == "knife":

            return False

        if self.reloading:

            return False

        if self.reload_timer > 0:

            return False

        if self.weapon_ammo[
            self.weapon
        ] <= 0:

            return False

        return (
            self.shoot_cooldown <= 0
        )

    # =========================================================
    # NAVIGATION BOUNDS
    # =========================================================

    def set_navigation_bounds(
        self,
        map_left,
        map_top,
        map_right,
        map_bottom,
    ):

        self.map_left = float(
            map_left
        )

        self.map_top = float(
            map_top
        )

        self.map_right = float(
            map_right
        )

        self.map_bottom = float(
            map_bottom
        )

        self.navigation_bounds = (
            self.map_left,
            self.map_top,
            self.map_right,
            self.map_bottom,
        )

        self._clamp_to_navigation_bounds()

    # =========================================================
    # CLAMP TO NAVIGATION BOUNDS
    # =========================================================

    def _clamp_to_navigation_bounds(self):

        if (
            self.map_left is None
            or
            self.map_top is None
            or
            self.map_right is None
            or
            self.map_bottom is None
        ):

            return

        self.x = max(
            self.map_left,
            min(
                self.x,
                self.map_right - self.width,
            ),
        )

        self.y = max(
            self.map_top,
            min(
                self.y,
                self.map_bottom - self.height,
            ),
        )

        # Final hard boundary: never allow the RL bot to leave
        # the visible Pygame screen, even if the Tiled-map
        # navigation bounds extend outside the screen.
        self.clamp_to_screen()


    # =========================================================
    # HARD SCREEN BOUNDARY
    # =========================================================
    # The visible screen is the final authority for actor
    # position. The complete 40x40 RL bot body must remain
    # inside the Pygame window, regardless of navigation bounds.
    # =========================================================

    def clamp_to_screen(self, screen_width=1000, screen_height=700):

        self.x = max(
            0.0,
            min(
                float(self.x),
                float(screen_width - self.width)
            )
        )

        self.y = max(
            0.0,
            min(
                float(self.y),
                float(screen_height - self.height)
            )
        )

    # =========================================================
    # PICKUP POSITION
    # =========================================================

    @staticmethod
    def _get_pickup_position(pickup):

        if isinstance(
            pickup,
            dict
        ):

            return (
                float(pickup["x"]),
                float(pickup["y"]),
            )

        return (
            float(pickup[0]),
            float(pickup[1]),
        )

    # =========================================================
    # PICKUP COLLECTED
    # =========================================================

    @staticmethod
    def _pickup_is_collected(pickup):

        if isinstance(
            pickup,
            dict
        ):

            return bool(
                pickup.get(
                    "collected",
                    False
                )
            )

        return False

    # =========================================================
    # MARK PICKUP COLLECTED
    # =========================================================

    @staticmethod
    def _mark_pickup_collected(pickup):

        if isinstance(
            pickup,
            dict
        ):

            pickup["collected"] = True

    # =========================================================
    # COLLECT PICKUPS
    # =========================================================

    def collect_pickups(
        self,
        health_pickups,
        ammo_pickups,
    ):

        if not self.alive:

            return

        bot_rect = self.get_rect()

        # =====================================================
        # HEALTH
        # =====================================================

        if self.health < self.max_health:

            for pickup in health_pickups:

                if self._pickup_is_collected(
                    pickup
                ):

                    continue

                px, py = (
                    self._get_pickup_position(
                        pickup
                    )
                )

                pickup_rect = pygame.Rect(
                    int(px),
                    int(py),
                    8,
                    8,
                )

                if bot_rect.colliderect(
                    pickup_rect
                ):

                    self.heal(15)

                    self._mark_pickup_collected(
                        pickup
                    )

                    break

        # =====================================================
        # AMMO
        # =====================================================
        #
        # Only collect an ammo pickup when the current weapon
        # actually needs ammo. A full magazine must NOT consume
        # the pickup.
        # =====================================================

        if self.weapon != "knife":

            current_ammo = self.current_ammo()
            maximum_ammo = self.max_ammo()

            if (
                current_ammo is not None
                and maximum_ammo is not None
                and current_ammo < maximum_ammo
            ):

                for pickup in ammo_pickups:

                    if self._pickup_is_collected(
                        pickup
                    ):

                        continue

                    px, py = (
                        self._get_pickup_position(
                            pickup
                        )
                    )

                    pickup_rect = pygame.Rect(
                        int(px),
                        int(py),
                        8,
                        8,
                    )

                    if bot_rect.colliderect(
                        pickup_rect
                    ):

                        before = self.current_ammo()

                        self.add_ammo()

                        after = self.current_ammo()

                        # Mark the pickup only if ammo actually
                        # increased.
                        if (
                            before is not None
                            and after is not None
                            and after > before
                        ):

                            self._mark_pickup_collected(
                                pickup
                            )

                        break

    # =========================================================
    # DRAW
    #
    # IMPORTANT:
    #
    # This now follows Player.draw().
    #
    # No orange rectangle.
    # No artificial facing line.
    # No mouse input.
    #
    # RLBot uses facing_x / facing_y.
    # =========================================================

    def draw(self, screen):

        if not self.alive:

            return

        # =====================================================
        # UPDATE ANIMATIONS
        # =====================================================

        self.update_animation()

        # =====================================================
        # BOT CENTER
        # =====================================================

        center_x = (
            self.x +
            self.width // 2
        )

        center_y = (
            self.y +
            self.height // 2
        )

        # =====================================================
        # AIM / FACING DIRECTION
        #
        # Player uses:
        #
        # mouse -> dx/dy -> atan2
        #
        # RLBot already has its facing vector, so we use that
        # directly.
        # =====================================================

        angle = math.degrees(
            math.atan2(
                -self.facing_y,
                self.facing_x
            )
        )

        # =====================================================
        # FEET LAYER
        #
        # EXACT same rendering structure as Player.
        # =====================================================

        if len(
            self.current_feet_animation
        ) > 0:

            feet_index = (
                int(self.feet_frame)
                %
                len(
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

        # =====================================================
        # WEAPON / UPPER BODY LAYER
        #
        # EXACT same rendering structure as Player.
        # =====================================================

        if len(
            self.weapon_animation
        ) > 0:

            weapon_index = (
                int(self.current_frame)
                %
                len(
                    self.weapon_animation
                )
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