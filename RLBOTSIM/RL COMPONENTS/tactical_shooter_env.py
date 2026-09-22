import gymnasium as gym
from gymnasium import spaces

import numpy as np
import math


class TacticalShooterEnv(gym.Env):
    """
    Gymnasium environment connected to the REAL PyGame world.

    RL25 DEPLOYMENT VERSION

    IMPORTANT:
        This environment MUST produce the exact same observation
        contract used by HeadlessShooterEnv during RL25 training.

    =========================================================
    ACTION SPACE
    =========================================================

        0 = idle
        1 = forward
        2 = backward
        3 = left
        4 = right
        5 = sprint
        6 = shoot
        7 = reload
        8 = melee

    =========================================================
    OBSERVATION SPACE
    =========================================================

    FINAL 34-DIMENSION RL / HEADLESS ORDER:

        0  = bot X
        1  = bot Y

        2  = dx to player
        3  = dy to player
        4  = distance to player

        5  = bot health
        6  = player health
        7  = current ammo

        8  = weapon encoding

        9  = bot facing X
        10 = bot facing Y

        11 = line of sight

        12 = health pickup distance
        13 = ammo pickup distance

        14 = health pickup available
        15 = ammo pickup available

        16-23 = obstacle ray distances

        24 = enemy velocity X
        25 = enemy velocity Y
        26 = health pickup dx
        27 = health pickup dy
        28 = ammo pickup dx
        29 = ammo pickup dy
        30 = knife range flag
        31 = shotgun range flag
        32 = handgun range flag
        33 = rifle range flag

    This ordering MUST NOT be changed without retraining
    the DQN model.

    =========================================================
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
    STATE_SIZE = 34

    # =========================================================
    # RL25 WEAPON RANGES
    # =========================================================

    KNIFE_RANGE = 75.0
    SHOTGUN_RANGE = 110.0
    HANDGUN_RANGE = 200.0
    RIFLE_RANGE = 280.0

    # =========================================================
    # TRAINING-COMPATIBLE WEAPON SWITCH COOLDOWN
    # =========================================================
    #
    # HeadlessShooterEnv uses this to stop the agent from
    # rapidly oscillating between knife and firearms.
    #
    # The deployed environment must behave similarly.
    # =========================================================

    WEAPON_SWITCH_COOLDOWN = 0.8

    # =========================================================
    # RL25 TRAINING TIMING
    # =========================================================
    # HeadlessShooterEnv uses 1 RL step = 0.1 second.
    # The rendered game runs at 60 FPS, so one RL action is
    # applied once every 6 rendered frames.
    # =========================================================

    RL_STEP_DT = 0.1
    GAME_FRAME_DT = 1.0 / 60.0
    RL_FRAMES_PER_STEP = int(round(RL_STEP_DT / GAME_FRAME_DT))

    # =========================================================
    # MAP SETTINGS
    #
    # These are the actual bounds used by the current map.
    # main.py also calculates these dynamically.
    # =========================================================

    TILE_SCALE = 1.638
    MAP_VERTICAL_OFFSET = -30

    MAP_LEFT = -339.0
    MAP_TOP = -309.0
    MAP_RIGHT = 1338.0
    MAP_BOTTOM = 948.0

    PLAYABLE_LEFT = 0.0
    PLAYABLE_TOP = 0.0
    PLAYABLE_RIGHT = 1000.0
    PLAYABLE_BOTTOM = 700.0

    # =========================================================
    # OBSERVATION SETTINGS
    # =========================================================

    POSITION_NORMALIZATION_LOW = -1.0
    POSITION_NORMALIZATION_HIGH = 1.0

    MAX_RELATIVE_DISTANCE = 500.0
    MAX_RAY_DISTANCE = 200.0
    RAY_STEP = 5.0

    # =========================================================
    # INITIALIZATION
    # =========================================================

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
        self.previous_health_pickup_distance = 500.0
        self.previous_ammo_pickup_distance = 500.0

        # Target velocity is measured once per real RL interval
        # (0.1 s / 6 render frames), matching HeadlessShooterEnv.
        # Intermediate render-frame observations keep the last
        # completed RL-step velocity instead of producing a
        # frame-by-frame /6 scaling error.
        self.previous_player_center = None
        self.target_velocity_x = 0.0
        self.target_velocity_y = 0.0

        # -----------------------------------------------------
        # REWARD SETTINGS
        #
        # These preserve the current RL25 reward structure.
        # They are primarily useful for diagnostics because
        # main.py runs the trained model with training=False.
        # -----------------------------------------------------

        self.damage_reward_scale = 3.0
        self.successful_hit_reward = 1.0

        self.damage_taken_penalty_scale = 0.75

        self.player_defeat_reward = 100.0
        self.bot_defeat_penalty = 100.0

        self.health_pickup_reward = 0.0  # tiered in _collect_bot_pickups
        self.ammo_pickup_reward = 0.0    # tiered in _collect_bot_pickups

        self.unsuccessful_shot_penalty = 0.0
        self.weapon_switch_penalty = 0.05

        self.step_penalty = 0.01

        self.engagement_reward = 0.05
        self.far_distance_penalty = 0.03

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
        self.total_melee_attempts = 0
        self.total_melee_hits = 0
        self.total_weapon_switches = 0

        # -----------------------------------------------------
        # WEAPON SWITCH TIMER
        # -----------------------------------------------------

        self.weapon_switch_timer = 0.0

        # -----------------------------------------------------
        # RANGE MILESTONES
        #
        # Not required for inference, but kept for reward
        # compatibility with the RL25 training environment.
        # -----------------------------------------------------

        self.range_milestones = {
            350.0: False,
            280.0: False,
            200.0: False,
            110.0: False,
            75.0: False
        }

        # -----------------------------------------------------
        # TERMINAL STATE
        # -----------------------------------------------------

        self.player_defeated = False
        self.bot_defeated = False

        # -----------------------------------------------------
        # PER-STEP SWITCH COUNT
        # -----------------------------------------------------

        self._step_weapon_switches = 0

        # main.py calls env.step() once per rendered frame.
        # Bridge those 60 FPS calls to the 0.1 s RL25 timestep.
        # Start at threshold so the first action executes immediately.
        self._rl_frame_count = self.RL_FRAMES_PER_STEP - 1

        # Action currently being held between RL decisions.
        # Movement is applied every rendered frame at 1/6 of the
        # RL-step movement, so the bot moves smoothly while the
        # total displacement over 0.1 s remains training-equivalent.
        self._active_action = self.ACTION_IDLE

        # Pickups are checked on every rendered frame, just like the
        # six-frame Headless simulation. Their reward is accumulated
        # until the next real RL decision boundary.
        self._pending_pickup_reward = 0.0

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
        Connect this environment to the real PyGame world.

        No second game world is created.

        main.py passes:
            player
            RL bot
            obstacles
            health pickups
            ammo pickups
            shooting callback
            melee callback
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

        super().reset(
            seed=seed
        )

        if self.player is None or self.bot is None:

            raise RuntimeError(
                "TacticalShooterEnv is not connected "
                "to the real game. "
                "Call set_game_state() first."
            )

        self.current_step = 0

        # First post-reset action executes immediately.
        self._rl_frame_count = self.RL_FRAMES_PER_STEP - 1
        self._active_action = self.ACTION_IDLE
        self._pending_pickup_reward = 0.0

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

        if hasattr(
            self.bot,
            "rl_target_weapon"
        ):

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
        # WEAPON SWITCH TIMER
        # -----------------------------------------------------

        self.weapon_switch_timer = 0.0

        # -----------------------------------------------------
        # PREVIOUS VALUES
        # -----------------------------------------------------

        self.previous_bot_health = float(
            getattr(
                self.bot,
                "health",
                0.0
            )
        )

        self.previous_player_health = float(
            getattr(
                self.player,
                "health",
                0.0
            )
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

        player_cx, player_cy = self._get_center(self.player)
        self.previous_player_center = (player_cx, player_cy)

        self.target_velocity_x = 0.0
        self.target_velocity_y = 0.0

        self.previous_health_pickup_distance = self._nearest_needed_pickup_distance(
            self.health_pickups,
        )
        self.previous_ammo_pickup_distance = self._nearest_needed_pickup_distance(
            self.ammo_pickups,
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
        self.total_melee_attempts = 0
        self.total_melee_hits = 0
        self.total_weapon_switches = 0

        # -----------------------------------------------------
        # RANGE MILESTONES
        # -----------------------------------------------------

        self.range_milestones = {
            350.0: False,
            280.0: False,
            200.0: False,
            110.0: False,
            75.0: False
        }

        self.player_defeated = False
        self.bot_defeated = False

        self._step_weapon_switches = 0

        # -----------------------------------------------------
        # INITIAL OBSERVATION
        # -----------------------------------------------------

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

        return (
            observation,
            info
        )

    # =========================================================
    # STEP
    # =========================================================

    def needs_new_action(self):
        """
        True only on the rendered frame where a new RL action
        should be selected.

        The game still runs at 60 FPS, while RL25 decisions
        occur every 0.1 s (6 frames).
        """
        return (
            self._rl_frame_count
            >= self.RL_FRAMES_PER_STEP - 1
        )

    def step(
        self,
        action
    ):

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

        # -----------------------------------------------------
        # 60 FPS GAME -> 0.1 s RL25 STEP BRIDGE
        # -----------------------------------------------------
        # main.py calls this once per rendered frame. Execute the
        # RL action only every 6 frames: 6/60 = 0.1 seconds.
        # Intermediate calls do not move, shoot, reload, or switch
        # the RL bot. This makes each actual RL step equivalent to
        # one HeadlessShooterEnv step.
        # -----------------------------------------------------

        self._rl_frame_count += 1

        if self._rl_frame_count < self.RL_FRAMES_PER_STEP:

            # Keep the last RL movement action active between decisions.
            # This removes the visible stop-start/stutter while preserving
            # the same total movement distance as one Headless 0.1 s step.
            if self._active_action in (
                self.ACTION_FORWARD,
                self.ACTION_BACKWARD,
                self.ACTION_LEFT,
                self.ACTION_RIGHT,
                self.ACTION_SPRINT
            ):
                self._perform_action(
                    self._active_action,
                    movement_scale=(1.0 / self.RL_FRAMES_PER_STEP),
                    combat=False
                )

            # Headless checks pickup overlap on every simulated
            # 60-FPS frame. Do the same in the real game and carry
            # the reward to the next RL decision.
            self._pending_pickup_reward += (
                self._collect_bot_pickups()
            )

            observation = self._get_observation()

            terminated = (
                getattr(self.player, "health", 0) <= 0
                or not getattr(self.bot, "alive", True)
            )

            truncated = self.current_step >= self.max_steps

            info = {
                "bot_number": getattr(self.bot, "bot_number", None),
                "damage_dealt": 0.0,
                "damage_taken": 0.0,
                "shots_fired": 0,
                "shots_hit": 0,
                "weapon_switches": 0,
                "rl_step_skipped": True,
                "rl_frame": self._rl_frame_count
            }

            return (
                observation,
                0.0,
                terminated,
                truncated,
                info
            )

        # Exactly 0.1 s of game time has elapsed.
        self._rl_frame_count = 0
        self.current_step += 1

        # -----------------------------------------------------
        # RESET PER-RL-STEP TRACKING
        # -----------------------------------------------------

        self.last_damage_dealt = 0.0
        self.last_damage_taken = 0.0

        self.last_shot_fired = False
        self.last_shot_hit = False

        self.weapon_switched = False

        self._step_weapon_switches = 0

        # -----------------------------------------------------
        # UPDATE SWITCH TIMER
        # EXACT RL25 TRAINING TIMESTEP = 0.1 SECOND
        # -----------------------------------------------------

        self.weapon_switch_timer = max(
            0.0,
            self.weapon_switch_timer - self.RL_STEP_DT
        )

        # -----------------------------------------------------
        # SAVE OLD STATE
        # -----------------------------------------------------

        old_player_health = float(
            getattr(
                self.player,
                "health",
                0.0
            )
        )

        old_bot_health = float(
            getattr(
                self.bot,
                "health",
                0.0
            )
        )

        old_weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                None
            )
        )

        # -----------------------------------------------------
        # LEAVE MELEE STATE AT THE RL DECISION BOUNDARY
        # -----------------------------------------------------
        # Movement/shoot/reload after a MELEE decision must not leave
        # the bot permanently holding the knife.  This is done once
        # per RL decision, not on the six intermediate render frames.
        if action != self.ACTION_MELEE:
            current_weapon = getattr(
                self.bot,
                "weapon",
                getattr(self.bot, "current_weapon", None),
            )
            if current_weapon == "knife":
                self._select_combat_weapon(
                    self._distance_to_player(),
                    force=True,
                )

        # -----------------------------------------------------
        # EXECUTE ACTION
        # -----------------------------------------------------

        # Hold this action for the next 0.1 s RL interval.
        self._active_action = action

        # Movement is distributed over all 6 rendered frames so the
        # bot does not visibly teleport/pause while preserving the
        # same total 0.1 s displacement used during training.
        self._perform_action(
            action,
            movement_scale=(1.0 / self.RL_FRAMES_PER_STEP),
            combat=True
        )

        # -----------------------------------------------------
        # COLLECT PICKUPS
        #
        # RL bot interacts with the same pickup objects used
        # by main.py.
        # -----------------------------------------------------

        pickup_reward = (
            self._pending_pickup_reward
            + self._collect_bot_pickups()
        )
        self._pending_pickup_reward = 0.0

        # -----------------------------------------------------
        # READ NEW STATE
        # -----------------------------------------------------

        new_player_health = float(
            getattr(
                self.player,
                "health",
                0.0
            )
        )

        new_bot_health = float(
            getattr(
                self.bot,
                "health",
                0.0
            )
        )

        # -----------------------------------------------------
        # DAMAGE DEALT
        # -----------------------------------------------------

        damage_dealt = max(
            0.0,
            old_player_health -
            new_player_health
        )

        # -----------------------------------------------------
        # DAMAGE TAKEN
        # -----------------------------------------------------

        damage_taken = max(
            0.0,
            old_bot_health -
            new_bot_health
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
        # WEAPON SWITCH DETECTION
        # -----------------------------------------------------

        new_weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                None
            )
        )

        if (
            old_weapon is not None
            and
            new_weapon is not None
            and
            old_weapon != new_weapon
        ):

            self.weapon_switched = True

            self.total_weapon_switches += 1

        # =====================================================
        # REWARD
        # =====================================================

        reward = 0.0

        # -----------------------------------------------------
        # DAMAGE DEALT
        # -----------------------------------------------------

        if damage_dealt > 0:

            reward += (
                self.damage_reward_scale *
                damage_dealt
            )

        # -----------------------------------------------------
        # SUCCESSFUL HIT
        # -----------------------------------------------------

        if self.last_shot_hit or damage_dealt > 0.0:
            reward += self.successful_hit_reward

        # -----------------------------------------------------
        # DAMAGE TAKEN
        # -----------------------------------------------------

        if damage_taken > 0:

            reward -= (
                self.damage_taken_penalty_scale *
                damage_taken
            )

        # -----------------------------------------------------
        # PICKUPS
        # -----------------------------------------------------

        reward += pickup_reward

        # -----------------------------------------------------
        # CURRENT DISTANCE
        # -----------------------------------------------------

        current_distance = self._distance_to_player()
        player_x, player_y = self._get_center(self.player)

        # -----------------------------------------------------
        # DISTANCE SHAPING
        #
        # Match RL25 training environment.
        # -----------------------------------------------------

        if self.previous_distance is not None:

            distance_change = (
                self.previous_distance -
                current_distance
            )

            reward += (
                0.04 *
                float(
                    np.clip(
                        distance_change,
                        -5.0,
                        5.0
                    )
                )
            )

        self.previous_distance = current_distance

        # -----------------------------------------------------
        # PICKUP APPROACH SHAPING
        # -----------------------------------------------------
        health_distance = self._nearest_needed_pickup_distance(
            self.health_pickups,
        )
        ammo_distance = self._nearest_needed_pickup_distance(
            self.ammo_pickups,
        )

        if float(getattr(self.bot, "health", 0.0)) <= 0.50 * float(
            getattr(self.bot, "max_health", 30.0)
        ):
            reward += 0.03 * float(np.clip(
                self.previous_health_pickup_distance - health_distance,
                -5.0, 5.0,
            ))

        if (
            self._get_current_ammo() is not None
            and self._current_ammo_ratio() <= 0.25
        ):
            reward += 0.03 * float(np.clip(
                self.previous_ammo_pickup_distance - ammo_distance,
                -5.0, 5.0,
            ))

        self.previous_health_pickup_distance = health_distance
        self.previous_ammo_pickup_distance = ammo_distance

        # -----------------------------------------------------
        # RANGE MILESTONES
        # -----------------------------------------------------
        for range_limit, bonus in {
            350.0: 1.0,
            280.0: 2.0,
            200.0: 3.0,
            110.0: 4.0,
            75.0: 5.0,
        }.items():
            if current_distance <= range_limit and not self.range_milestones[range_limit]:
                self.range_milestones[range_limit] = True
                reward += bonus

        # -----------------------------------------------------
        # ENGAGEMENT REWARD
        # -----------------------------------------------------

        if (
            current_distance <=
            self.RIFLE_RANGE
            and
            self._line_of_sight()
        ):

            reward += (
                self.engagement_reward
            )

        # -----------------------------------------------------
        # FAR DISTANCE PENALTY
        # -----------------------------------------------------

        if current_distance > 350.0:

            reward -= (
                self.far_distance_penalty
            )

        # -----------------------------------------------------
        # STEP COST
        # -----------------------------------------------------

        reward -= (
            self.step_penalty
        )

        # -----------------------------------------------------
        # WEAPON SWITCH COST
        # -----------------------------------------------------

        reward -= (
            self.weapon_switch_penalty *
            self._step_weapon_switches
        )

        # -----------------------------------------------------
        # TERMINATION
        # -----------------------------------------------------

        terminated = False

        # -----------------------------------------------------
        # PLAYER DEFEATED
        # -----------------------------------------------------

        if self.player.health <= 0:

            self.player.health = 0.0

            self.player_defeated = True

            reward += (
                self.player_defeat_reward
            )

            terminated = True

        # -----------------------------------------------------
        # BOT DEFEATED
        # -----------------------------------------------------

        elif self.bot.health <= 0:

            self.bot.health = 0.0

            self.bot_defeated = True

            reward -= (
                self.bot_defeat_penalty
            )

            terminated = True

        # -----------------------------------------------------
        # TIME LIMIT
        # -----------------------------------------------------

        truncated = (
            self.current_step >=
            self.max_steps
        )

        # -----------------------------------------------------
        # TARGET VELOCITY
        # -----------------------------------------------------
        #
        # Match HeadlessShooterEnv exactly:
        # displacement over the completed 0.1-second RL interval,
        # normalized by the target's 180 px/s reference speed.
        #
        # player_x/player_y were captured after the actual RL
        # interval above. previous_player_center is the position
        # at the previous decision boundary.
        # -----------------------------------------------------

        if self.previous_player_center is None:
            self.target_velocity_x = 0.0
            self.target_velocity_y = 0.0
        else:
            self.target_velocity_x = float(
                np.clip(
                    (
                        player_x -
                        self.previous_player_center[0]
                    )
                    / self.RL_STEP_DT
                    / 180.0,
                    -1.0,
                    1.0
                )
            )

            self.target_velocity_y = float(
                np.clip(
                    (
                        player_y -
                        self.previous_player_center[1]
                    )
                    / self.RL_STEP_DT
                    / 180.0,
                    -1.0,
                    1.0
                )
            )

        self.previous_player_center = (
            player_x,
            player_y
        )

        # -----------------------------------------------------
        # NEXT OBSERVATION
        # -----------------------------------------------------

        observation = self._get_observation()

        # -----------------------------------------------------
        # INFO
        # -----------------------------------------------------

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

            "melee_attempts": int(self.total_melee_attempts),
            "melee_hits": int(self.total_melee_hits),

            "weapon_switches": int(
                self.total_weapon_switches
            ),

            "distance": float(
                current_distance
            ),

            "line_of_sight": bool(
                self._line_of_sight()
            ),

            "weapon": getattr(
                self.bot,
                "weapon",
                getattr(
                    self.bot,
                    "current_weapon",
                    None
                )
            ),

            "action": int(
                action
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
        action,
        movement_scale=1.0,
        combat=True
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

        dx = (
            player_x -
            bot_x
        )

        dy = (
            player_y -
            bot_y
        )

        distance = math.hypot(
            dx,
            dy
        )

        # -----------------------------------------------------
        # FACE PLAYER
        #
        # This is intentional and matches the training
        # environment's task-oriented behavior.
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

            else:

                self.bot.facing_x = (
                    dx / distance
                )

                self.bot.facing_y = (
                    dy / distance
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
                ) * movement_scale
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
                ) * movement_scale
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
                ) * movement_scale
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
                ) * movement_scale
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
                ) * movement_scale
            )

            return

        # -----------------------------------------------------
        # SHOOT
        # -----------------------------------------------------

        if action == self.ACTION_SHOOT:

            if not combat:
                return

            self._execute_shoot(
                distance
            )

            return

        # -----------------------------------------------------
        # RELOAD
        # -----------------------------------------------------

        if action == self.ACTION_RELOAD:

            if not combat:
                return

            self._execute_reload()

            return

        # -----------------------------------------------------
        # MELEE
        # -----------------------------------------------------

        if action == self.ACTION_MELEE:

            if not combat:
                return

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

        if not hasattr(
            self.bot,
            "move"
        ):

            return

        # -----------------------------------------------------
        # RLBot.move() CURRENT API:
        #
        # move(dx, dy, obstacles, speed)
        #
        # -----------------------------------------------------

        try:

            self.bot.move(
                dx,
                dy,
                self.obstacles,
                speed
            )

        except TypeError:

            # Compatibility fallback for older versions.
            try:

                self.bot.move(
                    dx,
                    dy,
                    self.obstacles,
                    speed=speed
                )

            except TypeError:

                try:

                    self.bot.move(
                        dx,
                        dy,
                        self.obstacles,
                        sprint=(
                            speed >=
                            getattr(
                                self.bot,
                                "run_speed",
                                3.0
                            )
                        )
                    )

                except TypeError:

                    return

        # -----------------------------------------------------
        # Final bounds safety.
        # -----------------------------------------------------

        self._clamp_bot()

    # =========================================================
    # SHOOT
    # =========================================================

    def _execute_shoot(
        self,
        distance
    ):

        # -----------------------------------------------------
        # LINE OF SIGHT
        # -----------------------------------------------------

        if not self._line_of_sight():

            self.last_shot_fired = False
            self.last_shot_hit = False

            return

        # -----------------------------------------------------
        # AUTOMATIC WEAPON SELECTION
        # -----------------------------------------------------

        selected_weapon = (
            self._select_combat_weapon(
                distance
            )
        )

        # -----------------------------------------------------
        # KNIFE CANNOT SHOOT
        # -----------------------------------------------------

        if selected_weapon == "knife":

            self.last_shot_fired = False
            self.last_shot_hit = False

            return

        # -----------------------------------------------------
        # WEAPON RANGE
        # -----------------------------------------------------

        weapon_range = (
            self._weapon_range(
                selected_weapon
            )
        )

        if distance > weapon_range:

            self.last_shot_fired = False
            self.last_shot_hit = False

            return

        # -----------------------------------------------------
        # CHECK AMMO
        # -----------------------------------------------------

        ammo = self._get_weapon_ammo(
            selected_weapon
        )

        if ammo is not None and ammo <= 0:

            # Automatically request reload.
            self._execute_reload()

            self.last_shot_fired = False
            self.last_shot_hit = False

            return

        # -----------------------------------------------------
        # FIRE
        # -----------------------------------------------------

        if not hasattr(
            self.bot,
            "shoot"
        ):

            return

        fired = bool(
            self.bot.shoot()
        )

        if not fired:

            self.last_shot_fired = False
            self.last_shot_hit = False

            return

        self.last_shot_fired = True
        self.total_shots_fired += 1

        # -----------------------------------------------------
        # CREATE REAL BULLET
        #
        # main.py callback creates the PyGame Bullet.
        # -----------------------------------------------------

        if self.shoot_callback is not None:

            before_player_health = float(
                getattr(
                    self.player,
                    "health",
                    0.0
                )
            )

            self.shoot_callback(
                self.bot
            )

            after_player_health = float(
                getattr(
                    self.player,
                    "health",
                    0.0
                )
            )

            # Some callback implementations may apply
            # immediate damage. Detect that if it happens.
            if after_player_health < before_player_health:

                self.last_shot_hit = True
                self.total_shots_hit += 1

            else:

                self.last_shot_hit = False

        else:

            self.last_shot_hit = False

    # =========================================================
    # RELOAD
    # =========================================================

    def _execute_reload(self):

        if hasattr(
            self.bot,
            "reload"
        ):

            return bool(
                self.bot.reload()
            )

        if hasattr(
            self.bot,
            "start_reload"
        ):

            return bool(
                self.bot.start_reload()
            )

        return False

    # =========================================================
    # MELEE
    # =========================================================

    def _execute_melee(
        self,
        distance
    ):

        self.total_melee_attempts += 1

        # -----------------------------------------------------
        # MELEE RANGE
        # -----------------------------------------------------

        melee_range = getattr(
            self.bot,
            "RL_MELEE_RANGE",
            self.KNIFE_RANGE
        )

        if distance > melee_range:

            return

        # -----------------------------------------------------
        # EQUIP KNIFE
        # -----------------------------------------------------

        changed = self._switch_weapon(
            "knife",
            force=True
        )

        # -----------------------------------------------------
        # EXECUTE MELEE ANIMATION / ACTION
        # -----------------------------------------------------

        if hasattr(
            self.bot,
            "melee"
        ):

            started = bool(
                self.bot.melee()
            )

        elif hasattr(
            self.bot,
            "melee_attack"
        ):

            started = bool(
                self.bot.melee_attack()
            )

        else:

            started = False

        if not started:

            return

        # -----------------------------------------------------
        # WORLD CALLBACK
        #
        # main.py performs the actual player damage.
        # -----------------------------------------------------

        if self.melee_callback is not None:

            before_player_health = float(
                getattr(
                    self.player,
                    "health",
                    0.0
                )
            )

            callback_result = (
                self.melee_callback(
                    self.bot
                )
            )

            after_player_health = float(
                getattr(
                    self.player,
                    "health",
                    0.0
                )
            )

            if after_player_health < before_player_health:

                self.last_shot_hit = True
                self.total_melee_hits += 1

    # =========================================================
    # SELECT COMBAT WEAPON
    # =========================================================

    def _select_combat_weapon(
        self,
        distance,
        force=False
    ):

        # -----------------------------------------------------
        # TARGET WEAPON
        # -----------------------------------------------------

        # ACTION_SHOOT must always select a firearm.
        # The knife is reserved for ACTION_MELEE, which explicitly
        # equips the knife in _execute_melee().
        # This matches HeadlessShooterEnv training semantics.
        if distance <= self.SHOTGUN_RANGE:

            preferred = "shotgun"

        elif distance <= self.HANDGUN_RANGE:

            preferred = "handgun"

        else:

            preferred = "rifle"

        # -----------------------------------------------------
        # SAVE TARGET INFORMATION
        # -----------------------------------------------------

        if hasattr(
            self.bot,
            "rl_target_weapon"
        ):

            self.bot.rl_target_weapon = (
                preferred
            )

        # -----------------------------------------------------
        # CURRENT WEAPON
        # -----------------------------------------------------

        current_weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                "handgun"
            )
        )

        # -----------------------------------------------------
        # SAME WEAPON
        # -----------------------------------------------------

        if current_weapon == preferred:

            return preferred

        # -----------------------------------------------------
        # SWITCH COOLDOWN
        #
        # This prevents rapid knife/firearm oscillation.
        # -----------------------------------------------------

        if self.weapon_switch_timer > 0.0 and not force:

            # Keep current weapon while locked if it is usable.
            if (
                current_weapon == "knife"
                and
                distance > self.KNIFE_RANGE
            ):

                # Knife is no longer appropriate, but don't
                # oscillate immediately.
                return current_weapon

            if (
                current_weapon != "knife"
                and
                self._get_weapon_ammo(
                    current_weapon
                ) is not None
                and
                self._get_weapon_ammo(
                    current_weapon
                ) > 0
            ):

                return current_weapon

        # -----------------------------------------------------
        # PREFERRED FIREARM EMPTY -> FIND AVAILABLE FIREARM
        # -----------------------------------------------------

        if preferred != "knife":

            preferred_ammo = (
                self._get_weapon_ammo(
                    preferred
                )
            )

            if (
                preferred_ammo is not None
                and
                preferred_ammo <= 0
            ):

                available = []

                for weapon in (
                    "shotgun",
                    "handgun",
                    "rifle"
                ):

                    ammo = (
                        self._get_weapon_ammo(
                            weapon
                        )
                    )

                    if (
                        ammo is not None
                        and
                        ammo > 0
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
                            -
                            distance
                        )
                    )

                    preferred = (
                        available[0]
                    )

                else:

                    # No firearm has ammo.
                    # Return preferred so reload logic can
                    # handle the situation.
                    preferred = (
                        preferred
                    )

        # -----------------------------------------------------
        # SWITCH
        # -----------------------------------------------------

        if (
            current_weapon != preferred
            and
            (self.weapon_switch_timer <= 0.0 or force)
        ):

            changed = self._switch_weapon(
                preferred,
                force=force
            )

            if changed:

                self.weapon_switch_timer = (
                    self.WEAPON_SWITCH_COOLDOWN
                )

        return getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                preferred
            )
        )

    # =========================================================
    # SWITCH WEAPON
    # =========================================================

    def _switch_weapon(
        self,
        weapon,
        force=False
    ):

        current_weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                None
            )
        )

        if current_weapon == weapon:

            return False

        if (
            not force
            and
            self.weapon_switch_timer > 0.0
        ):

            return False

        changed = False

        # -----------------------------------------------------
        # RLBot.set_weapon()
        # -----------------------------------------------------

        # -----------------------------------------------------
        # RLBot.set_weapon()
        #
        # Verify the actual post-call state as well as the return
        # value. This makes the environment robust to older
        # compatibility implementations that return None after
        # successfully changing the weapon.
        # -----------------------------------------------------

        if hasattr(
            self.bot,
            "set_weapon"
        ):

            result = self.bot.set_weapon(
                weapon
            )

            current_after = getattr(
                self.bot,
                "weapon",
                getattr(
                    self.bot,
                    "current_weapon",
                    None
                )
            )

            changed = (
                current_after == weapon
                and
                current_weapon != weapon
                and
                result is not False
            )

        # -----------------------------------------------------
        # RLBot.equip()
        # -----------------------------------------------------

        elif hasattr(
            self.bot,
            "equip"
        ):

            result = self.bot.equip(
                weapon
            )

            current_after = getattr(
                self.bot,
                "weapon",
                getattr(
                    self.bot,
                    "current_weapon",
                    None
                )
            )

            changed = (
                current_after == weapon
                and
                current_weapon != weapon
                and
                result is not False
            )

        # -----------------------------------------------------
        # Compatibility fallback
        # -----------------------------------------------------

        elif hasattr(
            self.bot,
            "switch_to_weapon"
        ):

            result = self.bot.switch_to_weapon(
                weapon
            )

            current_after = getattr(
                self.bot,
                "weapon",
                getattr(
                    self.bot,
                    "current_weapon",
                    None
                )
            )

            changed = (
                current_after == weapon
                and
                current_weapon != weapon
                and
                result is not False
            )

        if changed:

            self.weapon_switched = True

            self._step_weapon_switches += 1

            self.total_weapon_switches += 1

            # Headless starts the switch lock for every actual
            # weapon change, including the forced knife -> firearm
            # transition at a decision boundary.
            self.weapon_switch_timer = (
                self.WEAPON_SWITCH_COOLDOWN
            )

        return changed

    # =========================================================
    # WEAPON RANGE
    # =========================================================

    def _weapon_range(
        self,
        weapon
    ):

        ranges = {

            "knife":
                self.KNIFE_RANGE,

            "shotgun":
                self.SHOTGUN_RANGE,

            "handgun":
                self.HANDGUN_RANGE,

            "rifle":
                self.RIFLE_RANGE
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

        # -----------------------------------------------------
        # RLBot current implementation
        # -----------------------------------------------------

        if hasattr(
            self.bot,
            "weapon_ammo"
        ):

            try:

                return self.bot.weapon_ammo.get(
                    weapon,
                    0
                )

            except Exception:

                pass

        # -----------------------------------------------------
        # Current weapon API
        # -----------------------------------------------------

        current_weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                None
            )
        )

        if (
            current_weapon == weapon
            and
            hasattr(
                self.bot,
                "current_ammo"
            )
        ):

            try:

                return self.bot.current_ammo()

            except Exception:

                pass

        # -----------------------------------------------------
        # Legacy ammo API
        # -----------------------------------------------------

        if (
            current_weapon == weapon
            and
            hasattr(
                self.bot,
                "ammo"
            )
        ):

            try:

                return self.bot.ammo

            except Exception:

                pass

        return 0

    # =========================================================
    # CURRENT AMMO
    # =========================================================

    def _get_current_ammo(self):

        weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                "handgun"
            )
        )

        if weapon == "knife":

            return None

        return self._get_weapon_ammo(
            weapon
        )

    # =========================================================
    # CURRENT MAX AMMO
    # =========================================================

    def _get_current_max_ammo(self):

        weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                "handgun"
            )
        )

        if weapon == "knife":

            return 1

        # -----------------------------------------------------
        # RLBot WEAPON_STATS
        # -----------------------------------------------------

        if hasattr(
            self.bot,
            "WEAPON_STATS"
        ):

            try:

                stats = (
                    self.bot.WEAPON_STATS.get(
                        weapon
                    )
                )

                if stats is not None:

                    # Headless uses "magazine"; older Tactical
                    # code looked only for "max_ammo". Support both
                    # while preferring the same field as Headless.
                    value = stats.get("magazine")
                    if value is None:
                        value = stats.get("max_ammo")

                    if value is not None:
                        return int(value)

            except Exception:

                pass

        # -----------------------------------------------------
        # Legacy max_ammo method
        # -----------------------------------------------------

        if hasattr(
            self.bot,
            "max_ammo"
        ):

            try:

                value = self.bot.max_ammo()

                if value is not None:

                    return int(
                        value
                    )

            except Exception:

                pass

        # -----------------------------------------------------
        # Fallback values
        # -----------------------------------------------------

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
    # CURRENT AMMO RATIO
    # =========================================================
    #
    # Used by pickup-approach reward shaping.  Derives the ratio
    # from the same ammo helpers used everywhere else in this
    # environment.
    # =========================================================

    def _current_ammo_ratio(self):
        """Return current firearm ammo as a normalized 0.0-1.0 ratio.

        Knife has no magazine, so it is treated as full (1.0).
        Invalid/zero magazine sizes are handled safely.
        """

        current_ammo = self._get_current_ammo()

        if current_ammo is None:
            return 1.0

        max_ammo = self._get_current_max_ammo()

        if max_ammo is None or max_ammo <= 0:
            return 1.0

        return float(
            np.clip(
                float(current_ammo) / float(max_ammo),
                0.0,
                1.0,
            )
        )

    # =========================================================
    # OBSERVATION
    # =========================================================

    def _get_observation(self):

        # -----------------------------------------------------
        # CENTERS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # RELATIVE PLAYER POSITION
        # -----------------------------------------------------

        dx = (
            player_x -
            bot_x
        )

        dy = (
            player_y -
            bot_y
        )

        distance = math.hypot(
            dx,
            dy
        )

        # =====================================================
        # IMPORTANT:
        #
        # The following order EXACTLY matches HeadlessShooterEnv.
        # Do not rearrange these values.
        # =====================================================

        observation = []

        # -----------------------------------------------------
        # 0 = BOT X
        # -----------------------------------------------------

        observation.append(
            self._normalize_x(
                bot_x
            )
        )

        # -----------------------------------------------------
        # 1 = BOT Y
        # -----------------------------------------------------

        observation.append(
            self._normalize_y(
                bot_y
            )
        )

        # -----------------------------------------------------
        # 2 = DX
        # -----------------------------------------------------

        observation.append(
            np.clip(
                dx / 500.0,
                -1.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 3 = DY
        # -----------------------------------------------------

        observation.append(
            np.clip(
                dy / 500.0,
                -1.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 4 = DISTANCE
        # -----------------------------------------------------

        observation.append(
            np.clip(
                distance / 500.0,
                0.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 5 = BOT HEALTH
        # -----------------------------------------------------

        bot_max_health = float(
            getattr(
                self.bot,
                "max_health",
                30.0
            )
        )

        observation.append(
            np.clip(
                float(
                    getattr(
                        self.bot,
                        "health",
                        0.0
                    )
                )
                /
                max(
                    1.0,
                    bot_max_health
                ),
                0.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 6 = PLAYER HEALTH
        # -----------------------------------------------------

        # HeadlessShooterEnv uses the fixed scripted-enemy maximum
        # health of 40.0 for observation index 6.  The deployed target
        # must use the SAME denominator; using player.max_health here
        # would change the meaning of the trained feature.
        observation.append(
            np.clip(
                float(
                    getattr(
                        self.player,
                        "health",
                        0.0
                    )
                )
                / 40.0,
                0.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 7 = CURRENT AMMO
        # -----------------------------------------------------

        ammo = self._get_current_ammo()

        if ammo is None:

            ammo_normalized = 1.0

        else:

            max_ammo = (
                self._get_current_max_ammo()
            )

            if max_ammo <= 0:

                ammo_normalized = 0.0

            else:

                ammo_normalized = np.clip(
                    float(ammo)
                    /
                    float(max_ammo),
                    0.0,
                    1.0
                )

        observation.append(
            ammo_normalized
        )

        # -----------------------------------------------------
        # 8 = WEAPON ENCODING
        #
        # EXACT HEADLESS ENCODING
        # -----------------------------------------------------

        weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                "handgun"
            )
        )

        weapon_encoding = {

            "handgun":
                -1.0,

            "shotgun":
                -0.33,

            "rifle":
                0.33,

            "knife":
                1.0
        }

        observation.append(
            weapon_encoding.get(
                weapon,
                -1.0
            )
        )

        # -----------------------------------------------------
        # 9 = FACING X
        # -----------------------------------------------------

        observation.append(
            np.clip(
                float(
                    getattr(
                        self.bot,
                        "facing_x",
                        1.0
                    )
                ),
                -1.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 10 = FACING Y
        # -----------------------------------------------------

        observation.append(
            np.clip(
                float(
                    getattr(
                        self.bot,
                        "facing_y",
                        0.0
                    )
                ),
                -1.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 11 = LINE OF SIGHT
        # -----------------------------------------------------

        observation.append(
            1.0
            if self._line_of_sight()
            else
            0.0
        )

        # -----------------------------------------------------
        # 12 = HEALTH PICKUP DISTANCE
        # -----------------------------------------------------

        health_distance = (
            self._nearest_pickup_distance(
                self.health_pickups
            )
        )

        observation.append(
            np.clip(
                health_distance / 500.0,
                0.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 13 = AMMO PICKUP DISTANCE
        # -----------------------------------------------------

        ammo_distance = (
            self._nearest_pickup_distance(
                self.ammo_pickups
            )
        )

        observation.append(
            np.clip(
                ammo_distance / 500.0,
                0.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 14 = HEALTH PICKUP AVAILABLE
        # -----------------------------------------------------

        observation.append(
            1.0
            if self._count_available_pickups(
                self.health_pickups
            ) > 0
            else
            0.0
        )

        # -----------------------------------------------------
        # 15 = AMMO PICKUP AVAILABLE
        # -----------------------------------------------------

        observation.append(
            1.0
            if self._count_available_pickups(
                self.ammo_pickups
            ) > 0
            else
            0.0
        )

        # -----------------------------------------------------
        # 16-23 = OBSTACLE RAYS
        #
        # EXACT SAME ORDER AS HEADLESS
        # -----------------------------------------------------

        obstacle_distances = (
            self._get_obstacle_distances()
        )

        observation.extend(
            obstacle_distances
        )

        # -----------------------------------------------------
        # 24 = ENEMY VELOCITY X
        # 25 = ENEMY VELOCITY Y
        #
        # Use the completed 0.1-second RL interval velocity.
        # Tactical stores this value at the decision boundary so
        # intermediate render-frame observations do not drift.
        # Headless uses:
        #     displacement / 0.1 / 180 px/s
        # -----------------------------------------------------

        observation.append(
            np.clip(
                self.target_velocity_x,
                -1.0,
                1.0
            )
        )

        observation.append(
            np.clip(
                self.target_velocity_y,
                -1.0,
                1.0
            )
        )

        # -----------------------------------------------------
        # 26-27 = HEALTH PICKUP DIRECTION
        # 28-29 = AMMO PICKUP DIRECTION
        # -----------------------------------------------------
        health_dx, health_dy = self._nearest_pickup_direction(
            self.health_pickups,
        )
        ammo_dx, ammo_dy = self._nearest_pickup_direction(
            self.ammo_pickups,
        )

        observation.append(np.clip(health_dx, -1.0, 1.0))
        observation.append(np.clip(health_dy, -1.0, 1.0))
        observation.append(np.clip(ammo_dx, -1.0, 1.0))
        observation.append(np.clip(ammo_dy, -1.0, 1.0))

        # -----------------------------------------------------
        # 30 = KNIFE RANGE
        # -----------------------------------------------------

        observation.append(
            1.0
            if distance <= self.KNIFE_RANGE
            else
            0.0
        )

        # -----------------------------------------------------
        # 31 = SHOTGUN RANGE
        # -----------------------------------------------------

        observation.append(
            1.0
            if distance <= self.SHOTGUN_RANGE
            else
            0.0
        )

        # -----------------------------------------------------
        # 32 = HANDGUN RANGE
        # -----------------------------------------------------

        observation.append(
            1.0
            if distance <= self.HANDGUN_RANGE
            else
            0.0
        )

        # -----------------------------------------------------
        # 33 = RIFLE RANGE
        # -----------------------------------------------------

        observation.append(
            1.0
            if distance <= self.RIFLE_RANGE
            else
            0.0
        )

        # -----------------------------------------------------
        # FINAL VALIDATION
        # -----------------------------------------------------

        if len(observation) != self.STATE_SIZE:

            raise RuntimeError(
                "Observation size mismatch: "
                f"{len(observation)} "
                f"instead of "
                f"{self.STATE_SIZE}"
            )

        result = np.asarray(
            observation,
            dtype=np.float32
        )

        # -----------------------------------------------------
        # SAFETY CHECK
        # -----------------------------------------------------

        result = np.clip(
            result,
            -1.0,
            1.0
        ).astype(
            np.float32
        )

        return result

    def _nearest_pickup_direction(self, pickups):
        available = []
        for pickup in pickups:
            if self._pickup_is_collected(pickup):
                continue
            try:
                px, py = self._get_pickup_position(pickup)
            except Exception:
                continue
            available.append((px, py))

        if not available:
            return 0.0, 0.0

        bot_x, bot_y = self._get_center(self.bot)
        px, py = min(
            available,
            key=lambda point: math.hypot(point[0] - bot_x, point[1] - bot_y),
        )
        return (
            float(np.clip((px - bot_x) / 500.0, -1.0, 1.0)),
            float(np.clip((py - bot_y) / 500.0, -1.0, 1.0)),
        )

    def _nearest_needed_pickup_distance(self, pickups):
        if not pickups:
            return 500.0
        bot_x, bot_y = self._get_center(self.bot)
        distances = []
        for pickup in pickups:
            if self._pickup_is_collected(pickup):
                continue
            try:
                px, py = self._get_pickup_position(pickup)
            except Exception:
                continue
            distances.append(math.hypot(px - bot_x, py - bot_y))
        return min(distances) if distances else 500.0

    # =========================================================
    # OBSTACLE DISTANCES
    # =========================================================

    def _get_obstacle_distances(self):

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # This is the EXACT diagonal ordering used by the
        # HeadlessShooterEnv.
        #
        # 16 = +X,+Y
        # 17 = -X,+Y
        # 18 = +X,-Y
        # 19 = -X,-Y
        # -----------------------------------------------------

        directions = [

            # 16
            (1.0, 0.0),

            # 17
            (-1.0, 0.0),

            # 18
            (0.0, 1.0),

            # 19
            (0.0, -1.0),

            # 20
            (0.70710678, 0.70710678),

            # 21
            (-0.70710678, 0.70710678),

            # 22
            (0.70710678, -0.70710678),

            # 23
            (-0.70710678, -0.70710678)
        ]

        values = []

        for direction_x, direction_y in directions:

            ray_distance = (
                self._ray_distance(
                    bot_x,
                    bot_y,
                    direction_x,
                    direction_y,
                    self.MAX_RAY_DISTANCE
                )
            )

            values.append(
                np.clip(
                    ray_distance /
                    self.MAX_RAY_DISTANCE,
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

        distance = 0.0

        while distance <= max_distance:

            x = (
                start_x
                +
                direction_x *
                distance
            )

            y = (
                start_y
                +
                direction_y *
                distance
            )

            if self._point_inside_obstacle(
                x,
                y
            ):

                return distance

            distance += self.RAY_STEP

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

            # -------------------------------------------------
            # DICTIONARY
            # -------------------------------------------------

            if isinstance(
                obstacle,
                dict
            ):

                ox = float(
                    obstacle.get(
                        "x",
                        0
                    )
                )

                oy = float(
                    obstacle.get(
                        "y",
                        0
                    )
                )

                ow = float(
                    obstacle.get(
                        "width",
                        0
                    )
                )

                oh = float(
                    obstacle.get(
                        "height",
                        0
                    )
                )

            # -------------------------------------------------
            # pygame.Rect / RECT-LIKE
            # -------------------------------------------------

            elif hasattr(
                obstacle,
                "rect"
            ):

                rect = obstacle.rect

                ox = float(
                    rect.x
                )

                oy = float(
                    rect.y
                )

                ow = float(
                    rect.width
                )

                oh = float(
                    rect.height
                )

            # -------------------------------------------------
            # OBJECT WITH X/Y/WIDTH/HEIGHT
            # -------------------------------------------------

            elif all(
                hasattr(
                    obstacle,
                    attribute
                )
                for attribute in (
                    "x",
                    "y",
                    "width",
                    "height"
                )
            ):

                ox = float(
                    obstacle.x
                )

                oy = float(
                    obstacle.y
                )

                ow = float(
                    obstacle.width
                )

                oh = float(
                    obstacle.height
                )

            else:

                continue

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

    def _line_of_sight(self):

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

        return self._has_line_of_sight(
            bot_x,
            bot_y,
            player_x,
            player_y
        )

    # =========================================================
    # PLAYER LINE OF SIGHT
    # =========================================================

    def _player_line_of_sight(self):

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

        return self._has_line_of_sight(
            player_x,
            player_y,
            bot_x,
            bot_y
        )

    # =========================================================
    # LINE OF SIGHT TEST
    # =========================================================

    def _has_line_of_sight(
        self,
        x1,
        y1,
        x2,
        y2
    ):

        distance = math.hypot(
            x2 - x1,
            y2 - y1
        )

        if distance <= 0:

            return True

        steps = max(
            1,
            int(
                distance / 5.0
            )
        )

        for i in range(
            1,
            steps
        ):

            t = (
                i /
                steps
            )

            x = (
                x1
                +
                (x2 - x1) *
                t
            )

            y = (
                y1
                +
                (y2 - y1) *
                t
            )

            if self._point_inside_obstacle(
                x,
                y
            ):

                return False

        return True

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
    # PICKUP DISTANCE
    # =========================================================

    def _nearest_pickup_distance(
        self,
        pickups
    ):

        # Match Headless behavior:
        # no available pickup -> 500 px sentinel.

        available_pickups = []

        for pickup in pickups:

            if self._pickup_is_collected(
                pickup
            ):

                continue

            available_pickups.append(
                pickup
            )

        if not available_pickups:

            return 500.0

        bot_x, bot_y = (
            self._get_center(
                self.bot
            )
        )

        nearest = 500.0

        for pickup in available_pickups:

            try:

                pickup_x, pickup_y = (
                    self._get_pickup_position(
                        pickup
                    )
                )

            except Exception:

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
    # PICKUP POSITION
    # =========================================================

    @staticmethod
    def _get_pickup_position(
        pickup
    ):

        # -----------------------------------------------------
        # MAIN.PY DICTIONARY
        # -----------------------------------------------------

        if isinstance(
            pickup,
            dict
        ):

            return (
                float(
                    pickup["x"]
                ),
                float(
                    pickup["y"]
                )
            )

        # -----------------------------------------------------
        # pygame/object with rect
        # -----------------------------------------------------

        if hasattr(
            pickup,
            "rect"
        ):

            return (
                float(
                    pickup.rect.centerx
                ),
                float(
                    pickup.rect.centery
                )
            )

        # -----------------------------------------------------
        # Tuple/list
        # -----------------------------------------------------

        return (
            float(
                pickup[0]
            ),
            float(
                pickup[1]
            )
        )

    # =========================================================
    # PICKUP COLLECTED
    # =========================================================

    @staticmethod
    def _pickup_is_collected(
        pickup
    ):

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
    # COUNT AVAILABLE PICKUPS
    # =========================================================

    def _count_available_pickups(
        self,
        pickups
    ):

        count = 0

        for pickup in pickups:

            if not self._pickup_is_collected(
                pickup
            ):

                count += 1

        return count

    # =========================================================
    # MARK PICKUP COLLECTED
    # =========================================================

    @staticmethod
    def _mark_pickup_collected(
        pickup
    ):

        if isinstance(
            pickup,
            dict
        ):

            pickup["collected"] = True

    # =========================================================
    # COLLECT BOT PICKUPS
    # =========================================================

    def _collect_bot_pickups(self):

        if not getattr(
            self.bot,
            "alive",
            True
        ):

            return 0.0

        reward = 0.0

        bot_rect = self._get_rect(
            self.bot
        )

        # Match HeadlessShooterEnv exactly.
        pickup_size = max(
            1,
            int(
                8 * self.TILE_SCALE
            )
        )

        # =====================================================
        # HEALTH PICKUP
        # =====================================================

        bot_health = float(
            getattr(
                self.bot,
                "health",
                0
            )
        )

        bot_max_health = float(
            getattr(
                self.bot,
                "max_health",
                30
            )
        )

        if bot_health < bot_max_health:

            for pickup in self.health_pickups:

                if self._pickup_is_collected(
                    pickup
                ):

                    continue

                try:

                    px, py = (
                        self._get_pickup_position(
                            pickup
                        )
                    )

                except Exception:

                    continue

                pickup_rect = (
                    float(px),
                    float(py),
                    float(pickup_size),
                    float(pickup_size)
                )

                if self._rects_overlap(
                    bot_rect,
                    pickup_rect
                ):

                    old_health = float(
                        getattr(
                            self.bot,
                            "health",
                            0
                        )
                    )

                    # Prefer RLBot.heal().
                    if hasattr(
                        self.bot,
                        "heal"
                    ):

                        self.bot.heal(
                            15
                        )

                    else:

                        self.bot.health = min(
                            bot_max_health,
                            self.bot.health + 15
                        )

                    new_health = float(
                        getattr(
                            self.bot,
                            "health",
                            0
                        )
                    )

                    if new_health > old_health:
                        self._mark_pickup_collected(pickup)
                        health_ratio = old_health / max(1.0, bot_max_health)
                        reward += 8.0 if health_ratio <= 0.50 else 4.0

                    break

        # =====================================================
        # AMMO PICKUP
        # =====================================================

        current_weapon = getattr(
            self.bot,
            "weapon",
            getattr(
                self.bot,
                "current_weapon",
                "handgun"
            )
        )

        if current_weapon != "knife":

            current_ammo = self._get_current_ammo()
            max_ammo = self._get_current_max_ammo()

            if current_ammo is None or current_ammo >= max_ammo:
                return reward

            for pickup in self.ammo_pickups:

                if self._pickup_is_collected(
                    pickup
                ):

                    continue

                try:

                    px, py = (
                        self._get_pickup_position(
                            pickup
                        )
                    )

                except Exception:

                    continue

                pickup_rect = (
                    float(px),
                    float(py),
                    float(pickup_size),
                    float(pickup_size)
                )

                if self._rects_overlap(
                    bot_rect,
                    pickup_rect
                ):

                    if hasattr(
                        self.bot,
                        "add_ammo"
                    ):

                        self.bot.add_ammo()

                    elif hasattr(
                        self.bot,
                        "weapon_ammo"
                    ):

                        try:

                            max_ammo = (
                                self._get_current_max_ammo()
                            )

                            self.bot.weapon_ammo[
                                current_weapon
                            ] = max_ammo

                        except Exception:

                            pass

                    new_ammo = self._get_current_ammo()
                    if new_ammo is not None and new_ammo > current_ammo:
                        self._mark_pickup_collected(pickup)
                        ammo_ratio = current_ammo / max(1, max_ammo)
                        reward += 5.0 if ammo_ratio <= 0.25 else 2.5

                    break

        return reward

    # =========================================================
    # RECTANGLE OVERLAP
    # =========================================================

    @staticmethod
    def _rects_overlap(
        a,
        b
    ):

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

    # =========================================================
    # GET RECT
    # =========================================================

    def _get_rect(
        self,
        obj
    ):

        if hasattr(
            obj,
            "get_rect"
        ):

            try:

                rect = obj.get_rect()

                return (
                    float(rect.x),
                    float(rect.y),
                    float(rect.width),
                    float(rect.height)
                )

            except Exception:

                pass

        if hasattr(
            obj,
            "rect"
        ):

            rect = obj.rect

            return (
                float(rect.x),
                float(rect.y),
                float(rect.width),
                float(rect.height)
            )

        width = float(
            getattr(
                obj,
                "width",
                40
            )
        )

        height = float(
            getattr(
                obj,
                "height",
                40
            )
        )

        return (
            float(
                getattr(
                    obj,
                    "x",
                    0
                )
            ),
            float(
                getattr(
                    obj,
                    "y",
                    0
                )
            ),
            width,
            height
        )

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

                result = obj.get_center()

                if (
                    isinstance(
                        result,
                        tuple
                    )
                    and
                    len(result) == 2
                ):

                    return (
                        float(result[0]),
                        float(result[1])
                    )

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
                    and
                    len(result) == 2
                ):

                    return (
                        float(result[0]),
                        float(result[1])
                    )

            except Exception:

                pass

        width = float(
            getattr(
                obj,
                "width",
                40
            )
        )

        height = float(
            getattr(
                obj,
                "height",
                40
            )
        )

        x = float(
            getattr(
                obj,
                "x",
                0
            )
        )

        y = float(
            getattr(
                obj,
                "y",
                0
            )
        )

        return (
            x + width / 2.0,
            y + height / 2.0
        )

    # =========================================================
    # NORMALIZE X
    #
    # IMPORTANT:
    #
    # Headless uses:
    #
    # normalized [0,1]
    #       ->
    # normalized [−1,1]
    #
    # Therefore Tactical MUST do the same.
    # =========================================================

    def _normalize_x(
        self,
        x
    ):

        denominator = (
            self.MAP_RIGHT -
            self.MAP_LEFT
        )

        if denominator <= 0:

            return 0.0

        normalized = (
            (
                x -
                self.MAP_LEFT
            )
            /
            denominator
        )

        normalized = (
            normalized *
            2.0
            -
            1.0
        )

        return float(
            np.clip(
                normalized,
                -1.0,
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

        denominator = (
            self.MAP_BOTTOM -
            self.MAP_TOP
        )

        if denominator <= 0:

            return 0.0

        normalized = (
            (
                y -
                self.MAP_TOP
            )
            /
            denominator
        )

        normalized = (
            normalized *
            2.0
            -
            1.0
        )

        return float(
            np.clip(
                normalized,
                -1.0,
                1.0
            )
        )

    # =========================================================
    # CLAMP BOT
    # =========================================================

    def _clamp_bot(self):

        if self.bot is None:

            return

        width = float(
            getattr(
                self.bot,
                "width",
                40
            )
        )

        height = float(
            getattr(
                self.bot,
                "height",
                40
            )
        )

        self.bot.x = max(
            self.PLAYABLE_LEFT,
            min(float(self.bot.x), self.PLAYABLE_RIGHT - width)
        )

        self.bot.y = max(
            self.PLAYABLE_TOP,
            min(float(self.bot.y), self.PLAYABLE_BOTTOM - height)
        )

        # Some older Player/Enemy-style objects use rect.
        if hasattr(
            self.bot,
            "rect"
        ):

            try:

                self.bot.rect.topleft = (
                    int(self.bot.x),
                    int(self.bot.y)
                )

            except Exception:

                pass

    # =========================================================
    # VALIDATE ENVIRONMENT
    # =========================================================

    def validate(self):

        if self.player is None or self.bot is None:

            return {
                "connected": False,
                "observation_shape": (
                    self.STATE_SIZE,
                ),
                "observation_valid": False
            }

        try:

            observation = (
                self._get_observation()
            )

            observation_valid = (
                observation.shape ==
                (self.STATE_SIZE,)
                and
                observation.dtype ==
                np.float32
                and
                np.all(
                    observation >= -1.0
                )
                and
                np.all(
                    observation <= 1.0
                )
            )

        except Exception:

            observation_valid = False

        return {
            "connected": True,
            "observation_shape": (
                self.STATE_SIZE,
            ),
            "observation_valid": (
                observation_valid
            ),
            "action_size": (
                self.ACTION_SIZE
            )
        }

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        pass