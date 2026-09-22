import random
from collections import deque

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class QNetwork(nn.Module):
    def __init__(self, state_size, action_size):
        super(QNetwork, self).__init__()

        self.network = nn.Sequential(
            nn.Linear(state_size, 256),
            nn.ReLU(),

            nn.Linear(256, 256),
            nn.ReLU(),

            nn.Linear(256, action_size)
        )

    def forward(self, state):
        return self.network(state)


class DQNAgent:

    def __init__(
        self,
        state_size,
        action_size,
        learning_rate=0.0005,
        gamma=0.99,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.997,
        batch_size=64,
        memory_size=100000,
        target_update_frequency=1000
    ):

        self.state_size = state_size
        self.action_size = action_size

        self.gamma = gamma

        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        self.batch_size = batch_size
        self.target_update_frequency = target_update_frequency

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print(f"DQN device: {self.device}")

        if self.device.type == "cuda":
            print(f"GPU: {torch.cuda.get_device_name(0)}")

        # Online network
        self.q_network = QNetwork(
            state_size,
            action_size
        ).to(self.device)

        # Target network
        self.target_network = QNetwork(
            state_size,
            action_size
        ).to(self.device)

        self.target_network.load_state_dict(
            self.q_network.state_dict()
        )

        self.target_network.eval()

        self.optimizer = optim.Adam(
            self.q_network.parameters(),
            lr=learning_rate
        )

        self.loss_function = nn.SmoothL1Loss()

        self.memory = deque(
            maxlen=memory_size
        )

        self.training_steps = 0

    # ---------------------------------------------------------
    # STORE EXPERIENCE
    # ---------------------------------------------------------

    def remember(
        self,
        state,
        action,
        reward,
        next_state,
        done
    ):

        self.memory.append(
            (
                np.array(state, dtype=np.float32),
                int(action),
                float(reward),
                np.array(next_state, dtype=np.float32),
                bool(done)
            )
        )

    # ---------------------------------------------------------
    # SELECT ACTION
    # ---------------------------------------------------------

    def choose_action(self, state, training=True):
        if self.state_size == 34 and len(state) != 34:
            raise ValueError(f"Expected 34 observations, got {len(state)}.")

        # -----------------------------------------------------
        # EPSILON EXPLORATION
        # -----------------------------------------------------
        #
        # Observation 30 is the 75 px knife-range flag in the final 34-state contract.
        #
        # The original explorer selected all 9 actions with
        # equal probability. Because close-range encounters are
        # relatively short, action 8 (MELEE) could receive too
        # few useful training transitions before epsilon became
        # small.
        #
        # When the bot is actually inside knife range, increase
        # the chance of exploring MELEE. This only affects
        # epsilon-random training actions.
        #
        # IMPORTANT:
        # - It does NOT force MELEE during exploitation.
        # - It does NOT change the network architecture.
        # - It does NOT change evaluation when epsilon = 0.
        # -----------------------------------------------------

        if training and random.random() < self.epsilon:

            close_range = (
                len(state) > 30
                and float(state[30]) >= 0.5
            )

            if close_range and self.action_size >= 9:

                # 40% of exploratory close-range actions are
                # deliberately MELEE. The remaining 60% explore
                # the other actions normally.
                if random.random() < 0.40:
                    return 8

                other_actions = [
                    action
                    for action in range(self.action_size)
                    if action != 8
                ]

                return random.choice(
                    other_actions
                )

            return random.randrange(
                self.action_size
            )

        # -----------------------------------------------------
        # EXPLOITATION
        # -----------------------------------------------------

        state_tensor = torch.tensor(
            state,
            dtype=torch.float32,
            device=self.device
        ).unsqueeze(0)

        with torch.no_grad():

            q_values = self.q_network(
                state_tensor
            )

        return int(
            torch.argmax(q_values, dim=1).item()
        )

    # ---------------------------------------------------------
    # GET Q VALUES
    # ---------------------------------------------------------

    def get_q_values(self, state):

        state_tensor = torch.tensor(
            state,
            dtype=torch.float32,
            device=self.device
        ).unsqueeze(0)

        with torch.no_grad():

            q_values = self.q_network(
                state_tensor
            )

        return q_values.cpu().numpy()[0]

    # ---------------------------------------------------------
    # TRAIN
    # ---------------------------------------------------------

    def replay(self):

        if len(self.memory) < self.batch_size:

            return None

        batch = random.sample(
            self.memory,
            self.batch_size
        )

        states = np.array(
            [experience[0] for experience in batch],
            dtype=np.float32
        )

        actions = np.array(
            [experience[1] for experience in batch],
            dtype=np.int64
        )

        rewards = np.array(
            [experience[2] for experience in batch],
            dtype=np.float32
        )

        next_states = np.array(
            [experience[3] for experience in batch],
            dtype=np.float32
        )

        dones = np.array(
            [experience[4] for experience in batch],
            dtype=np.float32
        )

        states = torch.tensor(
            states,
            dtype=torch.float32,
            device=self.device
        )

        actions = torch.tensor(
            actions,
            dtype=torch.long,
            device=self.device
        )

        rewards = torch.tensor(
            rewards,
            dtype=torch.float32,
            device=self.device
        )

        next_states = torch.tensor(
            next_states,
            dtype=torch.float32,
            device=self.device
        )

        dones = torch.tensor(
            dones,
            dtype=torch.float32,
            device=self.device
        )

        # -----------------------------------------------------
        # CURRENT Q VALUES
        # -----------------------------------------------------

        current_q_values = self.q_network(
            states
        ).gather(
            1,
            actions.unsqueeze(1)
        ).squeeze(1)

        # -----------------------------------------------------
        # DOUBLE DQN
        # -----------------------------------------------------

        with torch.no_grad():

            # Online network chooses the next action
            next_actions = self.q_network(
                next_states
            ).argmax(
                dim=1
            )

            # Target network evaluates that action
            next_q_values = self.target_network(
                next_states
            ).gather(
                1,
                next_actions.unsqueeze(1)
            ).squeeze(1)

            target_q_values = (
                rewards
                + self.gamma
                * next_q_values
                * (1.0 - dones)
            )

        # -----------------------------------------------------
        # LOSS
        # -----------------------------------------------------

        loss = self.loss_function(
            current_q_values,
            target_q_values
        )

        self.optimizer.zero_grad()

        loss.backward()

        # Prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(
            self.q_network.parameters(),
            max_norm=1.0
        )

        self.optimizer.step()

        self.training_steps += 1

        # -----------------------------------------------------
        # TARGET NETWORK UPDATE
        # -----------------------------------------------------

        if (
            self.training_steps
            % self.target_update_frequency
            == 0
        ):

            self.target_network.load_state_dict(
                self.q_network.state_dict()
            )

        return float(loss.item())

    # ---------------------------------------------------------
    # EPSILON DECAY
    # ---------------------------------------------------------

    def decay_epsilon(self):

        if self.epsilon > self.epsilon_min:

            self.epsilon *= self.epsilon_decay

            self.epsilon = max(
                self.epsilon,
                self.epsilon_min
            )

    # ---------------------------------------------------------
    # SAVE MODEL
    # ---------------------------------------------------------

    def save(self, path):

        checkpoint = {

            "state_size": self.state_size,

            "action_size": self.action_size,

            "epsilon": self.epsilon,

            "training_steps": self.training_steps,

            "q_network": self.q_network.state_dict(),

            "target_network": self.target_network.state_dict(),

            "optimizer": self.optimizer.state_dict()
        }

        torch.save(
            checkpoint,
            path
        )

        print(f"Model saved: {path}")

    # ---------------------------------------------------------
    # LOAD MODEL
    # ---------------------------------------------------------

    def load(self, path, training=True):

        checkpoint = torch.load(
            path,
            map_location=self.device
        )

        saved_state_size = checkpoint.get(
            "state_size",
            None
        )

        saved_action_size = checkpoint.get(
            "action_size",
            None
        )

        if saved_state_size is not None:

            if saved_state_size != self.state_size:

                raise ValueError(
                    f"State size mismatch! "
                    f"Model has {saved_state_size}, "
                    f"but current environment has "
                    f"{self.state_size}."
                )

        if saved_action_size is not None:

            if saved_action_size != self.action_size:

                raise ValueError(
                    f"Action size mismatch! "
                    f"Model has {saved_action_size}, "
                    f"but current environment has "
                    f"{self.action_size}."
                )

        self.q_network.load_state_dict(
            checkpoint["q_network"]
        )

        if "target_network" in checkpoint:

            self.target_network.load_state_dict(
                checkpoint["target_network"]
            )

        else:

            self.target_network.load_state_dict(
                self.q_network.state_dict()
            )

        if training and "optimizer" in checkpoint:

            self.optimizer.load_state_dict(
                checkpoint["optimizer"]
            )

        self.epsilon = checkpoint.get(
            "epsilon",
            self.epsilon
        )

        self.training_steps = checkpoint.get(
            "training_steps",
            0
        )

        print(f"Model loaded: {path}")

        if training:

            print(
                f"Epsilon restored: "
                f"{self.epsilon:.4f}"
            )

        else:

            self.epsilon = 0.0

            print(
                "Evaluation mode: epsilon = 0"
            )

    # ---------------------------------------------------------
    # MEMORY SIZE
    # ---------------------------------------------------------

    def memory_size(self):

        return len(self.memory)