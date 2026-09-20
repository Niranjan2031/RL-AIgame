from headless_shooter_env import HeadlessShooterEnv


def main():

    print("=" * 60)
    print("RL25 HEADLESS ENVIRONMENT TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # CREATE ENVIRONMENT
    # --------------------------------------------------------

    env = HeadlessShooterEnv(
        max_steps=3000
    )

    print()
    print(
        f"Action space      : {env.action_space}"
    )

    print(
        f"Observation space : {env.observation_space}"
    )

    print(
        f"Observation shape : "
        f"{env.observation_space.shape}"
    )

    # --------------------------------------------------------
    # CHECK ACTION SPACE
    # --------------------------------------------------------

    assert env.action_space.n == 9, (
        f"Expected 9 actions, "
        f"got {env.action_space.n}"
    )

    print(
        "PASS: Action space = 9"
    )

    # --------------------------------------------------------
    # CHECK OBSERVATION SPACE
    # --------------------------------------------------------

    assert (
        env.observation_space.shape
        == (28,)
    ), (
        "Expected observation shape "
        "(28,), got "
        f"{env.observation_space.shape}"
    )

    print(
        "PASS: Observation space = 28"
    )

    # --------------------------------------------------------
    # CHECK OBSTACLES
    # --------------------------------------------------------

    print()
    print(
        f"Obstacle count    : "
        f"{len(env.obstacles)}"
    )

    if len(env.obstacles) > 0:

        print(
            "PASS: Obstacles loaded."
        )

    else:

        print(
            "WARNING: No Tiled obstacles "
            "were loaded. Fallback may be active."
        )

    # --------------------------------------------------------
    # CHECK PICKUPS
    # --------------------------------------------------------

    print(
        f"Health pickups    : "
        f"{len(env.health_pickups)}"
    )

    print(
        f"Ammo pickups      : "
        f"{len(env.ammo_pickups)}"
    )

    assert len(
        env.health_pickups
    ) == 3, (
        "Expected 3 health pickups."
    )

    assert len(
        env.ammo_pickups
    ) == 3, (
        "Expected 3 ammo pickups."
    )

    print(
        "PASS: Pickup counts are correct."
    )

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    print()
    print(
        "Testing reset..."
    )

    observation, info = env.reset(
        seed=42
    )

    print(
        f"Observation shape : "
        f"{observation.shape}"
    )

    print(
        f"Observation dtype : "
        f"{observation.dtype}"
    )

    assert observation.shape == (
        28,
    )

    assert observation.dtype.name == (
        "float32"
    )

    print(
        "PASS: Reset returned valid "
        "28-value float32 observation."
    )

    # --------------------------------------------------------
    # OBSERVATION RANGE
    # --------------------------------------------------------

    assert (
        observation >= -1.0
    ).all(), (
        "Observation contains "
        "values below -1."
    )

    assert (
        observation <= 1.0
    ).all(), (
        "Observation contains "
        "values above 1."
    )

    print(
        "PASS: Observation values "
        "are within [-1, 1]."
    )

    # --------------------------------------------------------
    # TEST ALL 9 ACTIONS
    # --------------------------------------------------------

    print()
    print(
        "Testing all 9 actions..."
    )

    action_names = {
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

    for action in range(9):

        observation, reward, terminated, truncated, info = (
            env.step(action)
        )

        assert observation.shape == (
            28,
        )

        assert (
            observation >= -1.0
        ).all()

        assert (
            observation <= 1.0
        ).all()

        print(
            f"  Action {action}: "
            f"{action_names[action]:10s} "
            f"PASS"
        )

        if terminated or truncated:

            print(
                "Episode ended during "
                "action testing."
            )

            observation, info = env.reset()

    # --------------------------------------------------------
    # TEST MULTIPLE RANDOM STEPS
    # --------------------------------------------------------

    print()
    print(
        "Testing 100 random steps..."
    )

    observation, info = env.reset(
        seed=123
    )

    for step in range(100):

        action = env.action_space.sample()

        observation, reward, terminated, truncated, info = (
            env.step(action)
        )

        assert observation.shape == (
            28,
        )

        assert (
            observation >= -1.0
        ).all()

        assert (
            observation <= 1.0
        ).all()

        if terminated or truncated:

            observation, info = env.reset()

    print(
        "PASS: 100 random environment "
        "steps completed."
    )

    # --------------------------------------------------------
    # CHECK INFO
    # --------------------------------------------------------

    required_info_keys = [
        "damage_dealt",
        "damage_taken",
        "shots_fired",
        "shots_hit",
        "weapon_switches",
    ]

    print()
    print(
        "Checking info dictionary..."
    )

    for key in required_info_keys:

        assert key in info, (
            f"Missing info key: {key}"
        )

        print(
            f"  {key:20s} PASS"
        )

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    env.close()

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "ALL RL25 HEADLESS ENVIRONMENT TESTS PASSED"
    )
    print("=" * 60)

    print()
    print("RL25 configuration:")
    print("  Actions       : 9")
    print("  Observations  : 28")
    print("  Health pickups: 3")
    print("  Ammo pickups  : 3")
    print("  DQN actions   : IDLE / MOVE / SHOOT / RELOAD / MELEE")
    print()
    print(
        "Ready for short sanity training."
    )


if __name__ == "__main__":

    main()