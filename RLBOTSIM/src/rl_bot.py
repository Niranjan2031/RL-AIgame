import math


class RLBot:

    WIDTH = 40
    HEIGHT = 40

    # =========================================================
    # RL25 ACTIONS
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
    # They are NOT part of the RL25 action space.
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

    # RL25 deterministic weapon-selection ranges.

    WEAPON_RANGES = {
        "knife": 75,
        "shotgun": 110,
        "handgun": 200,
        "rifle": 280,
    }

    def __init__(self, x, y):

        self.x = float(x)
        self.y = float(y)

        self.width = self.WIDTH
        self.height = self.HEIGHT

        self.speed = 2.3
        self.run_speed = 3.0

        self.health = 30
        self.max_health = 30

        # -----------------------------------------------------
        # Weapon
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Facing
        # -----------------------------------------------------

        self.facing_x = 1.0
        self.facing_y = 0.0

        # Weapon the RL system currently considers appropriate.

        self.rl_target_weapon = "handgun"

        # -----------------------------------------------------
        # Animation state
        # -----------------------------------------------------

        self.shooting = False
        self.shoot_animation_timer = 0.0

        self.melee_animation = False
        self.melee_animation_timer = 0.0

        self.reloading = False

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

            self.facing_x = dx / distance
            self.facing_y = dy / distance

    # =========================================================
    # SET WEAPON
    # =========================================================

    def set_weapon(self, weapon):

        if weapon not in self.WEAPON_STATS:

            return False

        if self.weapon == weapon:

            return False

        self.weapon = weapon

        self.reloading = False
        self.reload_timer = 0.0

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

        if self.weapon == "knife":

            return None

        return self.weapon_ammo[self.weapon]

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

        if self.weapon == "knife":

            return False

        return self.weapon_ammo[
            self.weapon
        ] <= 0

    # =========================================================
    # SHOOT
    # =========================================================

    def shoot(self):

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

        return True

    # =========================================================
    # RELOAD
    # =========================================================

    def reload(self):

        if self.weapon == "knife":

            return False

        if self.reloading:

            return False

        if self.weapon_ammo[
            self.weapon
        ] >= self.max_ammo():

            return False

        self.reloading = True

        self.reload_timer = self.WEAPON_STATS[
            self.weapon
        ]["reload_time"]

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

        if self.reloading:

            return False

        self.melee_animation = True

        self.melee_animation_timer = 0.20

        self.shoot_cooldown = 0.25

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

        # -----------------------------------------------------
        # Shoot cooldown
        # -----------------------------------------------------

        if self.shoot_cooldown > 0:

            self.shoot_cooldown -= dt

            if self.shoot_cooldown < 0:

                self.shoot_cooldown = 0

        # -----------------------------------------------------
        # Shooting animation
        # -----------------------------------------------------

        if self.shooting:

            self.shoot_animation_timer -= dt

            if self.shoot_animation_timer <= 0:

                self.shooting = False

                self.shoot_animation_timer = 0

        # -----------------------------------------------------
        # Melee animation
        # -----------------------------------------------------

        if self.melee_animation:

            self.melee_animation_timer -= dt

            if self.melee_animation_timer <= 0:

                self.melee_animation = False

                self.melee_animation_timer = 0

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

    # =========================================================
    # MOVE
    # =========================================================

    def move(
        self,
        dx,
        dy,
        obstacles,
        speed=None,
    ):

        if speed is None:

            speed = self.speed

        length = math.hypot(
            dx,
            dy,
        )

        if length == 0:

            return

        dx /= length
        dy /= length

        move_x = dx * speed
        move_y = dy * speed

        # -----------------------------------------------------
        # Horizontal movement
        # -----------------------------------------------------

        old_x = self.x

        self.x += move_x

        if self.collides_with_obstacles(
            obstacles
        ):

            self.x = old_x

        # -----------------------------------------------------
        # Vertical movement
        # -----------------------------------------------------

        old_y = self.y

        self.y += move_y

        if self.collides_with_obstacles(
            obstacles
        ):

            self.y = old_y

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

            ox = obstacle.x
            oy = obstacle.y
            ow = obstacle.width
            oh = obstacle.height

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

        self.health -= damage

        if self.health < 0:

            self.health = 0

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

        # Give the currently equipped firearm
        # a full magazine.

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

        # If preferred weapon has ammo, use it.

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
    #
    # This is still used by main.py for now.
    #
    # The DQN is NOT loaded into main.py yet.
    #
    # RL25 action space:
    #
    # 0 IDLE
    # 1 FORWARD
    # 2 BACKWARD
    # 3 LEFT
    # 4 RIGHT
    # 5 SPRINT
    # 6 SHOOT
    # 7 RELOAD
    # 8 MELEE
    #
    # Weapon selection is handled automatically.
    # =========================================================

    def choose_action(
        self,
        player,
        obstacles,
        health_pickups,
        ammo_pickups,
    ):

        bot_x, bot_y = self.center()

        player_x, player_y = player.center()

        dx = player_x - bot_x
        dy = player_y - bot_y

        distance = math.hypot(
            dx,
            dy,
        )

        # -----------------------------------------------------
        # LOW HEALTH
        # -----------------------------------------------------

        if self.health <= 10:

            nearest_health = None
            nearest_distance = float("inf")

            for pickup in health_pickups:

                px, py = pickup

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

                    return self._movement_action_to_target(
                        nearest_health,
                        bot_x,
                        bot_y,
                    )

        # -----------------------------------------------------
        # LOW AMMO
        # -----------------------------------------------------

        if (
            self.weapon != "knife"
            and self.current_ammo() == 0
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
    # DRAW
    # =========================================================

    def draw(self, screen):

        import pygame

        rect = pygame.Rect(
            int(self.x),
            int(self.y),
            self.width,
            self.height,
        )

        pygame.draw.rect(
            screen,
            (255, 165, 0),
            rect,
        )

        # -----------------------------------------------------
        # Facing indicator
        # -----------------------------------------------------

        cx, cy = self.center()

        end_x = (
            cx
            + self.facing_x * 25
        )

        end_y = (
            cy
            + self.facing_y * 25
        )

        pygame.draw.line(
            screen,
            (255, 255, 255),
            (int(cx), int(cy)),
            (int(end_x), int(end_y)),
            3,
        )

        # -----------------------------------------------------
        # Health bar
        # -----------------------------------------------------

        bar_width = self.width

        health_ratio = (
            self.health
            / self.max_health
        )

        health_ratio = max(
            0,
            min(1, health_ratio),
        )

        background = pygame.Rect(
            int(self.x),
            int(self.y - 8),
            bar_width,
            5,
        )

        foreground = pygame.Rect(
            int(self.x),
            int(self.y - 8),
            int(
                bar_width
                * health_ratio
            ),
            5,
        )

        pygame.draw.rect(
            screen,
            (60, 60, 60),
            background,
        )

        pygame.draw.rect(
            screen,
            (0, 220, 0),
            foreground,
        )