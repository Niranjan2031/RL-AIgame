"""
test_dqn.py

Quick validation of the DQN implementation.

Run:
    python test_dqn.py
"""

import numpy as np
import torch

from dqn_agent import DQNAgent, QNetwork, ReplayBuffer


STATE_SIZE = 20
ACTION_SIZE = 13


def run_tests():

    # =====================================================
    # NETWORK
    # =====================================================

    network = QNetwork(
        STATE_SIZE,
        ACTION_SIZE
    )

    dummy_state = torch.zeros(
        1,
        STATE_SIZE
    )

    q_values = network(
        dummy_state
    )

    assert q_values.shape == (
        1,
        ACTION_SIZE
    )

    print("PASS: Q-network 20 -> 13")

    # =====================================================
    # REPLAY BUFFER
    # =====================================================

    buffer = ReplayBuffer(
        capacity=100
    )

    state = np.zeros(
        STATE_SIZE,
        dtype=np.float32
    )

    next_state = np.ones(
        STATE_SIZE,
        dtype=np.float32
    )

    for i in range(70):
        buffer.add(
            state,
            i % ACTION_SIZE,
            1.0,
            next_state,
            False
        )

    assert len(buffer) == 70

    (
        states,
        actions,
        rewards,
        next_states,
        dones
    ) = buffer.sample(32)

    assert states.shape == (
        32,
        STATE_SIZE
    )

    assert actions.shape == (32,)
    assert rewards.shape == (32,)
    assert next_states.shape == (
        32,
        STATE_SIZE
    )
    assert dones.shape == (32,)

    print("PASS: replay buffer")

    # =====================================================
    # DQN AGENT
    # =====================================================

    agent = DQNAgent(
        state_size=STATE_SIZE,
        action_size=ACTION_SIZE,
        batch_size=32
    )

    assert agent.state_size == 20
    assert agent.action_size == 13

    random_action = agent.select_action(
        state,
        training=True
    )

    assert 0 <= random_action < ACTION_SIZE

    print("PASS: epsilon-greedy action selection")

    # Fill replay memory.
    for i in range(40):
        agent.remember(
            state,
            i % ACTION_SIZE,
            1.0,
            next_state,
            False
        )

    loss = agent.train_step()

    assert loss is not None
    assert np.isfinite(loss)

    print("PASS: DQN gradient update")

    old_epsilon = agent.epsilon

    agent.decay_epsilon()

    assert agent.epsilon < old_epsilon

    print("PASS: epsilon decay")

    # =====================================================
    # SAVE / LOAD
    # =====================================================

    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:

        model_path = (
            Path(temp_dir) /
            "test_dqn.pt"
        )

        agent.save(model_path)

        loaded_agent = DQNAgent(
            state_size=STATE_SIZE,
            action_size=ACTION_SIZE,
            batch_size=32
        )

        loaded_agent.load(
            model_path,
            training=True
        )

        loaded_q_values = (
            loaded_agent.get_q_values(
                state
            )
        )

        original_q_values = (
            agent.get_q_values(
                state
            )
        )

        assert np.allclose(
            original_q_values,
            loaded_q_values
        )

    print("PASS: model save/load")

    print("\nAll DQN tests passed.")


if __name__ == "__main__":
    run_tests()
