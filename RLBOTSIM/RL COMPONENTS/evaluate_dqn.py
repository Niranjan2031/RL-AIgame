import os
import sys
import numpy as np


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

SRC_DIR = os.path.join(
    BASE_DIR,
    "src"
)

# dqn_agent.py is inside src/
if SRC_DIR not in sys.path:
    sys.path.insert(
        0,
        SRC_DIR
    )


# ============================================================
# IMPORTS
# ============================================================

from headless_shooter_env import HeadlessShooterEnv
from dqn_agent import DQNAgent


# ============================================================
# FINAL DQN CONFIGURATION
# ============================================================

STATE_SIZE = 34
ACTION_SIZE = 9

NUM_EPISODES = 30

MODEL_NAME = "rl_bot_1_dqn_final.pt"


# ============================================================
# MODEL PATH
# ============================================================

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    MODEL_NAME
)


# ============================================================
# ACTION NAMES
# ============================================================

ACTION_NAMES = {
    0: "IDLE",
    1: "FORWARD",
    2: "BACKWARD",
    3: "LEFT",
    4: "RIGHT",
    5: "SPRINT",
    6: "SHOOT",
    7: "RELOAD",
    8: "MELEE",
}


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 65)
    print("DQN EVALUATION")
    print("=" * 65)

    print(
        f"State size  : {STATE_SIZE}"
    )

    print(
        f"Action size : {ACTION_SIZE}"
    )

    print(
        f"Episodes    : {NUM_EPISODES}"
    )

    print(
        f"Model       : {MODEL_PATH}"
    )

    print("=" * 65)
    print()

    # --------------------------------------------------------
    # CHECK MODEL
    # --------------------------------------------------------

    if not os.path.exists(MODEL_PATH):

        print(
            "ERROR: DQN model was not found."
        )

        print()
        print(
            "Expected:"
        )

        print(
            MODEL_PATH
        )

        print()
        print(
            "Train the model first."
        )

        return

    # --------------------------------------------------------
    # ENVIRONMENT
    # --------------------------------------------------------

    print(
        "Creating headless environment..."
    )

    env = HeadlessShooterEnv(
        max_steps=3000
    )

    # --------------------------------------------------------
    # VALIDATE ENVIRONMENT
    # --------------------------------------------------------

    if env.observation_space.shape != (
        STATE_SIZE,
    ):

        raise RuntimeError(
            "Observation size mismatch. "
            f"Expected {STATE_SIZE}, "
            f"got {env.observation_space.shape}."
        )

    if env.action_space.n != ACTION_SIZE:

        raise RuntimeError(
            "Action size mismatch. "
            f"Expected {ACTION_SIZE}, "
            f"got {env.action_space.n}."
        )

    print(
        "Environment dimensions validated."
    )

    # --------------------------------------------------------
    # AGENT
    # --------------------------------------------------------

    print(
        "Creating DQN agent..."
    )

    agent = DQNAgent(
        state_size=STATE_SIZE,
        action_size=ACTION_SIZE,
        learning_rate=0.0005,
        gamma=0.99,
        epsilon=0.0,
        epsilon_min=0.0,
        epsilon_decay=1.0,
        batch_size=64,
        memory_size=100000,
        target_update_frequency=1000
    )

    # --------------------------------------------------------
    # LOAD MODEL
    # --------------------------------------------------------

    print()
    print(
        "Loading DQN model..."
    )

    agent.load(
        MODEL_PATH,
        training=False
    )

    # Force deterministic evaluation.
    agent.epsilon = 0.0

    print(
        "Model loaded successfully."
    )

    # ========================================================
    # EVALUATION VARIABLES
    # ========================================================

    rewards = []
    lengths = []

    damage_dealt = []
    damage_taken = []

    shots_fired = []
    shots_hit = []

    weapon_switches = []
    melee_attempts = []
    melee_hits = []
    health_pickups = []
    ammo_pickups = []
    enemies_defeated = []

    action_counts = {
        action: 0
        for action in range(
            ACTION_SIZE
        )
    }

    survived_episodes = 0
    defeated_player_episodes = 0
    defeated_bot_episodes = 0

    # ========================================================
    # EPISODES
    # ========================================================

    for episode in range(
        NUM_EPISODES
    ):

        state, info = env.reset()

        episode_reward = 0.0
        episode_length = 0

        # damage_dealt and damage_taken in the environment
        # are per-step values, while shots and weapon_switches
        # are cumulative episode counters. Accumulate damage
        # across the episode instead of reading only the final
        # step.
        episode_damage_dealt = 0.0
        episode_damage_taken = 0.0

        terminated = False
        truncated = False

        while not (
            terminated
            or truncated
        ):

            # ------------------------------------------------
            # DETERMINISTIC ACTION
            # ------------------------------------------------

            action = agent.choose_action(
                state,
                training=False
            )

            action_counts[action] += 1

            # ------------------------------------------------
            # STEP
            # ------------------------------------------------

            (
                next_state,
                reward,
                terminated,
                truncated,
                info
            ) = env.step(
                action
            )

            state = next_state

            episode_reward += reward
            episode_length += 1

            episode_damage_dealt += float(
                info.get(
                    "damage_dealt",
                    0.0
                )
            )

            episode_damage_taken += float(
                info.get(
                    "damage_taken",
                    0.0
                )
            )

            if episode_length >= 3000:

                break

        # ----------------------------------------------------
        # EPISODE STATS
        # ----------------------------------------------------

        rewards.append(
            episode_reward
        )

        lengths.append(
            episode_length
        )

        current_damage_dealt = episode_damage_dealt
        current_damage_taken = episode_damage_taken

        current_shots_fired = info.get(
            "shots_fired",
            0
        )

        current_shots_hit = info.get(
            "shots_hit",
            0
        )

        current_weapon_switches = info.get(
            "weapon_switches",
            0
        )

        current_melee_attempts = info.get(
            "melee_attempts",
            0
        )

        current_melee_hits = info.get(
            "melee_hits",
            0
        )

        current_health_pickups = info.get(
            "health_pickups_collected",
            0
        )

        current_ammo_pickups = info.get(
            "ammo_pickups_collected",
            0
        )

        current_enemies_defeated = info.get(
            "enemies_defeated",
            0
        )

        damage_dealt.append(
            current_damage_dealt
        )

        damage_taken.append(
            current_damage_taken
        )

        shots_fired.append(
            current_shots_fired
        )

        shots_hit.append(
            current_shots_hit
        )

        weapon_switches.append(
            current_weapon_switches
        )

        melee_attempts.append(
            current_melee_attempts
        )

        melee_hits.append(
            current_melee_hits
        )

        health_pickups.append(
            current_health_pickups
        )

        ammo_pickups.append(
            current_ammo_pickups
        )

        enemies_defeated.append(
            current_enemies_defeated
        )

        # ----------------------------------------------------
        # SURVIVAL
        # ----------------------------------------------------

        if env.bot.health > 0:

            survived_episodes += 1

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        if env.bot.health <= 0:

            defeated_bot_episodes += 1

            result = "BOT DEFEATED"

        elif current_enemies_defeated >= 2:

            defeated_player_episodes += 1

            result = "ALL ENEMIES DEFEATED"

        else:

            result = "TIME LIMIT"

        # ----------------------------------------------------
        # PRINT EPISODE
        # ----------------------------------------------------

        print(
            f"Episode "
            f"{episode + 1:3d}/{NUM_EPISODES} | "
            f"Reward "
            f"{episode_reward:9.2f} | "
            f"Length "
            f"{episode_length:4d} | "
            f"Damage "
            f"{current_damage_dealt:6.2f} | "
            f"Taken "
            f"{current_damage_taken:6.2f} | "
            f"Shots "
            f"{current_shots_fired:3d} | "
            f"Hits "
            f"{current_shots_hit:3d} | "
            f"{result}"
        )

    # ========================================================
    # FINAL STATISTICS
    # ========================================================

    average_reward = float(
        np.mean(rewards)
    )

    average_length = float(
        np.mean(lengths)
    )

    average_damage_dealt = float(
        np.mean(damage_dealt)
    )

    average_damage_taken = float(
        np.mean(damage_taken)
    )

    average_shots_fired = float(
        np.mean(shots_fired)
    )

    average_shots_hit = float(
        np.mean(shots_hit)
    )

    average_weapon_switches = float(
        np.mean(weapon_switches)
    )

    average_melee_attempts = float(
        np.mean(melee_attempts)
    )

    average_melee_hits = float(
        np.mean(melee_hits)
    )

    average_health_pickups = float(
        np.mean(health_pickups)
    )

    average_ammo_pickups = float(
        np.mean(ammo_pickups)
    )

    average_enemies_defeated = float(
        np.mean(enemies_defeated)
    )

    total_shots = sum(
        shots_fired
    )

    total_hits = sum(
        shots_hit
    )

    if total_shots > 0:

        hit_rate = (
            total_hits
            / total_shots
            * 100
        )

    else:

        hit_rate = 0.0

    survival_rate = (
        survived_episodes
        / NUM_EPISODES
        * 100
    )

    player_defeat_rate = (
        defeated_player_episodes
        / NUM_EPISODES
        * 100
    )

    bot_defeat_rate = (
        defeated_bot_episodes
        / NUM_EPISODES
        * 100
    )

    # ========================================================
    # RESULTS
    # ========================================================

    print()
    print()
    print("=" * 65)
    print("DQN EVALUATION RESULTS")
    print("=" * 65)

    print()

    print(
        f"Average reward       : "
        f"{average_reward:.2f}"
    )

    print(
        f"Average episode len  : "
        f"{average_length:.2f}"
    )

    print(
        f"Average damage dealt : "
        f"{average_damage_dealt:.2f}"
    )

    print(
        f"Average damage taken : "
        f"{average_damage_taken:.2f}"
    )

    print(
        f"Average shots fired  : "
        f"{average_shots_fired:.2f}"
    )

    print(
        f"Average shots hit    : "
        f"{average_shots_hit:.2f}"
    )

    print(
        f"Hit rate             : "
        f"{hit_rate:.2f}%"
    )

    print(
        f"Average weapon swaps : "
        f"{average_weapon_switches:.2f}"
    )

    print(
        f"Average melee tries  : "
        f"{average_melee_attempts:.2f}"
    )

    print(
        f"Average melee hits   : "
        f"{average_melee_hits:.2f}"
    )

    print(
        f"Avg health pickups   : "
        f"{average_health_pickups:.2f}"
    )

    print(
        f"Avg ammo pickups     : "
        f"{average_ammo_pickups:.2f}"
    )

    print(
        f"Avg enemies defeated : "
        f"{average_enemies_defeated:.2f} / 2"
    )

    print()

    print(
        f"Bot survival rate    : "
        f"{survival_rate:.2f}%"
    )

    print(
        f"All-enemies defeat rate: "
        f"{player_defeat_rate:.2f}%"
    )

    print(
        f"Bot defeat rate        : "
        f"{bot_defeat_rate:.2f}%"
    )

    # ========================================================
    # ACTION USAGE
    # ========================================================

    print()
    print("-" * 65)
    print("ACTION USAGE")
    print("-" * 65)

    total_actions = sum(
        action_counts.values()
    )

    for action in range(
        ACTION_SIZE
    ):

        count = action_counts[action]

        if total_actions > 0:

            percentage = (
                count
                / total_actions
                * 100
            )

        else:

            percentage = 0.0

        print(
            f"{action}: "
            f"{ACTION_NAMES[action]:10s} "
            f"{count:8d} "
            f"({percentage:6.2f}%)"
        )

    # ========================================================
    # COMBAT CHECK
    # ========================================================

    print()
    print("-" * 65)
    print("COMBAT CHECK")
    print("-" * 65)

    if total_shots > 0:

        print(
            "SHOOT action was used."
        )

    else:

        print(
            "WARNING: The model did not shoot."
        )

    if total_hits > 0:

        print(
            "Successful hits were recorded."
        )

    else:

        print(
            "WARNING: No successful hits were recorded."
        )

    if average_damage_dealt > 0:

        print(
            "The model dealt damage."
        )

    else:

        print(
            "WARNING: Average damage dealt is 0."
        )

    if sum(melee_hits) > 0:

        print(
            "Successful melee hits were recorded."
        )

    else:

        print(
            "No successful melee hits were recorded."
        )

    if sum(health_pickups) > 0:

        print(
            "Health pickup usage was recorded."
        )

    else:

        print(
            "No health pickups were collected."
        )

    if sum(ammo_pickups) > 0:

        print(
            "Ammo pickup usage was recorded."
        )

    else:

        print(
            "No ammo pickups were collected."
        )

    print()
    print("=" * 65)

    env.close()


if __name__ == "__main__":
    main()