
import os

# =========================================================
# HEADLESS PYGAME SETUP
# =========================================================

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()

if not pygame.display.get_init():
    pygame.display.init()

pygame.display.set_mode((1, 1))

import math
import random

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class HeadlessBot:
    """Lightweight actor used only by the headless DQN environment."""

    WIDTH = 40
    HEIGHT = 40

    WEAPON_STATS = {
        "handgun": {
            "damage": 2,
            "range": 200.0,
            "cooldown": 0.70,
            "magazine": 12,
            "accuracy": 0.88,
        },
        "shotgun": {
            "damage": 5,
            "range": 110.0,
            "cooldown": 1.20,
            "magazine": 6,
            "accuracy": 0.78,
        },
        "rifle": {
            "damage": 1,
            "range": 280.0,
            "cooldown": 0.25,
            "magazine": 30,
            "accuracy": 0.93,
        },
        "knife": {
            "damage": 6,
            "range": 75.0,
            "cooldown": 0.75,
            "magazine": None,
            "accuracy": 1.0,
        },
    }

    WEAPON_RANGES = {
        "knife": 75.0,
        "shotgun": 110.0,
        "handgun": 200.0,
        "rifle": 280.0,
    }

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

        self.speed = 2.3
        self.run_speed = 3.0

        self.health = 30.0
        self.max_health = 30.0

        self.weapon = "handgun"

        self.weapon_ammo = {
            "handgun": 12,
            "shotgun": 6,
            "rifle": 30,
            "knife": None,
        }

        self.reload_timer = 0.0
        self.shoot_cooldown = 0.0

        self.facing_x = 1.0
        self.facing_y = 0.0

        self.rl_target_weapon = "handgun"

    def center(self):
        return (
            self.x + self.WIDTH / 2.0,
            self.y + self.HEIGHT / 2.0,
        )

    def distance_to(self, x, y):
        cx, cy = self.center()
        return math.hypot(x - cx, y - cy)

    def aim_at(self, x, y):
        cx, cy = self.center()
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)

        if distance > 0:
            self.facing_x = dx / distance
            self.facing_y = dy / distance

    def equip(self, weapon):
        if weapon not in self.WEAPON_STATS:
            return False

        if weapon == self.weapon:
            return False

        self.weapon = weapon

        # Magazines persist between weapon switches.
        if weapon != "knife" and self.weapon_ammo[weapon] is None:
            self.weapon_ammo[weapon] = self.WEAPON_STATS[weapon]["magazine"]

        return True

    def current_ammo(self):
        if self.weapon == "knife":
            return None
        return self.weapon_ammo[self.weapon]

    def max_ammo(self):
        if self.weapon == "knife":
            return None
        return self.WEAPON_STATS[self.weapon]["magazine"]

    def is_empty(self):
        if self.weapon == "knife":
            return False
        return self.weapon_ammo[self.weapon] <= 0

    def start_reload(self):
        if self.weapon == "knife":
            return False

        if self.reload_timer > 0:
            return False

        if self.weapon_ammo[self.weapon] >= self.max_ammo():
            return False

        self.reload_timer = 0.28
        return True

    def update_timers(self, dt):
        self.shoot_cooldown = max(
            0.0,
            self.shoot_cooldown - dt,
        )

        if self.reload_timer > 0:
            self.reload_timer -= dt

            if self.reload_timer <= 0:
                self.reload_timer = 0.0

                if self.weapon != "knife":
                    self.weapon_ammo[self.weapon] = self.max_ammo()

    def move(self, dx, dy, speed, obstacles):
        length = math.hypot(dx, dy)

        if length > 0:
            dx /= length
            dy /= length

        old_x = self.x
        old_y = self.y

        self.x += dx * speed
        self.y += dy * speed

        if self.collides_with_obstacles(obstacles):
            self.x = old_x
            self.y = old_y

            # Horizontal slide.
            self.x += dx * speed
            if self.collides_with_obstacles(obstacles):
                self.x = old_x

            # Vertical slide.
            self.y += dy * speed
            if self.collides_with_obstacles(obstacles):
                self.y = old_y

    def collides_with_obstacles(self, obstacles):
        left = self.x
        right = self.x + self.WIDTH
        top = self.y
        bottom = self.y + self.HEIGHT

        for obstacle in obstacles:
            ox = obstacle["x"]
            oy = obstacle["y"]
            ow = obstacle["width"]
            oh = obstacle["height"]

            if (
                right > ox
                and left < ox + ow
                and bottom > oy
                and top < oy + oh
            ):
                return True

        return False

    def can_shoot(self):
        if self.weapon == "knife":
            return False

        if self.reload_timer > 0:
            return False

        if self.weapon_ammo[self.weapon] <= 0:
            return False

        return self.shoot_cooldown <= 0

    def shoot(self):
        if not self.can_shoot():
            return False

        self.weapon_ammo[self.weapon] -= 1
        self.shoot_cooldown = self.WEAPON_STATS[self.weapon]["cooldown"]
        return True


class HeadlessShooterEnv(gym.Env):
    """
    RL25 headless training environment.

    IMPORTANT:
    - 9 actions
    - 28 observations
    - obstacles are loaded directly from the SAME Tiled
      object layer and transformation used by main.py
    - RL Bot 1 starts at the SAME Tiled spawn used by main.py
    - pickup positions are loaded from Tiled instead of
      being hard-coded
    """

    metadata = {"render_modes": []}

    # =====================================================
    # ACTIONS
    # =====================================================

    ACTION_IDLE = 0
    ACTION_FORWARD = 1
    ACTION_BACKWARD = 2
    ACTION_LEFT = 3
    ACTION_RIGHT = 4
    ACTION_SPRINT = 5
    ACTION_SHOOT = 6
    ACTION_RELOAD = 7
    ACTION_MELEE = 8

    ACTION_SIZE = 9
    STATE_SIZE = 28

    # =====================================================
    # MAP -- EXACT VALUES USED BY main.py
    # =====================================================

    TILE_SCALE = 1.638
    MAP_VERTICAL_OFFSET = -30

    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 700

    PLAYER_START = (150.0, 180.0)

    # main.py uses rl_bot_spawn_points[1] for Bot 1.
    RL_BOT_1_SPAWN_INDEX = 1

    def __init__(self, max_steps=1800, seed=None):
        super().__init__()

        self.max_steps = max_steps

        self.action_space = spaces.Discrete(self.ACTION_SIZE)

        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(self.STATE_SIZE,),
            dtype=np.float32,
        )

        self._seed_value = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # -------------------------------------------------
        # Load the real Tiled map.
        # -------------------------------------------------

        self.obstacles = self._load_obstacles()

        # Exact scaled map bounds used by main.py.
        (
            self.MAP_LEFT,
            self.MAP_TOP,
            self.MAP_RIGHT,
            self.MAP_BOTTOM,
        ) = self._get_map_bounds(self.tmx_data)

        print(
            f"Headless Tiled obstacle count: {len(self.obstacles)}"
        )
        print(
            "Headless map bounds: "
            f"({self.MAP_LEFT:.0f}, {self.MAP_TOP:.0f}) -> "
            f"({self.MAP_RIGHT:.0f}, {self.MAP_BOTTOM:.0f})"
        )

        if len(self.obstacles) == 114:
            print("PASS: Loaded all 114 Tiled obstacles.")
        else:
            raise RuntimeError(
                "Tiled obstacle count mismatch: "
                f"expected 114, loaded {len(self.obstacles)}."
            )

        # -------------------------------------------------
        # Load the exact Tiled pickup and RL spawn points.
        # -------------------------------------------------

        self.health_pickup_points = self._load_object_points(
            "health_pickups"
        )

        self.ammo_pickup_points = self._load_object_points(
            "ammo_pickups"
        )

        self.rl_bot_spawn_points = self._load_object_points(
            "rl_bot_spawn"
        )

        if len(self.health_pickup_points) != 3:
            raise RuntimeError(
                "Expected 3 health pickups, found "
                f"{len(self.health_pickup_points)}."
            )

        if len(self.ammo_pickup_points) != 3:
            raise RuntimeError(
                "Expected 3 ammo pickups, found "
                f"{len(self.ammo_pickup_points)}."
            )

        if len(self.rl_bot_spawn_points) < 2:
            raise RuntimeError(
                "Expected at least 2 RL bot spawn points, found "
                f"{len(self.rl_bot_spawn_points)}."
            )

        self.health_pickups = []
        self.ammo_pickups = []

        self.bot = None
        self.player = None

        self.step_count = 0
        self.previous_distance = 0.0

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False

        self.shots_fired = 0
        self.shots_hit = 0
        self.weapon_switches = 0

        self.bot_defeated = False
        self.player_defeated = False

        self._step_weapon_switches = 0

        # One-time distance milestone rewards.
        self.range_milestones = {
            350.0: False,
            280.0: False,
            200.0: False,
            110.0: False,
            75.0: False,
        }

        print("Environment created.")
        print(
            f"Observation space: {self.observation_space}"
        )
        print(
            f"Action space: {self.action_space}"
        )
        print("Environment dimensions validated.")

    # =====================================================
    # SEED
    # =====================================================

    def seed(self, seed=None):
        self._seed_value = seed

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        return [seed]

    # =====================================================
    # TILED MAP PATH
    # =====================================================

    def _get_map_path(self):
        project_root = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
            )
        )

        return os.path.join(
            project_root,
            "assets",
            "maps",
            "Dungeon1.tmx",
        )

    # =====================================================
    # LOAD TILED MAP
    # =====================================================

    def _load_tiled_map(self):
        try:
            import pytmx
        except ImportError as exc:
            raise ImportError(
                "pytmx is required. Install it with: pip install pytmx"
            ) from exc

        map_path = self._get_map_path()

        print("Headless map path:")
        print(map_path)

        if not os.path.exists(map_path):
            raise FileNotFoundError(
                "Dungeon1.tmx was not found at:\n"
                f"{map_path}"
            )

        try:
            tmx_data = pytmx.load_pygame(map_path)
        except Exception as exc:
            raise RuntimeError(
                "Failed to load Dungeon1.tmx.\n"
                f"Map path: {map_path}\n"
                f"Original error: {exc}"
            ) from exc

        return tmx_data

    # =====================================================
    # EXACT main.py MAP OFFSET
    # =====================================================

    def _get_map_offset(self, tmx_data):
        map_width = (
            tmx_data.width *
            tmx_data.tilewidth
        )

        map_height = (
            tmx_data.height *
            tmx_data.tileheight
        )

        enlarged_width = int(
            map_width * self.TILE_SCALE
        )

        enlarged_height = int(
            map_height * self.TILE_SCALE
        )

        offset_x = (
            self.SCREEN_WIDTH -
            enlarged_width
        ) // 2

        offset_y = (
            (
                self.SCREEN_HEIGHT -
                enlarged_height
            ) // 2
        ) + self.MAP_VERTICAL_OFFSET

        return offset_x, offset_y

    # =====================================================
    # EXACT main.py MAP BOUNDS
    # =====================================================

    def _get_map_bounds(self, tmx_data):
        offset_x, offset_y = self._get_map_offset(
            tmx_data
        )

        map_width = (
            tmx_data.width *
            tmx_data.tilewidth
        )

        map_height = (
            tmx_data.height *
            tmx_data.tileheight
        )

        enlarged_width = int(
            map_width * self.TILE_SCALE
        )

        enlarged_height = int(
            map_height * self.TILE_SCALE
        )

        return (
            float(offset_x),
            float(offset_y),
            float(offset_x + enlarged_width),
            float(offset_y + enlarged_height),
        )

    # =====================================================
    # LOAD TILED OBJECT POINTS
    # =====================================================

    def _load_object_points(self, layer_name):
        """
        Load object positions exactly like main.py:

            offset + obj.x * TILE_SCALE
            offset + obj.y * TILE_SCALE

        This fixes the previous RL25 bug where the headless
        environment used raw Tiled coordinates such as
        (801.5, 395) instead of the actual screen coordinates.
        """

        tmx_data = self.tmx_data

        try:
            object_layer = tmx_data.get_layer_by_name(
                layer_name
            )
        except ValueError as exc:
            raise RuntimeError(
                f"Tiled layer '{layer_name}' was not found."
            ) from exc

        offset_x, offset_y = self._get_map_offset(
            tmx_data
        )

        points = []

        for obj in object_layer:
            screen_x = (
                offset_x +
                obj.x * self.TILE_SCALE
            )

            screen_y = (
                offset_y +
                obj.y * self.TILE_SCALE
            )

            points.append(
                (
                    float(screen_x),
                    float(screen_y),
                )
            )

        print(
            f"Tiled {layer_name}: {len(points)} object(s)"
        )

        for index, point in enumerate(points):
            print(
                f"  [{index}] "
                f"({point[0]:.2f}, {point[1]:.2f})"
            )

        return points

    # =====================================================
    # LOAD EXACT TILED OBSTACLES
    # =====================================================

    def _load_obstacles(self):
        """
        This uses the same transformation as main.py:

            offset_x + obj.x * TILE_SCALE
            offset_y + obj.y * TILE_SCALE
            obj.width  * TILE_SCALE
            obj.height * TILE_SCALE

        main.py then passes these through int(...), so the
        headless environment also converts all four values
        to int. This makes the collision rectangles match
        the actual game instead of merely having the same
        obstacle count.
        """

        self.tmx_data = self._load_tiled_map()

        tmx_data = self.tmx_data

        try:
            obstacle_layer = tmx_data.get_layer_by_name(
                "obstacle"
            )
        except ValueError as exc:
            raise RuntimeError(
                "The Tiled 'obstacle' object layer was not found."
            ) from exc

        offset_x, offset_y = self._get_map_offset(
            tmx_data
        )

        obstacles = []

        for obj in obstacle_layer:
            x = int(
                offset_x +
                obj.x * self.TILE_SCALE
            )

            y = int(
                offset_y +
                obj.y * self.TILE_SCALE
            )

            width = int(
                obj.width * self.TILE_SCALE
            )

            height = int(
                obj.height * self.TILE_SCALE
            )

            obstacles.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "width": float(width),
                    "height": float(height),
                }
            )

        if not obstacles:
            raise RuntimeError(
                "The Tiled obstacle layer exists but contains no objects."
            )

        print("Tiled obstacle layer:")
        print(
            f"  Layer name : {obstacle_layer.name}"
        )
        print(
            f"  Objects    : {len(obstacles)}"
        )
        print(
            f"  Scale      : {self.TILE_SCALE}"
        )
        print(
            f"  Offset     : ({offset_x}, {offset_y})"
        )

        return obstacles

    # =====================================================
    # RESET
    # =====================================================

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.step_count = 0

        # -------------------------------------------------
        # EXACT main.py RL Bot 1 spawn:
        #
        # rl_bot_1_spawn_point = rl_bot_spawn_points[1]
        # -------------------------------------------------

        bot_spawn = self.rl_bot_spawn_points[
            self.RL_BOT_1_SPAWN_INDEX
        ]

        self.bot = HeadlessBot(
            bot_spawn[0],
            bot_spawn[1],
        )

        # main.py Player() starts at (150, 180).
        self.player = HeadlessBot(
            self.PLAYER_START[0],
            self.PLAYER_START[1],
        )

        self.health_pickups = [
            {
                "x": point[0],
                "y": point[1],
                "collected": False,
            }
            for point in self.health_pickup_points
        ]

        self.ammo_pickups = [
            {
                "x": point[0],
                "y": point[1],
                "collected": False,
            }
            for point in self.ammo_pickup_points
        ]

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False

        self.shots_fired = 0
        self.shots_hit = 0
        self.weapon_switches = 0

        self.bot_defeated = False
        self.player_defeated = False

        self._step_weapon_switches = 0

        self.range_milestones = {
            350.0: False,
            280.0: False,
            200.0: False,
            110.0: False,
            75.0: False,
        }

        self.previous_distance = (
            self._distance_bot_player()
        )

        observation = self._get_observation()

        info = {
            "damage_dealt": 0.0,
            "damage_taken": 0.0,
            "shots_fired": 0,
            "shots_hit": 0,
            "weapon_switches": 0,
            "distance": float(self.previous_distance),
            "line_of_sight": bool(self._line_of_sight()),
            "weapon": self.bot.weapon,
        }

        return observation, info

    # =====================================================
    # STEP
    # =====================================================

    def step(self, action):
        action = int(action)

        if not self.action_space.contains(action):
            raise ValueError(f"Invalid action: {action}")

        self.step_count += 1

        # One RL step = 0.1 second.
        dt = 0.1

        self.bot.update_timers(dt)
        self.player.update_timers(dt)

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0
        self.last_shot_fired = False
        self.last_shot_hit = False

        self._execute_bot_action(action)

        self._update_scripted_player()

        reward = 0.0

        # -------------------------------------------------
        # PICKUPS
        # -------------------------------------------------

        reward += self._handle_pickups()

        # -------------------------------------------------
        # COMBAT
        # -------------------------------------------------

        reward += 3.0 * self.last_damage_dealt

        if self.last_shot_hit:
            reward += 1.0

        if self.last_shot_fired and not self.last_shot_hit:
            reward -= 0.05

        reward -= 0.75 * self.last_damage_taken

        # -------------------------------------------------
        # DISTANCE SHAPING
        #
        # Previous version used only 0.01 * distance change.
        # That was too weak compared with the step penalty.
        #
        # This gives the DQN a clear signal:
        # reducing the distance is useful.
        # -------------------------------------------------

        current_distance = self._distance_bot_player()

        distance_change = (
            self.previous_distance -
            current_distance
        )

        reward += 0.04 * float(
            np.clip(
                distance_change,
                -5.0,
                5.0,
            )
        )

        self.previous_distance = current_distance

        # -------------------------------------------------
        # ONE-TIME RANGE MILESTONES
        #
        # These are not repeated, so the bot cannot farm
        # reward by crossing the same range boundary forever.
        # -------------------------------------------------

        milestone_rewards = {
            350.0: 1.0,
            280.0: 2.0,
            200.0: 3.0,
            110.0: 4.0,
            75.0: 5.0,
        }

        for range_limit, bonus in milestone_rewards.items():
            if (
                current_distance <= range_limit
                and not self.range_milestones[range_limit]
            ):
                self.range_milestones[range_limit] = True
                reward += bonus

        # -------------------------------------------------
        # ENGAGEMENT REWARD
        # -------------------------------------------------

        if (
            current_distance <= 280.0
            and self._line_of_sight()
        ):
            reward += 0.05

        # -------------------------------------------------
        # TOO FAR PENALTY
        # -------------------------------------------------

        if current_distance > 350.0:
            reward -= 0.03

        # -------------------------------------------------
        # STEP COST
        # -------------------------------------------------

        reward -= 0.01

        # -------------------------------------------------
        # WEAPON SWITCH COST
        # -------------------------------------------------

        reward -= (
            0.01 *
            self._step_weapon_switches
        )

        terminated = False

        # -------------------------------------------------
        # PLAYER DEFEATED
        # -------------------------------------------------

        if self.player.health <= 0:
            self.player.health = 0.0
            self.player_defeated = True

            reward += 100.0
            terminated = True

        # -------------------------------------------------
        # BOT DEFEATED
        # -------------------------------------------------

        elif self.bot.health <= 0:
            self.bot.health = 0.0
            self.bot_defeated = True

            reward -= 100.0
            terminated = True

        truncated = (
            self.step_count >= self.max_steps
        )

        observation = self._get_observation()

        info = {
            "damage_dealt": float(
                self.last_damage_dealt
            ),
            "damage_taken": float(
                self.last_damage_taken
            ),
            "shots_fired": int(
                self.shots_fired
            ),
            "shots_hit": int(
                self.shots_hit
            ),
            "weapon_switches": int(
                self.weapon_switches
            ),
            "distance": float(
                current_distance
            ),
            "line_of_sight": bool(
                self._line_of_sight()
            ),
            "weapon": self.bot.weapon,
            "action": int(action),
        }

        return (
            observation,
            float(reward),
            terminated,
            truncated,
            info,
        )

    # =====================================================
    # BOT ACTION
    # =====================================================

    def _execute_bot_action(self, action):
        self._step_weapon_switches = 0

        player_x, player_y = self.player.center()
        bot_x, bot_y = self.bot.center()

        dx = player_x - bot_x
        dy = player_y - bot_y

        distance = math.hypot(dx, dy)

        # The RL bot always faces the player, matching the
        # task-oriented facing used by the rendered RL system.
        if distance > 0:
            self.bot.facing_x = dx / distance
            self.bot.facing_y = dy / distance

        if action == self.ACTION_FORWARD:
            self.bot.move(
                self.bot.facing_x,
                self.bot.facing_y,
                self.bot.speed,
                self.obstacles,
            )

        elif action == self.ACTION_BACKWARD:
            self.bot.move(
                -self.bot.facing_x,
                -self.bot.facing_y,
                self.bot.speed,
                self.obstacles,
            )

        elif action == self.ACTION_LEFT:
            self.bot.move(
                -self.bot.facing_y,
                self.bot.facing_x,
                self.bot.speed,
                self.obstacles,
            )

        elif action == self.ACTION_RIGHT:
            self.bot.move(
                self.bot.facing_y,
                -self.bot.facing_x,
                self.bot.speed,
                self.obstacles,
            )

        elif action == self.ACTION_SPRINT:
            self.bot.move(
                self.bot.facing_x,
                self.bot.facing_y,
                self.bot.run_speed,
                self.obstacles,
            )

        elif action == self.ACTION_SHOOT:
            self._select_combat_weapon(
                distance,
                force_melee=False,
            )
            self._bot_shoot()

        elif action == self.ACTION_RELOAD:
            self.bot.start_reload()

        elif action == self.ACTION_MELEE:
            self._select_combat_weapon(
                distance,
                force_melee=True,
            )
            self._bot_melee()

        self._clamp_bot()

    # =====================================================
    # WEAPON SELECTION
    # =====================================================

    def _select_combat_weapon(
        self,
        distance,
        force_melee=False,
    ):
        # -------------------------------------------------
        # MELEE
        # -------------------------------------------------

        if force_melee:
            preferred = "knife"

        # -------------------------------------------------
        # SHOOT
        #
        # IMPORTANT:
        # SHOOT can NEVER select knife.
        # -------------------------------------------------

        elif distance <= 110.0:
            preferred = "shotgun"

        elif distance <= 200.0:
            preferred = "handgun"

        else:
            preferred = "rifle"

        # -------------------------------------------------
        # KNIFE
        # -------------------------------------------------

        if preferred == "knife":
            if self.bot.weapon != "knife":
                if self.bot.equip("knife"):
                    self.weapon_switches += 1
                    self._step_weapon_switches += 1

            self.bot.rl_target_weapon = "knife"
            return

        # -------------------------------------------------
        # FIREARM FALLBACK
        # -------------------------------------------------

        if self.bot.weapon_ammo[preferred] <= 0:
            alternatives = [
                "shotgun",
                "handgun",
                "rifle",
            ]

            usable = [
                weapon
                for weapon in alternatives
                if self.bot.weapon_ammo[weapon] > 0
            ]

            if usable:
                usable.sort(
                    key=lambda weapon: abs(
                        self.bot.WEAPON_RANGES[weapon]
                        - distance
                    )
                )
                preferred = usable[0]
            else:
                # No firearm ammo. Keep current weapon.
                # The learned RELOAD action must restore it.
                self.bot.rl_target_weapon = preferred
                return

        # -------------------------------------------------
        # EQUIP FIREARM
        # -------------------------------------------------

        if self.bot.weapon != preferred:
            if self.bot.equip(preferred):
                self.weapon_switches += 1
                self._step_weapon_switches += 1

        self.bot.rl_target_weapon = preferred

    # =====================================================
    # BOT SHOOT
    # =====================================================

    def _bot_shoot(self):
        self.last_shot_fired = False
        self.last_shot_hit = False

        # Safety: SHOOT must always be a firearm.
        if self.bot.weapon == "knife":
            player_x, player_y = self.player.center()
            bot_x, bot_y = self.bot.center()

            distance = math.hypot(
                player_x - bot_x,
                player_y - bot_y,
            )

            self._select_combat_weapon(
                distance,
                force_melee=False,
            )

        if self.bot.weapon == "knife":
            return

        # Empty firearm -> start reload rather than pretending
        # a shot occurred.
        if not self.bot.can_shoot():
            if self.bot.is_empty():
                self.bot.start_reload()
            return

        bot_x, bot_y = self.bot.center()
        player_x, player_y = self.player.center()

        dx = player_x - bot_x
        dy = player_y - bot_y

        distance = math.hypot(dx, dy)

        stats = self.bot.WEAPON_STATS[self.bot.weapon]

        # -------------------------------------------------
        # RANGE
        # -------------------------------------------------

        if distance > stats["range"]:
            return

        # -------------------------------------------------
        # LINE OF SIGHT
        #
        # This matches the actual game concept:
        # walls stop bullets.
        # -------------------------------------------------

        if not self._line_of_sight():
            return

        # -------------------------------------------------
        # FIRE
        # -------------------------------------------------

        if not self.bot.shoot():
            return

        self.last_shot_fired = True
        self.shots_fired += 1

        # Aim is exact in the headless simulator.
        self.bot.aim_at(
            player_x,
            player_y,
        )

        # Weapon-specific accuracy gives realistic misses
        # without making aiming itself impossible to learn.
        if random.random() > stats["accuracy"]:
            return

        damage = stats["damage"]

        self.player.health -= damage
        self.player.health = max(
            0.0,
            self.player.health,
        )

        self.last_damage_dealt = damage
        self.last_shot_hit = True
        self.shots_hit += 1

    # =====================================================
    # BOT MELEE
    # =====================================================

    def _bot_melee(self):
        if self.bot.weapon != "knife":
            return

        if self.bot.shoot_cooldown > 0:
            return

        bot_x, bot_y = self.bot.center()
        player_x, player_y = self.player.center()

        distance = math.hypot(
            player_x - bot_x,
            player_y - bot_y,
        )

        if distance > 75.0:
            return

        self.bot.shoot_cooldown = (
            self.bot.WEAPON_STATS["knife"]["cooldown"]
        )

        damage = self.bot.WEAPON_STATS["knife"]["damage"]

        self.player.health -= damage
        self.player.health = max(
            0.0,
            self.player.health,
        )

        self.last_damage_dealt = damage

    # =====================================================
    # SCRIPTED PLAYER
    # =====================================================

    def _update_scripted_player(self):
        """
        Simple deterministic opponent.

        The previous controller could remain in a long
        220 px strafing loop, which made it unnecessarily
        difficult for the RL bot to reach combat.

        New behavior:
        - > 240 px: approach the bot
        - 140-240 px: strafe while still making a small
          closing movement
        - <= 140 px: strafe around the bot

        This creates a reliable combat encounter while still
        keeping the opponent dynamic.
        """

        if self.player.health <= 0:
            return

        bot_x, bot_y = self.bot.center()
        player_x, player_y = self.player.center()

        dx = bot_x - player_x
        dy = bot_y - player_y

        distance = math.hypot(dx, dy)

        if distance <= 0:
            return

        self.player.aim_at(
            bot_x,
            bot_y,
        )

        if distance > 240.0:
            # Close directly.
            self.player.move(
                dx,
                dy,
                1.35,
                self.obstacles,
            )

        elif distance > 140.0:
            # Close while strafing.
            self.player.move(
                dx - dy * 0.35,
                dy + dx * 0.35,
                1.15,
                self.obstacles,
            )

        else:
            # Close-range strafing.
            self.player.move(
                -dy,
                dx,
                1.0,
                self.obstacles,
            )

        if (
            distance <= 200.0
            and self._player_line_of_sight()
            and self.player.shoot_cooldown <= 0
        ):
            self._player_shoot()

        self._clamp_player()

    # =====================================================
    # SCRIPTED PLAYER SHOOT
    # =====================================================

    def _player_shoot(self):
        weapon = self.player.weapon

        if weapon == "knife":
            self.player.equip("handgun")
            weapon = "handgun"

        if self.player.is_empty():
            self.player.start_reload()
            return

        if not self.player.can_shoot():
            return

        player_x, player_y = self.player.center()
        bot_x, bot_y = self.bot.center()

        distance = math.hypot(
            bot_x - player_x,
            bot_y - player_y,
        )

        stats = self.player.WEAPON_STATS[weapon]

        if distance > stats["range"]:
            return

        if not self._player_line_of_sight():
            return

        self.player.aim_at(
            bot_x,
            bot_y,
        )

        if not self.player.shoot():
            return

        # Keep the scripted opponent imperfect.
        if random.random() > 0.72:
            return

        damage = stats["damage"]

        self.bot.health -= damage
        self.bot.health = max(
            0.0,
            self.bot.health,
        )

        self.last_damage_taken = damage

    # =====================================================
    # PICKUPS
    # =====================================================

    def _handle_pickups(self):
        reward = 0.0

        bot_rect = (
            self.bot.x,
            self.bot.y,
            self.bot.WIDTH,
            self.bot.HEIGHT,
        )

        # Main.py uses an 8x8 pickup collision area scaled
        # by TILE_SCALE, regardless of the Tiled object's
        # 12x12 object dimensions.
        pickup_size = max(
            1,
            int(8 * self.TILE_SCALE),
        )

        # -------------------------------------------------
        # HEALTH
        # -------------------------------------------------

        if self.bot.health < self.bot.max_health:
            for pickup in list(self.health_pickups):
                pickup_rect = (
                    pickup["x"],
                    pickup["y"],
                    pickup_size,
                    pickup_size,
                )

                if self._rects_overlap(
                    bot_rect,
                    pickup_rect,
                ):
                    old_health = self.bot.health

                    self.bot.health = min(
                        self.bot.max_health,
                        self.bot.health + 15.0,
                    )

                    self.health_pickups.remove(pickup)

                    # Small reward proportional to actual
                    # game pickup value.
                    if self.bot.health > old_health:
                        reward += 2.0

                    break

        # -------------------------------------------------
        # AMMO
        # -------------------------------------------------

        if self.bot.weapon != "knife":
            for pickup in list(self.ammo_pickups):
                pickup_rect = (
                    pickup["x"],
                    pickup["y"],
                    pickup_size,
                    pickup_size,
                )

                if self._rects_overlap(
                    bot_rect,
                    pickup_rect,
                ):
                    self.bot.weapon_ammo[
                        self.bot.weapon
                    ] = self.bot.max_ammo()

                    self.ammo_pickups.remove(pickup)

                    reward += 1.0
                    break

        return reward

    @staticmethod
    def _rects_overlap(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b

        return (
            ax < bx + bw
            and ax + aw > bx
            and ay < by + bh
            and ay + ah > by
        )

    # =====================================================
    # OBSERVATION
    # =====================================================

    def _get_observation(self):
        bot_x, bot_y = self.bot.center()
        player_x, player_y = self.player.center()

        dx = player_x - bot_x
        dy = player_y - bot_y

        distance = math.hypot(dx, dy)

        obs = []

        # -------------------------------------------------
        # 0-15 BASIC STATE
        # -------------------------------------------------

        obs.append(
            self._normalize_position_x(bot_x)
        )

        obs.append(
            self._normalize_position_y(bot_y)
        )

        obs.append(
            np.clip(
                dx / 500.0,
                -1.0,
                1.0,
            )
        )

        obs.append(
            np.clip(
                dy / 500.0,
                -1.0,
                1.0,
            )
        )

        obs.append(
            np.clip(
                distance / 500.0,
                0.0,
                1.0,
            )
        )

        obs.append(
            np.clip(
                self.bot.health / self.bot.max_health,
                0.0,
                1.0,
            )
        )

        obs.append(
            np.clip(
                self.player.health / self.player.max_health,
                0.0,
                1.0,
            )
        )

        if self.bot.weapon == "knife":
            obs.append(1.0)
        else:
            max_ammo = self.bot.max_ammo()

            obs.append(
                np.clip(
                    self.bot.current_ammo() / max_ammo,
                    0.0,
                    1.0,
                )
            )

        weapon_encoding = {
            "handgun": -1.0,
            "shotgun": -0.33,
            "rifle": 0.33,
            "knife": 1.0,
        }

        obs.append(
            weapon_encoding.get(
                self.bot.weapon,
                -1.0,
            )
        )

        obs.append(
            np.clip(
                self.bot.facing_x,
                -1.0,
                1.0,
            )
        )

        obs.append(
            np.clip(
                self.bot.facing_y,
                -1.0,
                1.0,
            )
        )

        obs.append(
            1.0
            if self._line_of_sight()
            else 0.0
        )

        health_distance = (
            self._nearest_pickup_distance(
                self.health_pickups
            )
        )

        obs.append(
            np.clip(
                health_distance / 500.0,
                0.0,
                1.0,
            )
        )

        ammo_distance = (
            self._nearest_pickup_distance(
                self.ammo_pickups
            )
        )

        obs.append(
            np.clip(
                ammo_distance / 500.0,
                0.0,
                1.0,
            )
        )

        obs.append(
            1.0
            if self.health_pickups
            else 0.0
        )

        obs.append(
            1.0
            if self.ammo_pickups
            else 0.0
        )

        # -------------------------------------------------
        # 16-23 OBSTACLE SENSORS
        # -------------------------------------------------

        directions = [
            (1.0, 0.0),
            (-1.0, 0.0),
            (0.0, 1.0),
            (0.0, -1.0),
            (0.70710678, 0.70710678),
            (-0.70710678, 0.70710678),
            (0.70710678, -0.70710678),
            (-0.70710678, -0.70710678),
        ]

        for direction_x, direction_y in directions:
            ray_distance = self._ray_distance(
                bot_x,
                bot_y,
                direction_x,
                direction_y,
                max_distance=200.0,
            )

            obs.append(
                np.clip(
                    ray_distance / 200.0,
                    0.0,
                    1.0,
                )
            )

        # -------------------------------------------------
        # 24-27 COMBAT RANGE FLAGS
        # -------------------------------------------------

        obs.append(
            1.0 if distance <= 75.0 else 0.0
        )

        obs.append(
            1.0 if distance <= 110.0 else 0.0
        )

        obs.append(
            1.0 if distance <= 200.0 else 0.0
        )

        obs.append(
            1.0 if distance <= 280.0 else 0.0
        )

        if len(obs) != self.STATE_SIZE:
            raise RuntimeError(
                f"Observation has {len(obs)} values, "
                f"expected {self.STATE_SIZE}."
            )

        return np.asarray(
            obs,
            dtype=np.float32,
        )

    # =====================================================
    # RAY DISTANCE
    # =====================================================

    def _ray_distance(
        self,
        start_x,
        start_y,
        direction_x,
        direction_y,
        max_distance,
    ):
        step = 5.0
        distance = 0.0

        while distance <= max_distance:
            x = start_x + direction_x * distance
            y = start_y + direction_y * distance

            if self._point_inside_obstacle(x, y):
                return distance

            distance += step

        return max_distance

    # =====================================================
    # OBSTACLE TEST
    # =====================================================

    def _point_inside_obstacle(self, x, y):
        for obstacle in self.obstacles:
            if (
                obstacle["x"] <= x <= obstacle["x"] + obstacle["width"]
                and
                obstacle["y"] <= y <= obstacle["y"] + obstacle["height"]
            ):
                return True

        return False

    # =====================================================
    # LINE OF SIGHT
    # =====================================================

    def _line_of_sight(self):
        bot_x, bot_y = self.bot.center()
        player_x, player_y = self.player.center()

        return self._has_line_of_sight(
            bot_x,
            bot_y,
            player_x,
            player_y,
        )

    def _player_line_of_sight(self):
        player_x, player_y = self.player.center()
        bot_x, bot_y = self.bot.center()

        return self._has_line_of_sight(
            player_x,
            player_y,
            bot_x,
            bot_y,
        )

    def _has_line_of_sight(
        self,
        x1,
        y1,
        x2,
        y2,
    ):
        distance = math.hypot(
            x2 - x1,
            y2 - y1,
        )

        if distance <= 0:
            return True

        steps = max(
            1,
            int(distance / 5),
        )

        for i in range(1, steps):
            t = i / steps

            x = (
                x1 +
                (x2 - x1) * t
            )

            y = (
                y1 +
                (y2 - y1) * t
            )

            if self._point_inside_obstacle(x, y):
                return False

        return True

    # =====================================================
    # DISTANCE
    # =====================================================

    def _distance_bot_player(self):
        bot_x, bot_y = self.bot.center()
        player_x, player_y = self.player.center()

        return math.hypot(
            player_x - bot_x,
            player_y - bot_y,
        )

    # =====================================================
    # PICKUP DISTANCE
    # =====================================================

    def _nearest_pickup_distance(self, pickups):
        if not pickups:
            return 500.0

        bot_x, bot_y = self.bot.center()

        distances = []

        for pickup in pickups:
            pickup_x = pickup["x"]
            pickup_y = pickup["y"]

            distances.append(
                math.hypot(
                    bot_x - pickup_x,
                    bot_y - pickup_y,
                )
            )

        return min(distances)

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize_position_x(self, x):
        normalized = (
            (
                x - self.MAP_LEFT
            )
            /
            (
                self.MAP_RIGHT -
                self.MAP_LEFT
            )
        )

        # observation_space is [-1, 1], so map the
        # normalized [0, 1] coordinate into [-1, 1].
        return float(
            np.clip(
                normalized * 2.0 - 1.0,
                -1.0,
                1.0,
            )
        )

    def _normalize_position_y(self, y):
        normalized = (
            (
                y - self.MAP_TOP
            )
            /
            (
                self.MAP_BOTTOM -
                self.MAP_TOP
            )
        )

        return float(
            np.clip(
                normalized * 2.0 - 1.0,
                -1.0,
                1.0,
            )
        )

    # =====================================================
    # MAP CLAMP
    # =====================================================

    def _clamp_bot(self):
        self.bot.x = float(
            np.clip(
                self.bot.x,
                self.MAP_LEFT,
                self.MAP_RIGHT - self.bot.WIDTH,
            )
        )

        self.bot.y = float(
            np.clip(
                self.bot.y,
                self.MAP_TOP,
                self.MAP_BOTTOM - self.bot.HEIGHT,
            )
        )

    def _clamp_player(self):
        self.player.x = float(
            np.clip(
                self.player.x,
                self.MAP_LEFT,
                self.MAP_RIGHT - self.player.WIDTH,
            )
        )

        self.player.y = float(
            np.clip(
                self.player.y,
                self.MAP_TOP,
                self.MAP_BOTTOM - self.player.HEIGHT,
            )
        )

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):
        pass
