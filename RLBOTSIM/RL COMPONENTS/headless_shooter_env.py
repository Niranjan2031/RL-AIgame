
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

import heapq
import math
import random

import gymnasium as gym
import numpy as np
from gymnasium import spaces


# =========================================================
# LIGHTWEIGHT RL ACTOR
# =========================================================

class HeadlessBot:
    """Lightweight actor used by the RL bot and scripted enemies."""

    WIDTH = 40
    HEIGHT = 40

    # Final shared combat contract used by training/deployment.
    # Damage is intentionally reduced so the RL bot has meaningful
    # time to disengage and navigate to pickups.
    WEAPON_STATS = {
        "handgun": {
            "damage": 1,
            "melee_damage": 1,
            "range": 200.0,
            "cooldown": 0.20,
            "magazine": 12,
        },
        "shotgun": {
            "damage": 2,
            "melee_damage": 2,
            "range": 110.0,
            "cooldown": 0.20,
            "magazine": 6,
        },
        "rifle": {
            "damage": 1,
            "melee_damage": 1,
            "range": 280.0,
            "cooldown": 0.20,
            "magazine": 30,
        },
        "knife": {
            "damage": 0,
            "melee_damage": 3,
            "range": 75.0,
            "cooldown": 0.25,
            "magazine": None,
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
        self.alive = True

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

        # Match the deployed RLBot's approximate weapon reload times
        # rather than using a single artificial 0.28 s value.
        reload_times = {
            "handgun": 0.28,
            "shotgun": 0.16,
            "rifle": 0.22,
        }
        self.reload_timer = reload_times.get(self.weapon, 0.28)
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


# =========================================================
# SCRIPTED A* ENEMY
# =========================================================

class ScriptedEnemy(HeadlessBot):
    """
    Training-only opponent.

    Each enemy:
      - spawns at a random safe map position
      - targets the RL bot
      - uses A* to navigate around Tiled obstacles
      - replans periodically when the RL bot moves
      - switches between ranged pursuit and close pressure
      - can strafe while maintaining combat distance
    """

    PROFILES = (
        {
            "name": "aggressive",
            "preferred_min": 65.0,
            "preferred_max": 125.0,
            "speed": 2.05,
        },
        {
            "name": "ranged",
            "preferred_min": 170.0,
            "preferred_max": 230.0,
            "speed": 1.80,
        },
        {
            "name": "strafer",
            "preferred_min": 115.0,
            "preferred_max": 190.0,
            "speed": 1.95,
        },
        {
            "name": "flanker",
            "preferred_min": 90.0,
            "preferred_max": 170.0,
            "speed": 2.00,
        },
        {
            "name": "hunter",
            "preferred_min": 55.0,
            "preferred_max": 145.0,
            "speed": 2.15,
        },
    )

    def __init__(self, x, y, enemy_id, profile):
        super().__init__(x, y)

        self.enemy_id = int(enemy_id)
        self.profile = dict(profile)
        self.speed = float(profile["speed"])
        self.run_speed = self.speed * 1.25

        self.weapon = "rifle"
        self.health = 40.0
        self.max_health = 40.0
        self.weapon_ammo = {
            "handgun": 12,
            "shotgun": 6,
            "rifle": 30,
            "knife": None,
        }

        self.path = []
        self.path_index = 0
        self.path_goal_cell = None
        self.last_path_target = None
        self.path_age = 999.0
        self.repath_interval = 1.0
        self.strafe_sign = random.choice((-1, 1))
        self.strafe_timer = random.uniform(0.8, 2.0)

        self.alive = True
        self.pursuing = False

    def reset_navigation(self):
        self.path = []
        self.path_index = 0
        self.path_goal_cell = None
        self.last_path_target = None
        self.path_age = 999.0
        self.strafe_sign = random.choice((-1, 1))
        self.strafe_timer = random.uniform(0.8, 2.0)

    def update_navigation(
        self,
        env,
        target_x,
        target_y,
        dt,
    ):
        if not self.alive or not self.pursuing:
            return

        self.path_age += dt
        self.strafe_timer -= dt

        if self.strafe_timer <= 0:
            self.strafe_sign *= -1
            self.strafe_timer = random.uniform(0.8, 2.0)

        enemy_x, enemy_y = self.center()
        distance = math.hypot(
            target_x - enemy_x,
            target_y - enemy_y,
        )

        los = env._has_line_of_sight(
            enemy_x,
            enemy_y,
            target_x,
            target_y,
        )

        # When the target is visible, direct pursuit/positioning is
        # faster and avoids needless A* work. If a wall blocks LOS,
        # A* is used to route around it.
        needs_path = (
            not los
            or self.path_age >= self.repath_interval
            or self._target_moved_enough(target_x, target_y)
            or not self._path_is_valid(env)
        )

        if needs_path:
            self.path = env._astar_path(
                (enemy_x, enemy_y),
                (target_x, target_y),
            )
            self.path_index = 0
            self.path_age = 0.0
            self.last_path_target = (target_x, target_y)

        desired_dx = 0.0
        desired_dy = 0.0

        min_range = self.profile["preferred_min"]
        max_range = self.profile["preferred_max"]

        if distance > max_range:
            # Close on the target.
            if los:
                desired_dx = target_x - enemy_x
                desired_dy = target_y - enemy_y
            else:
                desired_dx, desired_dy = self._path_direction(
                    enemy_x,
                    enemy_y,
                )

        elif distance < min_range:
            # Back away while keeping the target in sight.
            desired_dx = enemy_x - target_x
            desired_dy = enemy_y - target_y

            # If backing into an obstacle or the screen boundary, use
            # the A* path direction instead of getting stuck.
            if not self._can_move_direction(
                env,
                desired_dx,
                desired_dy,
            ):
                desired_dx, desired_dy = self._path_direction(
                    enemy_x,
                    enemy_y,
                )

        else:
            # Combat-distance strafe. A* path is still available if
            # the direct strafe is blocked by a wall.
            desired_dx = -(
                target_y - enemy_y
            ) * self.strafe_sign
            desired_dy = (
                target_x - enemy_x
            ) * self.strafe_sign

            if not self._can_move_direction(
                env,
                desired_dx,
                desired_dy,
            ):
                desired_dx, desired_dy = self._path_direction(
                    enemy_x,
                    enemy_y,
                )

        if desired_dx != 0.0 or desired_dy != 0.0:
            self.move(
                desired_dx,
                desired_dy,
                self.speed,
                env.obstacles,
            )

        env._clamp_actor(self)

    def _target_moved_enough(self, target_x, target_y):
        if self.last_path_target is None:
            return True

        return (
            math.hypot(
                target_x - self.last_path_target[0],
                target_y - self.last_path_target[1],
            )
            >= 45.0
        )

    def _path_is_valid(self, env):
        if not self.path:
            return False

        if self.path_index >= len(self.path):
            return False

        # The remaining waypoint itself must still be walkable.
        wx, wy = self.path[self.path_index]
        return env._actor_position_is_safe(
            wx - self.WIDTH / 2.0,
            wy - self.HEIGHT / 2.0,
            self,
        )

    def _path_direction(self, x, y):
        while (
            self.path_index < len(self.path)
        ):
            waypoint_x, waypoint_y = self.path[self.path_index]

            dx = waypoint_x - x
            dy = waypoint_y - y

            if math.hypot(dx, dy) <= 14.0:
                self.path_index += 1
                continue

            return dx, dy

        return 0.0, 0.0

    def _can_move_direction(self, env, dx, dy):
        if dx == 0 and dy == 0:
            return True

        length = math.hypot(dx, dy)
        dx /= length
        dy /= length

        test_distance = min(
            18.0,
            self.speed * 4.0,
        )

        old_x = self.x
        old_y = self.y

        self.x += dx * test_distance
        self.y += dy * test_distance

        blocked = not env._actor_position_is_safe(
            self.x,
            self.y,
            self,
        )

        self.x = old_x
        self.y = old_y

        return not blocked


# =========================================================
# HEADLESS RL25 ENVIRONMENT
# =========================================================

class HeadlessShooterEnv(gym.Env):
    """
    RL25 headless training environment.

    RL interface is intentionally unchanged:
        9 actions
        34 observations

    Final training-world contract:
        - exactly 2 scripted enemies
        - only enemy 0 pursues initially
        - enemy 1 joins when enemy 0 reaches <= 75% HP
        - both enemies can damage the RL bot after activation
        - RL bot can target either alive enemy
        - A* is used only by scripted enemies
        - RL bot learns its own navigation from observations
        - projectile travel/collision matches the real bullet model
        - health/ammo pickup direction is exposed to the DQN
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

    # Final observation contract. Keep this order identical in
    # TacticalShooterEnv and in DQNAgent's feature interpretation.
    STATE_SIZE = 34

    # =====================================================
    # WEAPON / TIMING
    # =====================================================

    WEAPON_SWITCH_COOLDOWN = 0.8
    RL_STEP_DT = 0.1

    # =====================================================
    # MAP
    # =====================================================

    TILE_SCALE = 1.638
    MAP_VERTICAL_OFFSET = -30

    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 700

    PLAYER_START = (150.0, 180.0)
    RL_BOT_1_SPAWN_INDEX = 1

    # Actual game entities are screen-clamped, so training
    # enemies are spawned in the same 1000x700 usable area.
    PLAYABLE_LEFT = 0.0
    PLAYABLE_TOP = 0.0
    PLAYABLE_RIGHT = 1000.0
    PLAYABLE_BOTTOM = 700.0

    NUM_SCRIPTED_ENEMIES = 2
    MIN_ENEMY_BOT_DISTANCE = 180.0
    MIN_ENEMY_ENEMY_DISTANCE = 120.0

    # The second scripted enemy joins only after the initially
    # pursuing enemy has lost 25% of its health, or immediately
    # if that first pursuer dies.
    SECOND_ENEMY_ACTIVATION_HEALTH_RATIO = 0.75

    # The real game advances at 60 FPS while the DQN makes one
    # decision every 0.1 s. Headless training therefore simulates
    # the same six 60-FPS frames per RL step.
    GAME_FRAME_DT = 1.0 / 60.0
    GAME_FRAMES_PER_RL_STEP = int(
        round(RL_STEP_DT / GAME_FRAME_DT)
    )

    # Matches src/bullet.py.
    PROJECTILE_SPEED = 10.0
    PROJECTILE_RADIUS = 5.0

    # A* grid. 20 px gives enough resolution for 40x40 actors
    # while keeping training computationally practical.
    ASTAR_CELL_SIZE = 20.0
    ASTAR_REPATH_INTERVAL = 1.0

    def __init__(self, max_steps=1800, seed=None):
        super().__init__()

        self.max_steps = max_steps

        self.action_space = spaces.Discrete(
            self.ACTION_SIZE
        )

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

        self.obstacles = self._load_obstacles()

        (
            self.MAP_LEFT,
            self.MAP_TOP,
            self.MAP_RIGHT,
            self.MAP_BOTTOM,
        ) = self._get_map_bounds(self.tmx_data)

        # Intersect the Tiled map bounds with the actual game
        # screen. This matches main.py's entity boundary.
        self.NAV_LEFT = max(
            self.PLAYABLE_LEFT,
            self.MAP_LEFT,
        )
        self.NAV_TOP = max(
            self.PLAYABLE_TOP,
            self.MAP_TOP,
        )
        self.NAV_RIGHT = min(
            self.PLAYABLE_RIGHT,
            self.MAP_RIGHT,
        )
        self.NAV_BOTTOM = min(
            self.PLAYABLE_BOTTOM,
            self.MAP_BOTTOM,
        )

        print(
            f"Headless Tiled obstacle count: {len(self.obstacles)}"
        )
        print(
            "Headless map bounds: "
            f"({self.MAP_LEFT:.0f}, {self.MAP_TOP:.0f}) -> "
            f"({self.MAP_RIGHT:.0f}, {self.MAP_BOTTOM:.0f})"
        )
        print(
            "Headless playable bounds: "
            f"({self.NAV_LEFT:.0f}, {self.NAV_TOP:.0f}) -> "
            f"({self.NAV_RIGHT:.0f}, {self.NAV_BOTTOM:.0f})"
        )

        if len(self.obstacles) != 114:
            raise RuntimeError(
                "Tiled obstacle count mismatch: "
                f"expected 114, loaded {len(self.obstacles)}."
            )

        print("PASS: Loaded all 114 Tiled obstacles.")

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
        self.enemies = []
        self.target_enemy = None

        self.step_count = 0
        self.previous_distance = 0.0
        self.previous_health_pickup_distance = 500.0
        self.previous_ammo_pickup_distance = 500.0

        self.previous_target_position = None
        self.previous_target_enemy_id = None
        self.target_velocity_x = 0.0
        self.target_velocity_y = 0.0

        self.projectiles = []
        self._shots_resolved_this_step = 0
        self._shots_missed_this_step = 0

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False
        self.last_melee_hit = False

        self.shots_fired = 0
        self.shots_hit = 0
        self.melee_attempts = 0
        self.melee_hits = 0

        self.weapon_switches = 0
        self.health_pickups_collected = 0
        self.ammo_pickups_collected = 0
        self.enemies_defeated_count = 0

        self.bot_defeated = False
        self.player_defeated = False

        self._step_weapon_switches = 0
        self.weapon_switch_lock = 0.0

        self.range_milestones = {
            350.0: False,
            280.0: False,
            200.0: False,
            110.0: False,
            75.0: False,
        }

        # -------------------------------------------------
        # A* GRID IS STATIC FOR THE MAP.
        # -------------------------------------------------
        self.astar_grid = self._build_astar_grid()

        print(
            "A* navigation grid: "
            f"{self.astar_width} x {self.astar_height} "
            f"({self.astar_width * self.astar_height} cells)"
        )

        print("Environment created.")
        print(
            f"Observation space: {self.observation_space}"
        )
        print(
            f"Action space: {self.action_space}"
        )
        print("Environment dimensions validated.")
        print(
            f"Training enemies per episode: "
            f"{self.NUM_SCRIPTED_ENEMIES}"
        )

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
    # TILED MAP
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
            return pytmx.load_pygame(map_path)
        except Exception as exc:
            raise RuntimeError(
                "Failed to load Dungeon1.tmx.\n"
                f"Map path: {map_path}\n"
                f"Original error: {exc}"
            ) from exc

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

    def _get_map_bounds(self, tmx_data):
        offset_x, offset_y = self._get_map_offset(tmx_data)

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

    def _load_object_points(self, layer_name):
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

    def _load_obstacles(self):
        self.tmx_data = self._load_tiled_map()

        try:
            obstacle_layer = self.tmx_data.get_layer_by_name(
                "obstacle"
            )
        except ValueError as exc:
            raise RuntimeError(
                "The Tiled 'obstacle' object layer was not found."
            ) from exc

        offset_x, offset_y = self._get_map_offset(
            self.tmx_data
        )

        obstacles = []

        for obj in obstacle_layer:
            obstacles.append(
                {
                    "x": float(
                        int(
                            offset_x +
                            obj.x * self.TILE_SCALE
                        )
                    ),
                    "y": float(
                        int(
                            offset_y +
                            obj.y * self.TILE_SCALE
                        )
                    ),
                    "width": float(
                        int(
                            obj.width * self.TILE_SCALE
                        )
                    ),
                    "height": float(
                        int(
                            obj.height * self.TILE_SCALE
                        )
                    ),
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
    # A* NAVIGATION
    # =====================================================

    def _build_astar_grid(self):
        self.astar_width = int(
            math.ceil(
                (
                    self.NAV_RIGHT -
                    self.NAV_LEFT
                ) /
                self.ASTAR_CELL_SIZE
            )
        )
        self.astar_height = int(
            math.ceil(
                (
                    self.NAV_BOTTOM -
                    self.NAV_TOP
                ) /
                self.ASTAR_CELL_SIZE
            )
        )

        grid = np.ones(
            (
                self.astar_height,
                self.astar_width
            ),
            dtype=np.bool_,
        )

        # Inflate obstacles by half the actor width plus a small
        # margin. This makes A* paths suitable for 40x40 actors,
        # not merely point particles.
        inflation = 22.0

        for gy in range(self.astar_height):
            center_y = (
                self.NAV_TOP
                +
                (gy + 0.5) *
                self.ASTAR_CELL_SIZE
            )

            for gx in range(self.astar_width):
                center_x = (
                    self.NAV_LEFT
                    +
                    (gx + 0.5) *
                    self.ASTAR_CELL_SIZE
                )

                body_left = center_x - HeadlessBot.WIDTH / 2.0
                body_top = center_y - HeadlessBot.HEIGHT / 2.0
                body_right = center_x + HeadlessBot.WIDTH / 2.0
                body_bottom = center_y + HeadlessBot.HEIGHT / 2.0

                outside_bounds = (
                    body_left < self.NAV_LEFT
                    or body_top < self.NAV_TOP
                    or body_right > self.NAV_RIGHT
                    or body_bottom > self.NAV_BOTTOM
                )

                if (
                    outside_bounds
                    or
                    self._point_inside_inflated_obstacle(
                        center_x,
                        center_y,
                        inflation,
                    )
                ):
                    grid[gy, gx] = False

        return grid

    def _point_inside_inflated_obstacle(
        self,
        x,
        y,
        inflation,
    ):
        for obstacle in self.obstacles:
            ox = obstacle["x"] - inflation
            oy = obstacle["y"] - inflation
            ow = obstacle["width"] + 2.0 * inflation
            oh = obstacle["height"] + 2.0 * inflation

            if (
                ox <= x <= ox + ow
                and
                oy <= y <= oy + oh
            ):
                return True

        return False

    def _world_to_cell(self, x, y):
        gx = int(
            (x - self.NAV_LEFT) /
            self.ASTAR_CELL_SIZE
        )
        gy = int(
            (y - self.NAV_TOP) /
            self.ASTAR_CELL_SIZE
        )

        gx = max(
            0,
            min(
                self.astar_width - 1,
                gx,
            ),
        )
        gy = max(
            0,
            min(
                self.astar_height - 1,
                gy,
            ),
        )

        return gx, gy

    def _cell_to_world(self, gx, gy):
        return (
            self.NAV_LEFT
            +
            (gx + 0.5) *
            self.ASTAR_CELL_SIZE,
            self.NAV_TOP
            +
            (gy + 0.5) *
            self.ASTAR_CELL_SIZE,
        )

    def _nearest_walkable_cell(self, cell):
        gx, gy = cell

        if self.astar_grid[gy, gx]:
            return cell

        max_radius = max(
            self.astar_width,
            self.astar_height,
        )

        for radius in range(1, max_radius):
            min_x = max(0, gx - radius)
            max_x = min(
                self.astar_width - 1,
                gx + radius,
            )
            min_y = max(0, gy - radius)
            max_y = min(
                self.astar_height - 1,
                gy + radius,
            )

            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    if self.astar_grid[y, x]:
                        return x, y

        return None

    def _astar_path(self, start_world, goal_world):
        start = self._nearest_walkable_cell(
            self._world_to_cell(
                start_world[0],
                start_world[1],
            )
        )
        goal = self._nearest_walkable_cell(
            self._world_to_cell(
                goal_world[0],
                goal_world[1],
            )
        )

        if start is None or goal is None:
            return []

        if start == goal:
            return []

        open_heap = []
        heapq.heappush(
            open_heap,
            (
                0.0,
                start,
            ),
        )

        came_from = {}
        g_score = {
            start: 0.0,
        }

        directions = (
            (-1, 0, 1.0),
            (1, 0, 1.0),
            (0, -1, 1.0),
            (0, 1, 1.0),
            (-1, -1, 1.41421356),
            (-1, 1, 1.41421356),
            (1, -1, 1.41421356),
            (1, 1, 1.41421356),
        )

        def heuristic(a, b):
            dx = abs(a[0] - b[0])
            dy = abs(a[1] - b[1])
            return (
                max(dx, dy)
                +
                (1.41421356 - 1.0)
                * min(dx, dy)
            )

        closed = set()

        while open_heap:
            _, current = heapq.heappop(
                open_heap
            )

            if current in closed:
                continue

            if current == goal:
                path_cells = [current]

                while current in came_from:
                    current = came_from[current]
                    path_cells.append(current)

                path_cells.reverse()

                # Remove the start cell and compress unnecessary
                # collinear waypoints.
                path_cells = path_cells[1:]
                path_cells = self._compress_path(
                    path_cells
                )

                return [
                    self._cell_to_world(x, y)
                    for x, y in path_cells
                ]

            closed.add(current)

            cx, cy = current

            for dx, dy, move_cost in directions:
                nx = cx + dx
                ny = cy + dy

                if (
                    nx < 0
                    or ny < 0
                    or nx >= self.astar_width
                    or ny >= self.astar_height
                ):
                    continue

                if not self.astar_grid[ny, nx]:
                    continue

                # Prevent diagonal corner cutting through walls.
                if dx != 0 and dy != 0:
                    if (
                        not self.astar_grid[cy, nx]
                        or
                        not self.astar_grid[ny, cx]
                    ):
                        continue

                neighbor = (nx, ny)

                if neighbor in closed:
                    continue

                tentative_g = (
                    g_score[current]
                    +
                    move_cost
                )

                if (
                    neighbor not in g_score
                    or
                    tentative_g < g_score[neighbor]
                ):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g

                    f_score = (
                        tentative_g
                        +
                        heuristic(
                            neighbor,
                            goal,
                        )
                    )

                    heapq.heappush(
                        open_heap,
                        (
                            f_score,
                            neighbor,
                        ),
                    )

        return []

    @staticmethod
    def _compress_path(path_cells):
        if len(path_cells) <= 2:
            return path_cells

        result = [path_cells[0]]

        previous_direction = None

        for i in range(1, len(path_cells)):
            previous = path_cells[i - 1]
            current = path_cells[i]

            direction = (
                current[0] - previous[0],
                current[1] - previous[1],
            )

            if (
                previous_direction is not None
                and
                direction != previous_direction
            ):
                result.append(previous)

            previous_direction = direction

        result.append(path_cells[-1])

        return result

    # =====================================================
    # SAFE SPAWNING
    # =====================================================

    def _random_safe_spawn(
        self,
        existing_positions,
        min_distance,
        max_attempts=500,
    ):
        for _ in range(max_attempts):
            x = random.uniform(
                self.NAV_LEFT + 40.0,
                self.NAV_RIGHT - 40.0,
            )
            y = random.uniform(
                self.NAV_TOP + 40.0,
                self.NAV_BOTTOM - 40.0,
            )

            if not self._actor_position_is_safe(
                x,
                y,
                self.bot,
            ):
                continue

            cx = x + 20.0
            cy = y + 20.0

            too_close = False

            for px, py in existing_positions:
                if math.hypot(
                    cx - px,
                    cy - py,
                ) < min_distance:
                    too_close = True
                    break

            if too_close:
                continue

            return float(x), float(y)

        # Deterministic fallback: search grid cells.
        candidates = []

        for gy in range(self.astar_height):
            for gx in range(self.astar_width):
                if not self.astar_grid[gy, gx]:
                    continue

                wx, wy = self._cell_to_world(
                    gx,
                    gy,
                )

                x = wx - 20.0
                y = wy - 20.0

                if self._actor_position_is_safe(
                    x,
                    y,
                    self.bot,
                ):
                    candidates.append(
                        (x, y)
                    )

        random.shuffle(candidates)

        for x, y in candidates:
            cx = x + 20.0
            cy = y + 20.0

            if all(
                math.hypot(
                    cx - px,
                    cy - py,
                ) >= min_distance
                for px, py in existing_positions
            ):
                return float(x), float(y)

        raise RuntimeError(
            "Could not find a safe spawn point for a scripted enemy."
        )

    def _actor_position_is_safe(
        self,
        x,
        y,
        actor,
    ):
        width = getattr(
            actor,
            "WIDTH",
            40,
        )
        height = getattr(
            actor,
            "HEIGHT",
            40,
        )

        if (
            x < self.NAV_LEFT
            or
            y < self.NAV_TOP
            or
            x + width > self.NAV_RIGHT
            or
            y + height > self.NAV_BOTTOM
        ):
            return False

        left = x
        right = x + width
        top = y
        bottom = y + height

        for obstacle in self.obstacles:
            ox = obstacle["x"]
            oy = obstacle["y"]
            ow = obstacle["width"]
            oh = obstacle["height"]

            if (
                right > ox
                and
                left < ox + ow
                and
                bottom > oy
                and
                top < oy + oh
            ):
                return False

        return True

    def _spawn_scripted_enemies(self):
        self.enemies = []

        bot_cx, bot_cy = self.bot.center()
        existing_positions = [
            (bot_cx, bot_cy)
        ]

        profiles = list(
            ScriptedEnemy.PROFILES
        )
        random.shuffle(profiles)

        for enemy_id in range(
            self.NUM_SCRIPTED_ENEMIES
        ):
            x, y = self._random_safe_spawn(
                existing_positions,
                self.MIN_ENEMY_BOT_DISTANCE
                if enemy_id == 0
                else self.MIN_ENEMY_ENEMY_DISTANCE,
            )

            # After the first enemy, the minimum-distance list also
            # contains the RL bot and all previous enemies.
            profile = profiles[
                enemy_id % len(profiles)
            ]

            enemy = ScriptedEnemy(
                x,
                y,
                enemy_id,
                profile,
            )

            # Enemy 0 is the initial pursuer. Enemy 1 is present in
            # the world and can be targeted, but does not pursue or
            # fire until the activation condition is reached.
            enemy.pursuing = (enemy_id == 0)

            self.enemies.append(enemy)

            cx, cy = enemy.center()
            existing_positions.append(
                (cx, cy)
            )

        # Spawns are intentionally not printed every episode; doing so
        # would flood the terminal during long DQN training runs.

    # =====================================================
    # RESET
    # =====================================================

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.step_count = 0

        bot_spawn = self.rl_bot_spawn_points[
            self.RL_BOT_1_SPAWN_INDEX
        ]

        self.bot = HeadlessBot(
            bot_spawn[0],
            bot_spawn[1],
        )

        # The RL bot must itself start inside the actual screen/map
        # bounds. Preserve the exact Tiled spawn if valid; otherwise
        # clamp it to the playable screen.
        self._clamp_actor(self.bot)

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

        self._spawn_scripted_enemies()
        self._update_target_enemy()

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False
        self.last_melee_hit = False

        self.shots_fired = 0
        self.shots_hit = 0
        self.melee_attempts = 0
        self.melee_hits = 0

        self.weapon_switches = 0
        self.health_pickups_collected = 0
        self.ammo_pickups_collected = 0
        self.enemies_defeated_count = 0

        self.bot_defeated = False
        self.player_defeated = False

        self._step_weapon_switches = 0
        self.weapon_switch_lock = 0.0

        self.range_milestones = {
            350.0: False,
            280.0: False,
            200.0: False,
            110.0: False,
            75.0: False,
        }

        self.previous_distance = (
            self._distance_bot_target()
        )
        self.previous_health_pickup_distance = (
            self._nearest_needed_pickup_distance(
                self.health_pickups,
            )
        )
        self.previous_ammo_pickup_distance = (
            self._nearest_needed_pickup_distance(
                self.ammo_pickups,
            )
        )

        self.previous_target_position = (
            self.target_enemy.center()
            if self.target_enemy is not None
            else None
        )
        self.previous_target_enemy_id = (
            self.target_enemy.enemy_id
            if self.target_enemy is not None
            else None
        )
        self.target_velocity_x = 0.0
        self.target_velocity_y = 0.0
        self.projectiles = []
        self._shots_resolved_this_step = 0
        self._shots_missed_this_step = 0

        observation = self._get_observation()

        info = self._info_dict()

        return observation, info

    # =====================================================
    # TARGET SELECTION
    # =====================================================

    def _update_target_enemy(self):
        alive = [
            enemy
            for enemy in self.enemies
            if enemy.alive
            and enemy.health > 0
        ]

        if not alive:
            self.target_enemy = None
            return None

        bot_x, bot_y = self.bot.center()

        # The DQN has one target slot, so expose the nearest alive
        # enemy with LOS when possible. Both scripted enemies are
        # therefore observable/targetable even while enemy 1 is still
        # inactive as a pursuer.
        visible = [
            enemy
            for enemy in alive
            if self._has_line_of_sight(
                bot_x,
                bot_y,
                *enemy.center(),
            )
        ]

        pool = visible if visible else alive

        self.target_enemy = min(
            pool,
            key=lambda enemy: math.hypot(
                enemy.center()[0] - bot_x,
                enemy.center()[1] - bot_y,
            ),
        )

        return self.target_enemy

    # =====================================================
    # STEP
    # =====================================================

    def step(self, action):
        action = int(action)

        if not self.action_space.contains(action):
            raise ValueError(f"Invalid action: {action}")

        self.step_count += 1

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0
        self.last_shot_fired = False
        self.last_shot_hit = False
        self.last_melee_hit = False
        self._step_weapon_switches = 0
        self._shots_resolved_this_step = 0
        self._shots_missed_this_step = 0

        # Snapshot target identity/position before the six simulated
        # render frames. This produces a stable per-RL-step velocity
        # feature instead of a noisy per-frame value.
        self._update_target_enemy()
        old_target_id = (
            self.target_enemy.enemy_id
            if self.target_enemy is not None
            else None
        )
        old_target_position = (
            self.target_enemy.center()
            if self.target_enemy is not None
            else None
        )

        reward = 0.0

        for frame_index in range(self.GAME_FRAMES_PER_RL_STEP):
            frame_dt = self.GAME_FRAME_DT

            self.bot.update_timers(frame_dt)
            for enemy in self.enemies:
                enemy.update_timers(frame_dt)

            self.weapon_switch_lock = max(
                0.0,
                self.weapon_switch_lock - frame_dt,
            )

            # Combat actions happen once at the beginning of the RL
            # interval. Movement actions are held for all six frames,
            # matching TacticalShooterEnv's render-frame bridge.
            if frame_index == 0:
                self._execute_bot_action(
                    action,
                    movement_scale=(1.0 / self.GAME_FRAMES_PER_RL_STEP),
                    combat=True,
                )
            elif action in (
                self.ACTION_FORWARD,
                self.ACTION_BACKWARD,
                self.ACTION_LEFT,
                self.ACTION_RIGHT,
                self.ACTION_SPRINT,
            ):
                self._execute_bot_action(
                    action,
                    movement_scale=(1.0 / self.GAME_FRAMES_PER_RL_STEP),
                    combat=False,
                )

            reward += self._handle_pickups()
            self._update_scripted_enemies(frame_dt)
            self._update_projectiles()

            if self.bot.health <= 0:
                break

        # Update target and derive velocity only when the same target
        # survived the whole RL interval. If the target changed/died,
        # report zero velocity for the new target rather than creating
        # an artificial velocity spike from two different actors.
        self._update_target_enemy()
        if (
            self.target_enemy is not None
            and old_target_id == self.target_enemy.enemy_id
            and old_target_position is not None
        ):
            new_x, new_y = self.target_enemy.center()
            self.target_velocity_x = float(
                np.clip(
                    (new_x - old_target_position[0]) / self.RL_STEP_DT / 180.0,
                    -1.0,
                    1.0,
                )
            )
            self.target_velocity_y = float(
                np.clip(
                    (new_y - old_target_position[1]) / self.RL_STEP_DT / 180.0,
                    -1.0,
                    1.0,
                )
            )
        else:
            self.target_velocity_x = 0.0
            self.target_velocity_y = 0.0

        # -------------------------------------------------
        # PICKUP APPROACH SHAPING
        # -------------------------------------------------
        current_distance = self._distance_bot_target()
        distance_change = self.previous_distance - current_distance
        reward += 0.04 * float(np.clip(distance_change, -5.0, 5.0))
        self.previous_distance = current_distance

        health_distance = self._nearest_needed_pickup_distance(self.health_pickups)
        ammo_distance = self._nearest_needed_pickup_distance(self.ammo_pickups)

        if self.bot.health <= 0.50 * self.bot.max_health:
            reward += 0.03 * float(
                np.clip(
                    self.previous_health_pickup_distance - health_distance,
                    -5.0,
                    5.0,
                )
            )

        if (
            self.bot.weapon != "knife"
            and self._current_ammo_ratio() <= 0.25
        ):
            reward += 0.03 * float(
                np.clip(
                    self.previous_ammo_pickup_distance - ammo_distance,
                    -5.0,
                    5.0,
                )
            )

        self.previous_health_pickup_distance = health_distance
        self.previous_ammo_pickup_distance = ammo_distance

        # -------------------------------------------------
        # RANGE / ENGAGEMENT
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

        if current_distance <= 280.0 and self._line_of_sight():
            reward += 0.05

        if current_distance > 350.0:
            reward -= 0.03

        reward -= 0.01
        reward -= 0.05 * self._step_weapon_switches

        # A projectile is only penalized when it actually resolves as
        # a miss (wall/out-of-bounds), not immediately after firing.
        # This avoids teaching the DQN that every long-range shot is a
        # miss simply because the projectile needs time to travel.
        reward -= 0.05 * self._shots_missed_this_step

        reward += 3.0 * self.last_damage_dealt

        if self.last_shot_hit:
            reward += 1.0

        reward -= 0.75 * self.last_damage_taken

        # -------------------------------------------------
        # TERMINATION
        # -------------------------------------------------
        terminated = False

        if self.bot.health <= 0:
            self.bot.health = 0.0
            self.bot.alive = False
            self.bot_defeated = True
            reward -= 100.0
            terminated = True

        elif not any(
            enemy.alive and enemy.health > 0
            for enemy in self.enemies
        ):
            self.player_defeated = True
            reward += 100.0
            terminated = True

        truncated = self.step_count >= self.max_steps

        observation = self._get_observation()
        info = self._info_dict(
            action=action,
            distance=current_distance,
        )

        return (
            observation,
            float(reward),
            terminated,
            truncated,
            info,
        )

    # =====================================================
    # RL BOT ACTION
    # =====================================================

    def _execute_bot_action(
        self,
        action,
        movement_scale=1.0,
        combat=True,
    ):
        bot_x, bot_y = self.bot.center()

        self._update_target_enemy()

        if self.target_enemy is not None:
            target_x, target_y = self.target_enemy.center()
        else:
            target_x, target_y = bot_x + 1.0, bot_y

        dx = target_x - bot_x
        dy = target_y - bot_y
        distance = math.hypot(dx, dy)

        if distance > 0:
            self.bot.facing_x = dx / distance
            self.bot.facing_y = dy / distance

        # Explicit melee owns the knife.
        if action == self.ACTION_MELEE:
            if combat and distance <= 75.0:
                self._select_combat_weapon(
                    distance,
                    force_melee=True,
                )
                self._bot_melee()
            self._clamp_actor(self.bot)
            return

        # Important deployment/training consistency:
        # once the bot leaves a melee action, a movement action
        # should not leave it wandering around the map permanently
        # with the knife equipped. A non-melee combat/movement
        # action returns it to an appropriate firearm.
        if self.bot.weapon == "knife":
            self._select_combat_weapon(
                distance,
                force_melee=False,
                ignore_switch_lock=True,
            )

        if action == self.ACTION_FORWARD:
            self.bot.move(
                self.bot.facing_x,
                self.bot.facing_y,
                self.bot.speed * movement_scale,
                self.obstacles,
            )

        elif action == self.ACTION_BACKWARD:
            self.bot.move(
                -self.bot.facing_x,
                -self.bot.facing_y,
                self.bot.speed * movement_scale,
                self.obstacles,
            )

        elif action == self.ACTION_LEFT:
            self.bot.move(
                -self.bot.facing_y,
                self.bot.facing_x,
                self.bot.speed * movement_scale,
                self.obstacles,
            )

        elif action == self.ACTION_RIGHT:
            self.bot.move(
                self.bot.facing_y,
                -self.bot.facing_x,
                self.bot.speed * movement_scale,
                self.obstacles,
            )

        elif action == self.ACTION_SPRINT:
            self.bot.move(
                self.bot.facing_x,
                self.bot.facing_y,
                self.bot.run_speed * movement_scale,
                self.obstacles,
            )

        elif action == self.ACTION_SHOOT and combat:
            self._select_combat_weapon(
                distance,
                force_melee=False,
            )
            self._bot_shoot()

        elif action == self.ACTION_RELOAD and combat:
            self._execute_reload()

        self._clamp_actor(self.bot)

    # =====================================================
    # WEAPON SELECTION
    # =====================================================

    def _select_combat_weapon(
        self,
        distance,
        force_melee=False,
        ignore_switch_lock=False,
    ):
        if force_melee:
            preferred = "knife"
        elif distance <= 110.0:
            preferred = "shotgun"
        elif distance <= 200.0:
            preferred = "handgun"
        else:
            preferred = "rifle"

        if (
            self.bot.weapon != preferred
            and
            self.weapon_switch_lock > 0.0
            and
            not ignore_switch_lock
            and
            not force_melee
        ):
            self.bot.rl_target_weapon = preferred
            return False

        if preferred == "knife":
            if self.bot.weapon != "knife":
                if self.bot.equip("knife"):
                    self.weapon_switches += 1
                    self._step_weapon_switches += 1
                    self.weapon_switch_lock = (
                        self.WEAPON_SWITCH_COOLDOWN
                    )
            self.bot.rl_target_weapon = "knife"
            return self.bot.weapon == "knife"

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
                self.bot.rl_target_weapon = preferred
                return False

        if self.bot.weapon != preferred:
            if self.bot.equip(preferred):
                self.weapon_switches += 1
                self._step_weapon_switches += 1
                self.weapon_switch_lock = (
                    self.WEAPON_SWITCH_COOLDOWN
                )

        self.bot.rl_target_weapon = preferred
        return self.bot.weapon == preferred

    # =====================================================
    # SHOOT
    # =====================================================

    def _bot_shoot(self):
        self.last_shot_fired = False
        self.last_shot_hit = False

        if self.target_enemy is None:
            return

        if self.bot.weapon == "knife":
            return

        if not self.bot.can_shoot():
            if self.bot.is_empty():
                self.bot.start_reload()
            return

        bot_x, bot_y = self.bot.center()
        target_x, target_y = self.target_enemy.center()

        distance = math.hypot(
            target_x - bot_x,
            target_y - bot_y,
        )

        stats = self.bot.WEAPON_STATS[self.bot.weapon]

        if distance > stats["range"]:
            return

        if not self._line_of_sight():
            return

        if not self.bot.shoot():
            return

        self.last_shot_fired = True
        self.shots_fired += 1

        self.bot.aim_at(
            target_x,
            target_y,
        )

        self._spawn_projectile(
            owner="rl_bot",
            shooter=self.bot,
            target_x=target_x,
            target_y=target_y,
            muzzle_distance=35.0,
            damage=stats["damage"],
        )

    # =====================================================
    # MELEE
    # =====================================================

    def _bot_melee(self):
        self.melee_attempts += 1
        self.last_melee_hit = False

        if (
            self.target_enemy is None
            or
            self.bot.weapon != "knife"
        ):
            return

        if self.bot.shoot_cooldown > 0:
            return

        bot_x, bot_y = self.bot.center()
        target_x, target_y = self.target_enemy.center()

        distance = math.hypot(
            target_x - bot_x,
            target_y - bot_y,
        )

        if distance > 75.0:
            return

        self.bot.shoot_cooldown = (
            self.bot.WEAPON_STATS["knife"]["cooldown"]
        )

        damage = self.bot.WEAPON_STATS["knife"]["melee_damage"]

        self.target_enemy.health = max(
            0.0,
            self.target_enemy.health - damage,
        )

        self.last_damage_dealt += damage
        self.last_shot_hit = True
        self.last_melee_hit = True
        self.melee_hits += 1

        if self.target_enemy.health <= 0:
            self.target_enemy.alive = False
            self.enemies_defeated_count += 1

    # =====================================================
    # RELOAD
    # =====================================================

    def _execute_reload(self):
        if self.bot.weapon == "knife":
            # Never reload the knife.
            return False

        return self.bot.start_reload()

    # =====================================================
    # SCRIPTED ENEMIES
    # =====================================================

    def _update_scripted_enemies(self, dt):
        if self.bot.health <= 0:
            return

        # Activate enemy 1 when the initial pursuer reaches 75% HP
        # or dies. This creates the intended staged difficulty.
        if len(self.enemies) >= 2:
            first = self.enemies[0]
            second = self.enemies[1]
            if (
                not second.pursuing
                and
                (
                    not first.alive
                    or
                    first.health <= (
                        first.max_health *
                        self.SECOND_ENEMY_ACTIVATION_HEALTH_RATIO
                    )
                )
            ):
                second.pursuing = True
                second.reset_navigation()

        bot_x, bot_y = self.bot.center()

        for enemy in self.enemies:
            if not enemy.alive or not enemy.pursuing:
                continue

            enemy.update_navigation(
                self,
                bot_x,
                bot_y,
                dt,
            )

            self._scripted_enemy_attack(enemy)

        self._clamp_actor(self.bot)

    def _scripted_enemy_attack(self, enemy):
        if (
            not enemy.alive
            or not enemy.pursuing
            or self.bot.health <= 0
        ):
            return

        enemy_x, enemy_y = enemy.center()
        bot_x, bot_y = self.bot.center()

        distance = math.hypot(
            bot_x - enemy_x,
            bot_y - enemy_y,
        )

        # Choose a weapon based on combat distance. Knife is not
        # used by scripted enemies; they provide ranged pressure.
        if distance <= 110.0:
            preferred = "shotgun"
        elif distance <= 200.0:
            preferred = "handgun"
        else:
            preferred = "rifle"

        if enemy.weapon != preferred:
            if enemy.weapon_ammo[preferred] > 0:
                enemy.equip(preferred)

        if enemy.weapon == "knife":
            enemy.equip("rifle")

        if enemy.is_empty():
            enemy.start_reload()
            return

        if (
            distance > enemy.WEAPON_STATS[enemy.weapon]["range"]
            or
            not self._has_line_of_sight(
                enemy_x,
                enemy_y,
                bot_x,
                bot_y,
            )
        ):
            return

        if not enemy.can_shoot():
            return

        enemy.aim_at(
            bot_x,
            bot_y,
        )

        if not enemy.shoot():
            return

        damage = enemy.WEAPON_STATS[
            enemy.weapon
        ]["damage"]

        self._spawn_projectile(
            owner="scripted_enemy",
            shooter=enemy,
            target_x=bot_x,
            target_y=bot_y,
            muzzle_distance=25.0,
            damage=damage,
        )

    # =====================================================
    # PROJECTILES
    # =====================================================

    def _spawn_projectile(
        self,
        owner,
        shooter,
        target_x,
        target_y,
        muzzle_distance,
        damage,
    ):
        sx, sy = shooter.center()
        dx = target_x - sx
        dy = target_y - sy
        length = math.hypot(dx, dy)

        if length <= 0.0:
            return

        dx /= length
        dy /= length

        self.projectiles.append({
            "x": sx + dx * muzzle_distance,
            "y": sy + dy * muzzle_distance,
            "dx": dx,
            "dy": dy,
            "damage": float(damage),
            "owner": owner,
            "radius": self.PROJECTILE_RADIUS,
        })

    def _projectile_rect(self, projectile):
        radius = projectile["radius"]
        return pygame.Rect(
            int(projectile["x"] - radius),
            int(projectile["y"] - radius),
            int(radius * 2),
            int(radius * 2),
        )

    def _projectile_hits_obstacle(self, projectile):
        rect = self._projectile_rect(projectile)
        for obstacle in self.obstacles:
            obstacle_rect = pygame.Rect(
                int(obstacle["x"]),
                int(obstacle["y"]),
                int(obstacle["width"]),
                int(obstacle["height"]),
            )
            if rect.colliderect(obstacle_rect):
                return True
        return False

    def _update_projectiles(self):
        if not self.projectiles:
            return

        for projectile in self.projectiles[:]:
            projectile["x"] += projectile["dx"] * self.PROJECTILE_SPEED
            projectile["y"] += projectile["dy"] * self.PROJECTILE_SPEED

            if self._projectile_hits_obstacle(projectile):
                self.projectiles.remove(projectile)
                self._shots_resolved_this_step += (
                    1 if projectile["owner"] == "rl_bot" else 0
                )
                self._shots_missed_this_step += (
                    1 if projectile["owner"] == "rl_bot" else 0
                )
                continue

            x = projectile["x"]
            y = projectile["y"]

            if (
                x < self.PLAYABLE_LEFT
                or x > self.PLAYABLE_RIGHT
                or y < self.PLAYABLE_TOP
                or y > self.PLAYABLE_BOTTOM
            ):
                self.projectiles.remove(projectile)
                if projectile["owner"] == "rl_bot":
                    self._shots_resolved_this_step += 1
                    self._shots_missed_this_step += 1
                continue

            if projectile["owner"] == "rl_bot":
                hit_enemy = False
                bullet_rect = self._projectile_rect(projectile)

                for enemy in self.enemies:
                    if (
                        not enemy.alive
                        or enemy.health <= 0
                    ):
                        continue

                    enemy_rect = pygame.Rect(
                        int(enemy.x),
                        int(enemy.y),
                        int(enemy.WIDTH),
                        int(enemy.HEIGHT),
                    )

                    if bullet_rect.colliderect(enemy_rect):
                        damage = projectile["damage"]
                        enemy.health = max(
                            0.0,
                            enemy.health - damage,
                        )
                        self.last_damage_dealt += damage
                        self.last_shot_hit = True
                        self.shots_hit += 1
                        self._shots_resolved_this_step += 1
                        hit_enemy = True

                        if enemy.health <= 0:
                            enemy.alive = False
                            self.enemies_defeated_count += 1

                        break

                if hit_enemy or projectile in self.projectiles:
                    if projectile in self.projectiles and hit_enemy:
                        self.projectiles.remove(projectile)
                        continue

            else:
                # Match the deployed enemy-bullet behavior: a point
                # collision against the RL bot body.
                if (
                    self.bot.alive
                    and
                    self.bot.x <= x <= self.bot.x + self.bot.WIDTH
                    and
                    self.bot.y <= y <= self.bot.y + self.bot.HEIGHT
                ):
                    damage = projectile["damage"]
                    self.bot.health = max(
                        0.0,
                        self.bot.health - damage,
                    )
                    self.last_damage_taken += damage

                    if self.bot.health <= 0:
                        self.bot.alive = False

                    self.projectiles.remove(projectile)
                    continue

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

        pickup_size = max(
            1,
            int(8 * self.TILE_SCALE),
        )

        # -------------------------------------------------
        # HEALTH
        # -------------------------------------------------
        if self.bot.health < self.bot.max_health:
            for pickup in self.health_pickups:
                if pickup["collected"]:
                    continue

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

                    if self.bot.health > old_health:
                        pickup["collected"] = True
                        self.health_pickups_collected += 1

                        # Stronger reward when the pickup was genuinely
                        # needed, encouraging health management.
                        health_ratio = (
                            old_health /
                            self.bot.max_health
                        )

                        reward += (
                            8.0
                            if health_ratio <= 0.50
                            else 4.0
                        )

                    break

        # -------------------------------------------------
        # AMMO
        # -------------------------------------------------
        if self.bot.weapon != "knife":
            current_ammo = self.bot.current_ammo()
            max_ammo = self.bot.max_ammo()

            # Only consume an ammo pack when ammo is not already full.
            if (
                current_ammo is not None
                and
                current_ammo < max_ammo
            ):
                for pickup in self.ammo_pickups:
                    if pickup["collected"]:
                        continue

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
                        old_ammo = current_ammo

                        self.bot.weapon_ammo[
                            self.bot.weapon
                        ] = max_ammo

                        if (
                            self.bot.current_ammo()
                            > old_ammo
                        ):
                            pickup["collected"] = True
                            self.ammo_pickups_collected += 1

                            ammo_ratio = (
                                old_ammo /
                                max_ammo
                            )

                            reward += (
                                5.0
                                if ammo_ratio <= 0.25
                                else 2.5
                            )

                        break

        return reward

    def _nearest_needed_pickup_distance(self, pickups):
        if not pickups:
            return 500.0

        bot_x, bot_y = self.bot.center()

        distances = []

        for pickup in pickups:
            if pickup["collected"]:
                continue

            distances.append(
                math.hypot(
                    bot_x - pickup["x"],
                    bot_y - pickup["y"],
                )
            )

        if not distances:
            return 500.0

        return min(distances)

    def _current_ammo_ratio(self):
        if self.bot.weapon == "knife":
            return 1.0

        ammo = self.bot.current_ammo()
        maximum = self.bot.max_ammo()

        if ammo is None or maximum <= 0:
            return 0.0

        return float(
            np.clip(
                ammo / maximum,
                0.0,
                1.0,
            )
        )

    @staticmethod
    def _rects_overlap(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b

        return (
            ax < bx + bw
            and
            ax + aw > bx
            and
            ay < by + bh
            and
            ay + ah > by
        )

    def _nearest_pickup_direction(self, pickups):
        available = [
            pickup
            for pickup in pickups
            if not pickup["collected"]
        ]

        if not available:
            return 0.0, 0.0

        bot_x, bot_y = self.bot.center()
        pickup = min(
            available,
            key=lambda p: math.hypot(
                p["x"] - bot_x,
                p["y"] - bot_y,
            ),
        )

        return (
            float(
                np.clip(
                    (pickup["x"] - bot_x) / 500.0,
                    -1.0,
                    1.0,
                )
            ),
            float(
                np.clip(
                    (pickup["y"] - bot_y) / 500.0,
                    -1.0,
                    1.0,
                )
            ),
        )

    # =====================================================
    # OBSERVATION
    # =====================================================

    def _get_observation(self):
        self._update_target_enemy()

        bot_x, bot_y = self.bot.center()

        if self.target_enemy is None:
            target_x = bot_x
            target_y = bot_y
            target_health = 0.0
            target_distance = 0.0
            los = False
            target_velocity_x = 0.0
            target_velocity_y = 0.0
        else:
            target_x, target_y = self.target_enemy.center()
            target_health = self.target_enemy.health
            target_distance = math.hypot(
                target_x - bot_x,
                target_y - bot_y,
            )
            los = self._line_of_sight()
            target_velocity_x = self.target_velocity_x
            target_velocity_y = self.target_velocity_y

        dx = target_x - bot_x
        dy = target_y - bot_y

        health_dx, health_dy = self._nearest_pickup_direction(
            self.health_pickups
        )
        ammo_dx, ammo_dy = self._nearest_pickup_direction(
            self.ammo_pickups
        )

        obs = [
            # 0-11: existing combat/body state
            self._normalize_position_x(bot_x),
            self._normalize_position_y(bot_y),
            np.clip(dx / 500.0, -1.0, 1.0),
            np.clip(dy / 500.0, -1.0, 1.0),
            np.clip(target_distance / 500.0, 0.0, 1.0),
            np.clip(self.bot.health / self.bot.max_health, 0.0, 1.0),
            np.clip(target_health / 40.0, 0.0, 1.0),
            (
                1.0
                if self.bot.weapon == "knife"
                else np.clip(
                    self.bot.current_ammo() / self.bot.max_ammo(),
                    0.0,
                    1.0,
                )
            ),
            {
                "handgun": -1.0,
                "shotgun": -0.33,
                "rifle": 0.33,
                "knife": 1.0,
            }.get(self.bot.weapon, -1.0),
            np.clip(self.bot.facing_x, -1.0, 1.0),
            np.clip(self.bot.facing_y, -1.0, 1.0),
            1.0 if los else 0.0,

            # 12-15: pickup distance/availability
            np.clip(
                self._nearest_pickup_distance(self.health_pickups) / 500.0,
                0.0, 1.0,
            ),
            np.clip(
                self._nearest_pickup_distance(self.ammo_pickups) / 500.0,
                0.0, 1.0,
            ),
            1.0 if any(not p["collected"] for p in self.health_pickups) else 0.0,
            1.0 if any(not p["collected"] for p in self.ammo_pickups) else 0.0,
        ]

        # 16-23: obstacle rays
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
            obs.append(
                np.clip(
                    self._ray_distance(
                        bot_x,
                        bot_y,
                        direction_x,
                        direction_y,
                        200.0,
                    ) / 200.0,
                    0.0,
                    1.0,
                )
            )

        # 24-25: target velocity, normalized to the real player's
        # maximum run speed of ~180 px/s (3 px/frame at 60 FPS).
        obs.extend([
            target_velocity_x,
            target_velocity_y,
        ])

        # 26-29: nearest available pickup directions.
        obs.extend([
            health_dx,
            health_dy,
            ammo_dx,
            ammo_dy,
        ])

        # 30-33: weapon-range flags.
        obs.extend([
            1.0 if target_distance <= 75.0 else 0.0,
            1.0 if target_distance <= 110.0 else 0.0,
            1.0 if target_distance <= 200.0 else 0.0,
            1.0 if target_distance <= 280.0 else 0.0,
        ])

        if len(obs) != self.STATE_SIZE:
            raise RuntimeError(
                f"Observation has {len(obs)} values, expected {self.STATE_SIZE}."
            )

        return np.asarray(obs, dtype=np.float32)

    # =====================================================
    # PICKUP DISTANCE / OBSERVATION HELPERS
    # =====================================================

    def _nearest_pickup_distance(self, pickups):
        available = [
            p
            for p in pickups
            if not p["collected"]
        ]

        if not available:
            return 500.0

        bot_x, bot_y = self.bot.center()

        return min(
            math.hypot(
                bot_x - p["x"],
                bot_y - p["y"],
            )
            for p in available
        )

    # =====================================================
    # RAYS
    # =====================================================

    def _ray_distance(
        self,
        start_x,
        start_y,
        direction_x,
        direction_y,
        max_distance,
    ):
        distance = 0.0
        step = 5.0

        while distance <= max_distance:
            x = (
                start_x
                +
                direction_x * distance
            )
            y = (
                start_y
                +
                direction_y * distance
            )

            if self._point_inside_obstacle(
                x,
                y,
            ):
                return distance

            distance += step

        return max_distance

    def _point_inside_obstacle(self, x, y):
        for obstacle in self.obstacles:
            if (
                obstacle["x"] <= x <=
                obstacle["x"] + obstacle["width"]
                and
                obstacle["y"] <= y <=
                obstacle["y"] + obstacle["height"]
            ):
                return True

        return False

    # =====================================================
    # LOS
    # =====================================================

    def _line_of_sight(self):
        if self.target_enemy is None:
            return False

        bot_x, bot_y = self.bot.center()
        target_x, target_y = self.target_enemy.center()

        return self._has_line_of_sight(
            bot_x,
            bot_y,
            target_x,
            target_y,
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
            int(distance / 5.0),
        )

        for i in range(1, steps):
            t = i / steps

            x = (
                x1
                +
                (x2 - x1) * t
            )
            y = (
                y1
                +
                (y2 - y1) * t
            )

            if self._point_inside_obstacle(
                x,
                y,
            ):
                return False

        return True

    # =====================================================
    # DISTANCE
    # =====================================================

    def _distance_bot_target(self):
        if self.target_enemy is None:
            return 500.0

        bot_x, bot_y = self.bot.center()
        target_x, target_y = self.target_enemy.center()

        return math.hypot(
            target_x - bot_x,
            target_y - bot_y,
        )

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize_position_x(self, x):
        denominator = (
            self.MAP_RIGHT -
            self.MAP_LEFT
        )

        if denominator <= 0:
            return 0.0

        normalized = (
            (x - self.MAP_LEFT) /
            denominator
        )

        return float(
            np.clip(
                normalized * 2.0 - 1.0,
                -1.0,
                1.0,
            )
        )

    def _normalize_position_y(self, y):
        denominator = (
            self.MAP_BOTTOM -
            self.MAP_TOP
        )

        if denominator <= 0:
            return 0.0

        normalized = (
            (y - self.MAP_TOP) /
            denominator
        )

        return float(
            np.clip(
                normalized * 2.0 - 1.0,
                -1.0,
                1.0,
            )
        )

    # =====================================================
    # CLAMP
    # =====================================================

    def _clamp_actor(self, actor):
        width = getattr(
            actor,
            "WIDTH",
            40,
        )
        height = getattr(
            actor,
            "HEIGHT",
            40,
        )

        actor.x = float(
            np.clip(
                actor.x,
                self.NAV_LEFT,
                self.NAV_RIGHT - width,
            )
        )

        actor.y = float(
            np.clip(
                actor.y,
                self.NAV_TOP,
                self.NAV_BOTTOM - height,
            )
        )

    # =====================================================
    # INFO
    # =====================================================

    def _info_dict(self, action=None, distance=None):
        if distance is None:
            distance = self._distance_bot_target()

        return {
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
            "melee_attempts": int(
                self.melee_attempts
            ),
            "melee_hits": int(
                self.melee_hits
            ),
            "health_pickups_collected": int(
                self.health_pickups_collected
            ),
            "ammo_pickups_collected": int(
                self.ammo_pickups_collected
            ),
            "enemies_defeated": int(
                self.enemies_defeated_count
            ),
            "active_enemies": int(
                sum(
                    enemy.alive
                    and enemy.health > 0
                    and enemy.pursuing
                    for enemy in self.enemies
                )
            ),
            "alive_enemies": int(
                sum(
                    enemy.alive
                    and enemy.health > 0
                    for enemy in self.enemies
                )
            ),
            "pursuing_enemies": int(
                sum(
                    enemy.alive
                    and enemy.health > 0
                    and enemy.pursuing
                    for enemy in self.enemies
                )
            ),
            "distance": float(distance),
            "line_of_sight": bool(
                self._line_of_sight()
            ),
            "weapon": self.bot.weapon,
            "action": (
                None
                if action is None
                else int(action)
            ),
        }

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):
        pass
