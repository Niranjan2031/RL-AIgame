import os
import sys
import time
import argparse

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
# RL25 CONFIGURATION
# ============================================================

STATE_SIZE = 28
ACTION_SIZE = 9

LEARNING_RATE = 0.0005
GAMMA = 0.99

EPSILON_START = 1.0
EPSILON_MIN = 0.05

# IMPORTANT:
# Epsilon is now decayed ONCE PER EPISODE,
# not once per environment step.
EPSILON_DECAY = 0.98

BATCH_SIZE = 64

MEMORY_SIZE = 100000

TARGET_UPDATE_FREQUENCY = 1000

DEFAULT_MINUTES = 2
DEFAULT_MAX_STEPS = 500000

CHECKPOINT_INTERVAL_MINUTES = 5


# ============================================================
# MODEL PATHS
# ============================================================

MODELS_DIR = os.path.join(
    BASE_DIR,
    "models"
)

os.makedirs(
    MODELS_DIR,
    exist_ok=True
)


FINAL_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "rl_bot_1_dqn_rl25_final.pt"
)

BEST_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "rl_bot_1_dqn_rl25_best.pt"
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
# ARGUMENTS
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description="Train RL25 DQN for Tactical Shooter."
    )

    parser.add_argument(
        "--minutes",
        type=float,
        default=DEFAULT_MINUTES,
        help="Maximum training time in minutes."
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        help="Maximum total environment steps."
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed."
    )

    return parser.parse_args()


# ============================================================
# CHECKPOINT PATH
# ============================================================

def checkpoint_path(minutes):

    minute_value = int(minutes)

    return os.path.join(
        MODELS_DIR,
        f"rl_bot_1_dqn_rl25_{minute_value:03d}min.pt"
    )


# ============================================================
# CONFIGURATION DISPLAY
# ============================================================

def print_configuration(
    minutes,
    max_steps
):

    print()
    print("=" * 65)
    print("RL25 DQN TRAINING")
    print("=" * 65)

    print(
        f"State size       : {STATE_SIZE}"
    )

    print(
        f"Action size      : {ACTION_SIZE}"
    )

    print(
        f"Training time    : {minutes:.1f} minutes"
    )

    print(
        f"Maximum steps    : {max_steps:,}"
    )

    print(
        f"Learning rate    : {LEARNING_RATE}"
    )

    print(
        f"Gamma            : {GAMMA}"
    )

    print(
        f"Epsilon start    : {EPSILON_START}"
    )

    print(
        f"Epsilon minimum  : {EPSILON_MIN}"
    )

    print(
        f"Epsilon decay    : {EPSILON_DECAY}"
        " per episode"
    )

    print(
        f"Batch size       : {BATCH_SIZE}"
    )

    print(
        f"Replay memory    : {MEMORY_SIZE:,}"
    )

    print(
        f"Target update    : every "
        f"{TARGET_UPDATE_FREQUENCY} steps"
    )

    print()
    print("Actions:")

    for action, name in ACTION_NAMES.items():

        print(
            f"  {action}: {name}"
        )

    print()

    print(
        "Weapon selection is automatic."
    )

    print(
        "RL weapon actions are NOT used."
    )

    print("=" * 65)
    print()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_arguments()

    minutes = max(
        0.1,
        args.minutes
    )

    max_steps = max(
        1,
        args.max_steps
    )

    print_configuration(
        minutes,
        max_steps
    )

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    print(
        "Creating headless environment..."
    )

    env = HeadlessShooterEnv(
        max_steps=3000,
        seed=args.seed
    )

    print(
        "Environment created."
    )

    print(
        f"Observation space: "
        f"{env.observation_space}"
    )

    print(
        f"Action space: "
        f"{env.action_space}"
    )

    # ========================================================
    # VALIDATE ENVIRONMENT
    # ========================================================

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

    # ========================================================
    # DQN AGENT
    # ========================================================

    print()
    print(
        "Creating DQN agent..."
    )

    agent = DQNAgent(
        state_size=STATE_SIZE,
        action_size=ACTION_SIZE,
        learning_rate=LEARNING_RATE,
        gamma=GAMMA,
        epsilon=EPSILON_START,
        epsilon_min=EPSILON_MIN,
        epsilon_decay=EPSILON_DECAY,
        batch_size=BATCH_SIZE,
        memory_size=MEMORY_SIZE,
        target_update_frequency=TARGET_UPDATE_FREQUENCY
    )

    print(
        "DQN agent created."
    )

    # ========================================================
    # TRAINING VARIABLES
    # ========================================================

    total_steps = 0
    episode_number = 0

    start_time = time.time()

    next_checkpoint_time = (
        start_time
        + CHECKPOINT_INTERVAL_MINUTES * 60
    )

    best_average_reward = -float(
        "inf"
    )

    episode_rewards = []
    episode_lengths = []

    total_damage_dealt = 0.0
    total_damage_taken = 0.0

    total_shots_fired = 0
    total_shots_hit = 0

    total_weapon_switches = 0

    # ========================================================
    # RESET
    # ========================================================

    state, info = env.reset(
        seed=args.seed
    )

    episode_reward = 0.0
    episode_length = 0

    # These track cumulative environment counters
    # so we only add the NEW amount from each step.
    previous_shots_fired = info.get(
        "shots_fired",
        0
    )

    previous_shots_hit = info.get(
        "shots_hit",
        0
    )

    previous_weapon_switches = info.get(
        "weapon_switches",
        0
    )

    # ========================================================
    # TRAINING LOOP
    # ========================================================

    print()
    print(
        "Training started..."
    )

    print(
        "Press Ctrl+C to stop safely."
    )

    print()

    try:

        while total_steps < max_steps:

            elapsed_time = (
                time.time()
                - start_time
            )

            if elapsed_time >= minutes * 60:

                print()
                print(
                    "Training time limit reached."
                )

                break

            # =================================================
            # CHOOSE ACTION
            # =================================================

            action = agent.choose_action(
                state,
                training=True
            )

            # =================================================
            # ENVIRONMENT STEP
            # =================================================

            (
                next_state,
                reward,
                terminated,
                truncated,
                info
            ) = env.step(
                action
            )

            # =================================================
            # STORE EXPERIENCE
            # =================================================

            agent.remember(
                state,
                action,
                reward,
                next_state,
                terminated or truncated
            )

            # =================================================
            # TRAIN DQN
            # =================================================

            agent.replay()

            # =================================================
            # UPDATE STATE
            # =================================================

            state = next_state

            episode_reward += reward
            episode_length += 1

            total_steps += 1

            # =================================================
            # DAMAGE
            # =================================================

            total_damage_dealt += info.get(
                "damage_dealt",
                0.0
            )

            total_damage_taken += info.get(
                "damage_taken",
                0.0
            )

            # =================================================
            # CUMULATIVE COUNTER DELTAS
            # =================================================

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

            shot_delta = (
                current_shots_fired
                - previous_shots_fired
            )

            hit_delta = (
                current_shots_hit
                - previous_shots_hit
            )

            switch_delta = (
                current_weapon_switches
                - previous_weapon_switches
            )

            # Safety against counter resets.
            if shot_delta < 0:
                shot_delta = current_shots_fired

            if hit_delta < 0:
                hit_delta = current_shots_hit

            if switch_delta < 0:
                switch_delta = current_weapon_switches

            total_shots_fired += shot_delta
            total_shots_hit += hit_delta
            total_weapon_switches += switch_delta

            previous_shots_fired = (
                current_shots_fired
            )

            previous_shots_hit = (
                current_shots_hit
            )

            previous_weapon_switches = (
                current_weapon_switches
            )

            # =================================================
            # EPISODE END
            # =================================================

            if (
                terminated
                or truncated
            ):

                episode_number += 1

                episode_rewards.append(
                    episode_reward
                )

                episode_lengths.append(
                    episode_length
                )

                # ---------------------------------------------
                # EPSILON DECAY
                # ---------------------------------------------
                # IMPORTANT:
                # Only decay once per episode.
                # This prevents epsilon from immediately
                # falling to 0.05 after a few thousand steps.

                agent.epsilon = max(
                    agent.epsilon_min,
                    agent.epsilon
                    * agent.epsilon_decay
                )

                recent_rewards = (
                    episode_rewards[-50:]
                )

                recent_lengths = (
                    episode_lengths[-50:]
                )

                average_reward = float(
                    np.mean(
                        recent_rewards
                    )
                )

                average_length = float(
                    np.mean(
                        recent_lengths
                    )
                )

                # ---------------------------------------------
                # BEST MODEL
                # ---------------------------------------------

                if (
                    len(episode_rewards) >= 5
                    and
                    average_reward
                    > best_average_reward
                ):

                    best_average_reward = (
                        average_reward
                    )

                    agent.save(
                        BEST_MODEL_PATH
                    )

                    print(
                        f"New best model saved: "
                        f"{BEST_MODEL_PATH}"
                    )

                # ---------------------------------------------
                # EPISODE OUTPUT
                # ---------------------------------------------

                print(
                    f"Episode "
                    f"{episode_number:5d} | "
                    f"Steps "
                    f"{total_steps:7d} | "
                    f"Reward "
                    f"{episode_reward:9.2f} | "
                    f"Avg50 "
                    f"{average_reward:9.2f} | "
                    f"Length "
                    f"{episode_length:5d} | "
                    f"Epsilon "
                    f"{agent.epsilon:.4f}"
                )

                # ---------------------------------------------
                # RESET
                # ---------------------------------------------

                state, info = env.reset()

                episode_reward = 0.0
                episode_length = 0

                previous_shots_fired = info.get(
                    "shots_fired",
                    0
                )

                previous_shots_hit = info.get(
                    "shots_hit",
                    0
                )

                previous_weapon_switches = info.get(
                    "weapon_switches",
                    0
                )

            # =================================================
            # CHECKPOINT
            # =================================================

            current_time = time.time()

            if current_time >= next_checkpoint_time:

                elapsed_minutes = (
                    current_time
                    - start_time
                ) / 60.0

                checkpoint = checkpoint_path(
                    elapsed_minutes
                )

                agent.save(
                    checkpoint
                )

                print()
                print(
                    f"Checkpoint saved at "
                    f"{elapsed_minutes:.1f} minutes:"
                )

                print(
                    checkpoint
                )

                print()

                next_checkpoint_time = (
                    current_time
                    + CHECKPOINT_INTERVAL_MINUTES
                    * 60
                )

    except KeyboardInterrupt:

        print()
        print(
            "Training interrupted by user."
        )

    finally:

        # =====================================================
        # FINAL SAVE
        # =====================================================

        print()
        print(
            "Saving final model..."
        )

        agent.save(
            FINAL_MODEL_PATH
        )

        # =====================================================
        # CLOSE
        # =====================================================

        env.close()

    # ========================================================
    # FINAL STATISTICS
    # ========================================================

    elapsed_seconds = (
        time.time()
        - start_time
    )

    elapsed_minutes = (
        elapsed_seconds / 60.0
    )

    print()
    print("=" * 65)
    print("TRAINING COMPLETE")
    print("=" * 65)

    print(
        f"Training time       : "
        f"{elapsed_minutes:.2f} minutes"
    )

    print(
        f"Total steps         : "
        f"{total_steps:,}"
    )

    print(
        f"Episodes            : "
        f"{episode_number:,}"
    )

    print(
        f"Final epsilon       : "
        f"{agent.epsilon:.4f}"
    )

    if episode_rewards:

        print(
            f"Average reward "
            f"(last 50)          : "
            f"{np.mean(episode_rewards[-50:]):.2f}"
        )

        print(
            f"Average length "
            f"(last 50)          : "
            f"{np.mean(episode_lengths[-50:]):.2f}"
        )

    print()

    print(
        f"Total damage dealt  : "
        f"{total_damage_dealt:.2f}"
    )

    print(
        f"Total damage taken  : "
        f"{total_damage_taken:.2f}"
    )

    print(
        f"Total shots fired   : "
        f"{total_shots_fired:,}"
    )

    print(
        f"Total shots hit     : "
        f"{total_shots_hit:,}"
    )

    if total_shots_fired > 0:

        hit_rate = (
            total_shots_hit
            / total_shots_fired
            * 100.0
        )

    else:

        hit_rate = 0.0

    print(
        f"Hit rate            : "
        f"{hit_rate:.2f}%"
    )

    print(
        f"Weapon switches     : "
        f"{total_weapon_switches:,}"
    )

    print()

    print(
        "Final model:"
    )

    print(
        FINAL_MODEL_PATH
    )

    print()

    print(
        "Best model:"
    )

    print(
        BEST_MODEL_PATH
    )

    print("=" * 65)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()