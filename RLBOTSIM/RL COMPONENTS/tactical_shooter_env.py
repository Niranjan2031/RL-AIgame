import gymnasium as gym
from gymnasium import spaces
import numpy as np
import math


class TacticalShooterEnv(gym.Env):
    """
    Gymnasium environment connected to the real PyGame world.

    RL25 VERSION

    Action space:
        0 = idle
        1 = forward
        2 = backward
        3 = left
        4 = right
        5 = sprint
        6 = shoot
        7 = reload
        8 = melee

    Weapon selection is handled automatically according
    to the distance from the player.

    Observation space:
        28 values.

        0  = bot X
        1  = bot Y
        2  = bot health
        3  = bot ammo
        4  = player X
        5  = player Y
        6  = player health
        7  = distance to player
        8  = direction X to player
        9  = direction Y to player
        10 = line of sight
        11 = current weapon
        12 = health pickup available
        13 = ammo pickup available
        14 = distance to health pickup
        15 = distance to ammo pickup
        16 = obstacle distance forward
        17 = obstacle distance backward
        18 = obstacle distance left
        19 = obstacle distance right
        20 = obstacle distance forward-right
        21 = obstacle distance forward-left
        22 = obstacle distance backward-right
        23 = obstacle distance backward-left
        24 = knife range
        25 = shotgun range
        26 = handgun range
        27 = rifle range
    """

    metadata = {
        "render_modes": []
    }

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

    ACTION_SIZE = 9
    STATE_SIZE = 28

    # =========================================================
    # RL25 WEAPON RANGES
    # =========================================================

    KNIFE_RANGE = 75.0
    SHOTGUN_RANGE = 110.0
    HANDGUN_RANGE = 200.0
    RIFLE_RANGE = 280.0

    # =========================================================
    # MAP SETTINGS
    # =========================================================

    TILE_SCALE = 1.638
    MAP_VERTICAL_OFFSET = -30

    # Actual map bounds from the current Tiled map.
    MAP_LEFT = -339.0
    MAP_TOP = -309.0
    MAP_RIGHT = 1338.0
    MAP_BOTTOM = 948.0

    def __init__(self):

        super().__init__()

        # -----------------------------------------------------
        # ACTION SPACE
        # -----------------------------------------------------

        self.action_space = spaces.Discrete(
            self.ACTION_SIZE
        )

        # -----------------------------------------------------
        # OBSERVATION SPACE
        # -----------------------------------------------------

        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(self.STATE_SIZE,),
            dtype=np.float32
        )

        # -----------------------------------------------------
        # EPISODE
        # -----------------------------------------------------

        self.max_steps = 3000
        self.current_step = 0

        # -----------------------------------------------------
        # REAL GAME OBJECTS
        # -----------------------------------------------------

        self.player = None
        self.bot = None

        self.obstacles = []
        self.health_pickups = []
        self.ammo_pickups = []

        # -----------------------------------------------------
        # CALLBACKS
        # -----------------------------------------------------

        self.shoot_callback = None
        self.melee_callback = None
        self.reset_callback = None

        # -----------------------------------------------------
        # PREVIOUS STATE
        # -----------------------------------------------------

        self.previous_bot_health = None
        self.previous_player_health = None

        self.previous_health_pickups = 0
        self.previous_ammo_pickups = 0

        self.previous_distance = None

        # -----------------------------------------------------
        # RL25 REWARD VALUES
        # -----------------------------------------------------

        self.damage_reward_scale = 3.0
        self.successful_hit_reward = 1.0

        self.damage_taken_penalty_scale = 0.75

        self.player_defeat_reward = 100.0
        self.bot_defeat_penalty = 100.0

        self.health_pickup_reward = 2.0
        self.ammo_pickup_reward = 1.0

        self.unsuccessful_shot_penalty = 0.08
        self.weapon_switch_penalty = 0.03

        self.step_penalty = 0.02

        self.engagement_reward = 0.02
        self.far_distance_penalty = 0.02

        # -----------------------------------------------------
        # COMBAT TRACKING
        # -----------------------------------------------------

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False

        self.weapon_switched = False

        self.total_damage_dealt = 0.0
        self.total_damage_taken = 0.0

        self.total_shots_fired = 0
        self.total_shots_hit = 0
        self.total_weapon_switches = 0

    # =========================================================
    # CONNECT REAL GAME STATE
    # =========================================================

    def set_game_state(
        self,
        player,
        bot,
        obstacles=None,
        health_pickups=None,
        ammo_pickups=None,
        shoot_callback=None,
        melee_callback=None,
        reset_callback=None
    ):
        """
        Connect the Gymnasium environment to the actual
        PyGame game objects.
        """

        self.player = player
        self.bot = bot

        self.obstacles = (
            obstacles
            if obstacles is not None
            else []
        )

        self.health_pickups = (
            health_pickups
            if health_pickups is not None
            else []
        )

        self.ammo_pickups = (
            ammo_pickups
            if ammo_pickups is not None
            else []
        )

        self.shoot_callback = shoot_callback
        self.melee_callback = melee_callback
        self.reset_callback = reset_callback

    # =========================================================
    # RESET
    # =========================================================

    def reset(
        self,
        *,
        seed=None,
        options=None
    ):

        super().reset(seed=seed)

        if self.player is None or self.bot is None:

            raise RuntimeError(
                "TacticalShooterEnv is not connected "
                "to the real game. "
                "Call set_game_state() first."
            )

        self.current_step = 0

        # -----------------------------------------------------
        # OPTIONAL RESET CALLBACK
        # -----------------------------------------------------

        if self.reset_callback is not None:

            self.reset_callback(
                self.player,
                self.bot
            )

        # -----------------------------------------------------
        # RL TARGET INFORMATION
        # -----------------------------------------------------

        self.bot.rl_target_weapon = None

        if hasattr(
            self.bot,
            "rl_target_x"
        ):

            self.bot.rl_target_x = None

        if hasattr(
            self.bot,
            "rl_target_y"
        ):

            self.bot.rl_target_y = None

        # -----------------------------------------------------
        # PREVIOUS VALUES
        # -----------------------------------------------------

        self.previous_bot_health = float(
            self.bot.health
        )

        self.previous_player_health = float(
            self.player.health
        )

        self.previous_health_pickups = (
            self._count_available_pickups(
                self.health_pickups
            )
        )

        self.previous_ammo_pickups = (
            self._count_available_pickups(
                self.ammo_pickups
            )
        )

        self.previous_distance = (
            self._distance_to_player()
        )

        # -----------------------------------------------------
        # COMBAT TRACKING
        # -----------------------------------------------------

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False

        self.weapon_switched = False

        self.total_damage_dealt = 0.0
        self.total_damage_taken = 0.0

        self.total_shots_fired = 0
        self.total_shots_hit = 0
        self.total_weapon_switches = 0

        observation = self._get_observation()

        info = {
            "bot_number": getattr(
                self.bot,
                "bot_number",
                None
            ),
            "damage_dealt": 0.0,
            "damage_taken": 0.0,
            "shots_fired": 0,
            "shots_hit": 0,
            "weapon_switches": 0
        }

        return observation, info

    # =========================================================
    # STEP
    # =========================================================

    def step(self, action):

        if self.player is None or self.bot is None:

            raise RuntimeError(
                "TacticalShooterEnv is not connected "
                "to the real game."
            )

        action = int(action)

        if not self.action_space.contains(action):

            raise ValueError(
                f"Invalid RL action: {action}"
            )

        self.current_step += 1

        # Reset per-step combat tracking.

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False

        self.weapon_switched = False

        # -----------------------------------------------------
        # SAVE HEALTH BEFORE ACTION
        # -----------------------------------------------------

        old_player_health = float(
            self.player.health
        )

        old_bot_health = float(
            self.bot.health
        )

        old_weapon = getattr(
            self.bot,
            "weapon",
            None
        )

        # -----------------------------------------------------
        # EXECUTE ACTION
        # -----------------------------------------------------

        self._perform_action(
            action
        )

        # -----------------------------------------------------
        # DETECT DAMAGE
        # -----------------------------------------------------

        new_player_health = float(
            self.player.health
        )

        new_bot_health = float(
            self.bot.health
        )

        # Damage dealt by bot.

        damage_dealt = max(
            0.0,
            old_player_health
            - new_player_health
        )

        # Damage taken by bot.

        damage_taken = max(
            0.0,
            old_bot_health
            - new_bot_health
        )

        self.last_damage_dealt = (
            damage_dealt
        )

        self.last_damage_taken = (
            damage_taken
        )

        self.total_damage_dealt += (
            damage_dealt
        )

        self.total_damage_taken += (
            damage_taken
        )

        # -----------------------------------------------------
        # DETECT WEAPON SWITCH
        # -----------------------------------------------------

        new_weapon = getattr(
            self.bot,
            "weapon",
            None
        )

        if (
            old_weapon is not None
            and new_weapon is not None
            and old_weapon != new_weapon
        ):

            self.weapon_switched = True

            self.total_weapon_switches += 1

        # -----------------------------------------------------
        # REWARD
        # -----------------------------------------------------

        reward = 0.0

        # Damage reward.

        reward += (
            self.damage_reward_scale
            * damage_dealt
        )

        # Successful hit reward.

        if damage_dealt > 0:

            self.last_shot_hit = True

            reward += (
                self.successful_hit_reward
            )

            self.total_shots_hit += 1

        # -----------------------------------------------------
        # UNSUCCESSFUL SHOOT
        # -----------------------------------------------------

        if (
            action == self.ACTION_SHOOT
            and damage_dealt <= 0
        ):

            reward -= (
                self.unsuccessful_shot_penalty
            )

        # -----------------------------------------------------
        # DAMAGE TAKEN
        # -----------------------------------------------------

        reward -= (
            self.damage_taken_penalty_scale
            * damage_taken
        )

        # -----------------------------------------------------
        # WEAPON SWITCH
        # -----------------------------------------------------

        if self.weapon_switched:

            reward -= (
                self.weapon_switch_penalty
            )

        # -----------------------------------------------------
        # PICKUPS
        # -----------------------------------------------------

        health_reward = (
            self._calculate_health_pickup_reward()
        )

        ammo_reward = (
            self._calculate_ammo_pickup_reward()
        )

        reward += health_reward
        reward += ammo_reward

        # -----------------------------------------------------
        # DISTANCE SHAPING
        # -----------------------------------------------------

        current_distance = (
            self._distance_to_player()
        )

        if self.previous_distance is not None:

            distance_change = (
                self.previous_distance
                - current_distance
            )

            reward += (
                0.01
                * np.clip(
                    distance_change,
                    -5.0,
                    5.0
                )
            )

        self.previous_distance = (
            current_distance
        )

        # -----------------------------------------------------
        # ENGAGEMENT REWARD
        # -----------------------------------------------------

        if (
            current_distance <= self.RIFLE_RANGE
            and self._has_line_of_sight()
        ):

            reward += (
                self.engagement_reward
            )

        # -----------------------------------------------------
        # FAR DISTANCE PENALTY
        # -----------------------------------------------------

        if current_distance > 350:

            reward -= (
                self.far_distance_penalty
            )

        # -----------------------------------------------------
        # STEP PENALTY
        # -----------------------------------------------------

        reward -= self.step_penalty

        # -----------------------------------------------------
        # TERMINATION
        # -----------------------------------------------------

        terminated = False

        if self.player.health <= 0:

            self.player.health = 0

            reward += (
                self.player_defeat_reward
            )

            terminated = True

        elif self.bot.health <= 0:

            self.bot.health = 0

            reward -= (
                self.bot_defeat_penalty
            )

            terminated = True

        # -----------------------------------------------------
        # TIME LIMIT
        # -----------------------------------------------------

        truncated = (
            self.current_step
            >= self.max_steps
        )

        observation = (
            self._get_observation()
        )

        info = {
            "bot_number": getattr(
                self.bot,
                "bot_number",
                None
            ),
            "damage_dealt": float(
                self.last_damage_dealt
            ),
            "damage_taken": float(
                self.last_damage_taken
            ),
            "shots_fired": int(
                self.total_shots_fired
            ),
            "shots_hit": int(
                self.total_shots_hit
            ),
            "weapon_switches": int(
                self.total_weapon_switches
            )
        }

        return (
            observation,
            float(reward),
            terminated,
            truncated,
            info
        )

    # =========================================================
    # PERFORM ACTION
    # =========================================================

    def _perform_action(
        self,
        action
    ):

        if not getattr(
            self.bot,
            "alive",
            True
        ):

            return

        # -----------------------------------------------------
        # TARGET PLAYER
        # -----------------------------------------------------

        player_x, player_y = (
            self._get_center(
                self.player
            )
        )

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        dx = player_x - bot_x
        dy = player_y - bot_y

        distance = math.hypot(
            dx,
            dy
        )

        # -----------------------------------------------------
        # FACE PLAYER
        # -----------------------------------------------------

        if distance > 0:

            if hasattr(
                self.bot,
                "aim_at"
            ):

                self.bot.aim_at(
                    player_x,
                    player_y
                )

        # -----------------------------------------------------
        # IDLE
        # -----------------------------------------------------

        if action == self.ACTION_IDLE:

            return

        # -----------------------------------------------------
        # FORWARD
        # -----------------------------------------------------

        if action == self.ACTION_FORWARD:

            self._move_bot(
                dx,
                dy,
                getattr(
                    self.bot,
                    "speed",
                    2.3
                )
            )

            return

        # -----------------------------------------------------
        # BACKWARD
        # -----------------------------------------------------

        if action == self.ACTION_BACKWARD:

            self._move_bot(
                -dx,
                -dy,
                getattr(
                    self.bot,
                    "speed",
                    2.3
                )
            )

            return

        # -----------------------------------------------------
        # LEFT
        # -----------------------------------------------------

        if action == self.ACTION_LEFT:

            self._move_bot(
                -dy,
                dx,
                getattr(
                    self.bot,
                    "speed",
                    2.3
                )
            )

            return

        # -----------------------------------------------------
        # RIGHT
        # -----------------------------------------------------

        if action == self.ACTION_RIGHT:

            self._move_bot(
                dy,
                -dx,
                getattr(
                    self.bot,
                    "speed",
                    2.3
                )
            )

            return

        # -----------------------------------------------------
        # SPRINT
        # -----------------------------------------------------

        if action == self.ACTION_SPRINT:

            self._move_bot(
                dx,
                dy,
                getattr(
                    self.bot,
                    "run_speed",
                    3.0
                )
            )

            return

        # -----------------------------------------------------
        # SHOOT
        # -----------------------------------------------------

        if action == self.ACTION_SHOOT:

            self._execute_shoot(
                distance
            )

            return

        # -----------------------------------------------------
        # RELOAD
        # -----------------------------------------------------

        if action == self.ACTION_RELOAD:

            if hasattr(
                self.bot,
                "reload"
            ):

                self.bot.reload()

            elif hasattr(
                self.bot,
                "start_reload"
            ):

                self.bot.start_reload()

            return

        # -----------------------------------------------------
        # MELEE
        # -----------------------------------------------------

        if action == self.ACTION_MELEE:

            self._execute_melee(
                distance
            )

            return

    # =========================================================
    # MOVEMENT
    # =========================================================

    def _move_bot(
        self,
        dx,
        dy,
        speed
    ):

        if hasattr(
            self.bot,
            "move"
        ):

            # RLBot.move() accepts:
            # dx, dy, obstacles, speed

            try:

                self.bot.move(
                    dx,
                    dy,
                    self.obstacles,
                    speed
                )

            except TypeError:

                try:

                    self.bot.move(
                        dx,
                        dy,
                        self.obstacles
                    )

                except TypeError:

                    self.bot.move(
                        dx,
                        dy,
                        speed
                    )

        self._clamp_bot()

    # =========================================================
    # SHOOT
    # =========================================================

    def _execute_shoot(
        self,
        distance
    ):

        # -----------------------------------------------------
        # AUTOMATIC WEAPON SELECTION
        # -----------------------------------------------------

        self._select_combat_weapon(
            distance
        )

        # -----------------------------------------------------
        # AIM
        # -----------------------------------------------------

        player_x, player_y = (
            self._get_center(
                self.player
            )
        )

        if hasattr(
            self.bot,
            "aim_at"
        ):

            self.bot.aim_at(
                player_x,
                player_y
            )

        # -----------------------------------------------------
        # FIRE
        # -----------------------------------------------------

        old_health = float(
            self.player.health
        )

        fired = False

        if hasattr(
            self.bot,
            "shoot"
        ):

            fired = bool(
                self.bot.shoot()
            )

        if fired:

            self.last_shot_fired = True

            self.total_shots_fired += 1

        # -----------------------------------------------------
        # GAME CALLBACK
        # -----------------------------------------------------

        if (
            fired
            and self.shoot_callback is not None
        ):

            self.shoot_callback(
                self.bot
            )

        # -----------------------------------------------------
        # CHECK IMMEDIATE DAMAGE
        # -----------------------------------------------------

        new_health = float(
            self.player.health
        )

        if new_health < old_health:

            self.last_shot_hit = True

    # =========================================================
    # MELEE
    # =========================================================

    def _execute_melee(
        self,
        distance
    ):

        # Melee range.

        if distance > self.KNIFE_RANGE:

            return

        # -----------------------------------------------------
        # EQUIP KNIFE
        # -----------------------------------------------------

        if hasattr(
            self.bot,
            "set_weapon"
        ):

            self.bot.set_weapon(
                "knife"
            )

        elif hasattr(
            self.bot,
            "equip"
        ):

            self.bot.equip(
                "knife"
            )

        # -----------------------------------------------------
        # AIM
        # -----------------------------------------------------

        player_x, player_y = (
            self._get_center(
                self.player
            )
        )

        if hasattr(
            self.bot,
            "aim_at"
        ):

            self.bot.aim_at(
                player_x,
                player_y
            )

        old_health = float(
            self.player.health
        )

        # -----------------------------------------------------
        # MELEE
        # -----------------------------------------------------

        fired = False

        if hasattr(
            self.bot,
            "melee"
        ):

            fired = bool(
                self.bot.melee()
            )

        # -----------------------------------------------------
        # GAME CALLBACK
        # -----------------------------------------------------

        if (
            fired
            and self.melee_callback is not None
        ):

            self.melee_callback(
                self.bot
            )

        # -----------------------------------------------------
        # IMMEDIATE DAMAGE
        # -----------------------------------------------------

        new_health = float(
            self.player.health
        )

        if new_health < old_health:

            self.last_damage_dealt = (
                old_health
                - new_health
            )

    # =========================================================
    # AUTOMATIC WEAPON SELECTION
    # =========================================================

    def _select_combat_weapon(
        self,
        distance
    ):

        # -----------------------------------------------------
        # DETERMINE PREFERRED WEAPON
        # -----------------------------------------------------

        if distance <= self.KNIFE_RANGE:

            preferred = "knife"

        elif distance <= self.SHOTGUN_RANGE:

            preferred = "shotgun"

        elif distance <= self.HANDGUN_RANGE:

            preferred = "handgun"

        else:

            preferred = "rifle"

        # -----------------------------------------------------
        # FALLBACK IF FIREARM EMPTY
        # -----------------------------------------------------

        if preferred != "knife":

            ammo = self._get_weapon_ammo(
                preferred
            )

            if ammo is not None and ammo <= 0:

                alternatives = [
                    "shotgun",
                    "handgun",
                    "rifle"
                ]

                available = []

                for weapon in alternatives:

                    weapon_ammo = (
                        self._get_weapon_ammo(
                            weapon
                        )
                    )

                    if (
                        weapon_ammo is not None
                        and weapon_ammo > 0
                    ):

                        available.append(
                            weapon
                        )

                if available:

                    available.sort(
                        key=lambda weapon:
                        abs(
                            self._weapon_range(
                                weapon
                            )
                            - distance
                        )
                    )

                    preferred = available[0]

        # -----------------------------------------------------
        # EQUIP
        # -----------------------------------------------------

        current_weapon = getattr(
            self.bot,
            "weapon",
            None
        )

        if current_weapon != preferred:

            changed = False

            if hasattr(
                self.bot,
                "set_weapon"
            ):

                changed = bool(
                    self.bot.set_weapon(
                        preferred
                    )
                )

            elif hasattr(
                self.bot,
                "equip"
            ):

                changed = bool(
                    self.bot.equip(
                        preferred
                    )
                )

            if changed:

                self.weapon_switched = True
                self.total_weapon_switches += 1

        self.bot.rl_target_weapon = (
            preferred
        )

    # =========================================================
    # WEAPON RANGE
    # =========================================================

    def _weapon_range(
        self,
        weapon
    ):

        ranges = {
            "knife": self.KNIFE_RANGE,
            "shotgun": self.SHOTGUN_RANGE,
            "handgun": self.HANDGUN_RANGE,
            "rifle": self.RIFLE_RANGE
        }

        return ranges.get(
            weapon,
            self.HANDGUN_RANGE
        )

    # =========================================================
    # WEAPON AMMO
    # =========================================================

    def _get_weapon_ammo(
        self,
        weapon
    ):

        if weapon == "knife":

            return None

        if hasattr(
            self.bot,
            "weapon_ammo"
        ):

            return self.bot.weapon_ammo.get(
                weapon,
                0
            )

        if getattr(
            self.bot,
            "weapon",
            None
        ) == weapon:

            if hasattr(
                self.bot,
                "current_ammo"
            ):

                return self.bot.current_ammo()

        return 0

    # =========================================================
    # OBSERVATION
    # =========================================================

    def _get_observation(self):

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        player_x, player_y = (
            self._get_center(
                self.player
            )
        )

        dx = player_x - bot_x
        dy = player_y - bot_y

        distance = math.hypot(
            dx,
            dy
        )

        # -----------------------------------------------------
        # 0-1 BOT POSITION
        # -----------------------------------------------------

        bot_x_norm = self._normalize_x(
            bot_x
        )

        bot_y_norm = self._normalize_y(
            bot_y
        )

        # -----------------------------------------------------
        # PLAYER DIRECTION
        # -----------------------------------------------------

        direction_x = np.clip(
            dx / 500.0,
            -1.0,
            1.0
        )

        direction_y = np.clip(
            dy / 500.0,
            -1.0,
            1.0
        )

        # -----------------------------------------------------
        # HEALTH
        # -----------------------------------------------------

        bot_max_health = getattr(
            self.bot,
            "max_health",
            30
        )

        player_max_health = getattr(
            self.player,
            "max_health",
            30
        )

        bot_health = np.clip(
            self.bot.health
            / max(
                1.0,
                bot_max_health
            ),
            0.0,
            1.0
        )

        player_health = np.clip(
            self.player.health
            / max(
                1.0,
                player_max_health
            ),
            0.0,
            1.0
        )

        # -----------------------------------------------------
        # AMMO
        # -----------------------------------------------------

        ammo = self._get_current_ammo()

        if ammo is None:

            ammo_normalized = 1.0

        else:

            max_ammo = self._get_current_max_ammo()

            if max_ammo <= 0:

                ammo_normalized = 0.0

            else:

                ammo_normalized = np.clip(
                    ammo / max_ammo,
                    0.0,
                    1.0
                )

        # -----------------------------------------------------
        # CURRENT WEAPON
        # -----------------------------------------------------

        weapon = getattr(
            self.bot,
            "weapon",
            "handgun"
        )

        weapon_encoding = {
            "handgun": 0.0,
            "shotgun": 0.33,
            "rifle": 0.66,
            "knife": 1.0
        }

        current_weapon = (
            weapon_encoding.get(
                weapon,
                0.0
            )
        )

        # -----------------------------------------------------
        # LINE OF SIGHT
        # -----------------------------------------------------

        line_of_sight = (
            1.0
            if self._has_line_of_sight()
            else 0.0
        )

        # -----------------------------------------------------
        # PICKUPS
        # -----------------------------------------------------

        health_available = (
            1.0
            if self._count_available_pickups(
                self.health_pickups
            ) > 0
            else 0.0
        )

        ammo_available = (
            1.0
            if self._count_available_pickups(
                self.ammo_pickups
            ) > 0
            else 0.0
        )

        health_distance = (
            self._nearest_pickup_distance(
                self.health_pickups
            )
        )

        ammo_distance = (
            self._nearest_pickup_distance(
                self.ammo_pickups
            )
        )

        health_distance = np.clip(
            health_distance / 500.0,
            0.0,
            1.0
        )

        ammo_distance = np.clip(
            ammo_distance / 500.0,
            0.0,
            1.0
        )

        # -----------------------------------------------------
        # OBSTACLE RAYS
        # -----------------------------------------------------

        obstacle_distances = (
            self._get_obstacle_distances()
        )

        # -----------------------------------------------------
        # RL25 RANGE FLAGS
        # -----------------------------------------------------

        knife_range = (
            1.0
            if distance <= self.KNIFE_RANGE
            else 0.0
        )

        shotgun_range = (
            1.0
            if distance <= self.SHOTGUN_RANGE
            else 0.0
        )

        handgun_range = (
            1.0
            if distance <= self.HANDGUN_RANGE
            else 0.0
        )

        rifle_range = (
            1.0
            if distance <= self.RIFLE_RANGE
            else 0.0
        )

        # -----------------------------------------------------
        # 28 OBSERVATIONS
        # -----------------------------------------------------

        observation = [

            # 0
            bot_x_norm,

            # 1
            bot_y_norm,

            # 2
            bot_health,

            # 3
            ammo_normalized,

            # 4
            self._normalize_x(
                player_x
            ),

            # 5
            self._normalize_y(
                player_y
            ),

            # 6
            player_health,

            # 7
            np.clip(
                distance / 500.0,
                0.0,
                1.0
            ),

            # 8
            direction_x,

            # 9
            direction_y,

            # 10
            line_of_sight,

            # 11
            current_weapon,

            # 12
            health_available,

            # 13
            ammo_available,

            # 14
            health_distance,

            # 15
            ammo_distance,

            # 16-23
            *obstacle_distances,

            # 24
            knife_range,

            # 25
            shotgun_range,

            # 26
            handgun_range,

            # 27
            rifle_range
        ]

        if len(observation) != self.STATE_SIZE:

            raise RuntimeError(
                "Observation size mismatch: "
                f"{len(observation)} "
                f"instead of "
                f"{self.STATE_SIZE}"
            )

        return np.asarray(
            observation,
            dtype=np.float32
        )

    # =========================================================
    # OBSTACLE DISTANCES
    # =========================================================

    def _get_obstacle_distances(self):

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        directions = [

            # Forward
            (1.0, 0.0),

            # Backward
            (-1.0, 0.0),

            # Left
            (0.0, 1.0),

            # Right
            (0.0, -1.0),

            # Forward-right
            (0.707, -0.707),

            # Forward-left
            (0.707, 0.707),

            # Backward-right
            (-0.707, -0.707),

            # Backward-left
            (-0.707, 0.707)
        ]

        values = []

        for dx, dy in directions:

            distance = (
                self._ray_distance(
                    bot_x,
                    bot_y,
                    dx,
                    dy,
                    200.0
                )
            )

            values.append(
                np.clip(
                    distance / 200.0,
                    0.0,
                    1.0
                )
            )

        return values

    # =========================================================
    # RAY DISTANCE
    # =========================================================

    def _ray_distance(
        self,
        start_x,
        start_y,
        direction_x,
        direction_y,
        max_distance
    ):

        step = 5.0

        distance = 0.0

        while distance <= max_distance:

            x = (
                start_x
                + direction_x * distance
            )

            y = (
                start_y
                + direction_y * distance
            )

            if self._point_inside_obstacle(
                x,
                y
            ):

                return distance

            distance += step

        return max_distance

    # =========================================================
    # POINT INSIDE OBSTACLE
    # =========================================================

    def _point_inside_obstacle(
        self,
        x,
        y
    ):

        for obstacle in self.obstacles:

            if isinstance(
                obstacle,
                dict
            ):

                ox = obstacle["x"]
                oy = obstacle["y"]
                ow = obstacle["width"]
                oh = obstacle["height"]

            else:

                ox = obstacle.x
                oy = obstacle.y
                ow = obstacle.width
                oh = obstacle.height

            if (
                ox <= x <= ox + ow
                and
                oy <= y <= oy + oh
            ):

                return True

        return False

    # =========================================================
    # LINE OF SIGHT
    # =========================================================

    def _has_line_of_sight(self):

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        player_x, player_y = (
            self._get_center(
                self.player
            )
        )

        return self._line_of_sight_between(
            bot_x,
            bot_y,
            player_x,
            player_y
        )

    def _line_of_sight_between(
        self,
        x1,
        y1,
        x2,
        y2
    ):

        dx = x2 - x1
        dy = y2 - y1

        distance = math.hypot(
            dx,
            dy
        )

        if distance <= 0:

            return True

        steps = max(
            1,
            int(distance / 5.0)
        )

        for i in range(
            1,
            steps
        ):

            t = i / steps

            x = x1 + dx * t
            y = y1 + dy * t

            if self._point_inside_obstacle(
                x,
                y
            ):

                return False

        return True

    # =========================================================
    # PICKUP REWARD
    # =========================================================

    def _calculate_health_pickup_reward(self):

        current = (
            self._count_available_pickups(
                self.health_pickups
            )
        )

        reward = 0.0

        if current < self.previous_health_pickups:

            reward = (
                self.health_pickup_reward
            )

        self.previous_health_pickups = current

        return reward

    def _calculate_ammo_pickup_reward(self):

        current = (
            self._count_available_pickups(
                self.ammo_pickups
            )
        )

        reward = 0.0

        if current < self.previous_ammo_pickups:

            reward = (
                self.ammo_pickup_reward
            )

        self.previous_ammo_pickups = current

        return reward

    # =========================================================
    # COUNT PICKUPS
    # =========================================================

    def _count_available_pickups(
        self,
        pickups
    ):

        count = 0

        for pickup in pickups:

            if isinstance(
                pickup,
                dict
            ):

                if not pickup.get(
                    "collected",
                    False
                ):

                    count += 1

            else:

                # Existing game pickup objects
                # may not use a collected flag.

                if getattr(
                    pickup,
                    "collected",
                    False
                ):

                    continue

                count += 1

        return count

    # =========================================================
    # NEAREST PICKUP
    # =========================================================

    def _nearest_pickup_distance(
        self,
        pickups
    ):

        if not pickups:

            return 500.0

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        nearest = 500.0

        for pickup in pickups:

            if isinstance(
                pickup,
                dict
            ):

                if pickup.get(
                    "collected",
                    False
                ):

                    continue

                px = pickup.get(
                    "x",
                    0
                )

                py = pickup.get(
                    "y",
                    0
                )

                # Pickup coordinates are already
                # world/screen coordinates.

                pickup_x = (
                    px + 8 * self.TILE_SCALE / 2
                )

                pickup_y = (
                    py + 8 * self.TILE_SCALE / 2
                )

            else:

                if getattr(
                    pickup,
                    "collected",
                    False
                ):

                    continue

                if hasattr(
                    pickup,
                    "rect"
                ):

                    pickup_x = pickup.rect.centerx
                    pickup_y = pickup.rect.centery

                elif hasattr(
                    pickup,
                    "x"
                ):

                    pickup_x = pickup.x
                    pickup_y = pickup.y

                else:

                    continue

            distance = math.hypot(
                pickup_x - bot_x,
                pickup_y - bot_y
            )

            nearest = min(
                nearest,
                distance
            )

        return nearest

    # =========================================================
    # GET CENTER
    # =========================================================

    def _get_center(
        self,
        obj
    ):

        if hasattr(
            obj,
            "get_center"
        ):

            try:

                return obj.get_center()

            except Exception:
                pass

        if hasattr(
            obj,
            "center"
        ):

            try:

                result = obj.center()

                if (
                    isinstance(
                        result,
                        tuple
                    )
                    and len(result) == 2
                ):

                    return result

            except Exception:
                pass

        width = getattr(
            obj,
            "width",
            40
        )

        height = getattr(
            obj,
            "height",
            40
        )

        x = getattr(
            obj,
            "x",
            0
        )

        y = getattr(
            obj,
            "y",
            0
        )

        return (
            x + width / 2,
            y + height / 2
        )

    # =========================================================
    # CURRENT AMMO
    # =========================================================

    def _get_current_ammo(self):

        weapon = getattr(
            self.bot,
            "weapon",
            "handgun"
        )

        if weapon == "knife":

            return None

        if hasattr(
            self.bot,
            "weapon_ammo"
        ):

            return self.bot.weapon_ammo.get(
                weapon,
                0
            )

        if hasattr(
            self.bot,
            "current_ammo"
        ):

            return self.bot.current_ammo()

        return 0

    # =========================================================
    # CURRENT MAX AMMO
    # =========================================================

    def _get_current_max_ammo(self):

        weapon = getattr(
            self.bot,
            "weapon",
            "handgun"
        )

        if weapon == "knife":

            return 1

        if hasattr(
            self.bot,
            "WEAPON_STATS"
        ):

            stats = self.bot.WEAPON_STATS.get(
                weapon
            )

            if stats is not None:

                max_ammo = stats.get(
                    "max_ammo"
                )

                if max_ammo is not None:

                    return max_ammo

        if hasattr(
            self.bot,
            "max_ammo"
        ):

            try:

                value = self.bot.max_ammo()

                if value is not None:

                    return value

            except Exception:
                pass

        defaults = {
            "handgun": 12,
            "shotgun": 6,
            "rifle": 30
        }

        return defaults.get(
            weapon,
            12
        )

    # =========================================================
    # DISTANCE TO PLAYER
    # =========================================================

    def _distance_to_player(self):

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        player_x, player_y = (
            self._get_center(
                self.player
            )
        )

        return math.hypot(
            player_x - bot_x,
            player_y - bot_y
        )

    # =========================================================
    # NORMALIZE X
    # =========================================================

    def _normalize_x(
        self,
        x
    ):

        value = (
            (
                x
                - self.MAP_LEFT
            )
            /
            (
                self.MAP_RIGHT
                - self.MAP_LEFT
            )
        )

        return float(
            np.clip(
                value,
                0.0,
                1.0
            )
        )

    # =========================================================
    # NORMALIZE Y
    # =========================================================

    def _normalize_y(
        self,
        y
    ):

        value = (
            (
                y
                - self.MAP_TOP
            )
            /
            (
                self.MAP_BOTTOM
                - self.MAP_TOP
            )
        )

        return float(
            np.clip(
                value,
                0.0,
                1.0
            )
        )

    # =========================================================
    # CLAMP BOT
    # =========================================================

    def _clamp_bot(self):

        width = getattr(
            self.bot,
            "width",
            40
        )

        height = getattr(
            self.bot,
            "height",
            40
        )

        self.bot.x = max(
            self.MAP_LEFT,
            min(
                self.bot.x,
                self.MAP_RIGHT - width
            )
        )

        self.bot.y = max(
            self.MAP_TOP,
            min(
                self.bot.y,
                self.MAP_BOTTOM - height
            )
        )

        if hasattr(
            self.bot,
            "rect"
        ):

            self.bot.rect.topleft = (
                int(self.bot.x),
                int(self.bot.y)
            )

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        pass