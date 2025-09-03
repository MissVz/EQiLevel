# src/rl/q_learning_agent.py
# AI687 HOS05A – EQiLevel: Q-Learning Agent Skeleton
# Purpose: Core class for tabular Q-learning with basic API and error handling

import os
import json
import random
from typing import Any, Dict, List

class QLearningAgent:
    def __init__(
        self,
        state_space_size: int,
        action_space_size: int,
        alpha: float = 0.1,
        gamma: float = 0.99,
        epsilon: float = 0.1,
        q_table: Dict[str, List[float]] = None
    ):
        """
        state_space_size: number of discrete states
        action_space_size: number of possible actions per state
        alpha: learning rate
        gamma: discount factor
        epsilon: exploration rate
        """
        self.n_states = state_space_size
        self.n_actions = action_space_size
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        # Q-table: { state_str : [q_val_for_action0, q_val_for_action1, …] }
        self.q_table = q_table if q_table is not None else {}
        print(f"[QLAgent] Initialized with {self.n_states} states, {self.n_actions} actions, "
              f"α={self.alpha}, γ={self.gamma}, ε={self.epsilon}")
    
    def _ensure_state(self, state: Any):
        """
        Ensure the state has an entry in the Q-table; initialize if missing.
        Prints when a new state is initialized.
        """
        key = str(state)
        if key not in self.q_table:
            self.q_table[key] = [0.0] * self.n_actions
            print(f"[QLAgent] New state initialized: '{key}' with Q-values {self.q_table[key]}")
        return key

    def choose_action(self, state: Any) -> int:
        """
        Choose an action using epsilon-greedy policy.
        Prints decision path and chosen action.
        """
        key = self._ensure_state(state)
        if random.random() < self.epsilon:
            action = random.randrange(self.n_actions)
            print(f"[QLAgent] Exploring: chose random action {action} for state '{key}'")
        else:
            qs = self.q_table[key]
            action = int(max(range(self.n_actions), key=lambda a: qs[a]))
            print(f"[QLAgent] Exploiting: chose best action {action} for state '{key}' (Q-values: {qs})")
        return action

    def update(self, state: Any, action: int, reward: float, next_state: Any, done: bool):
        """
        Apply the Q-learning update rule and print the updated Q-value.
        """
        key = self._ensure_state(state)
        next_key = self._ensure_state(next_state)
        q_current = self.q_table[key][action]
        q_next_max = 0.0 if done else max(self.q_table[next_key])
        # Q ← Q + α [ r + γ max Q' – Q ]
        new_q = q_current + self.alpha * (reward + self.gamma * q_next_max - q_current)
        self.q_table[key][action] = new_q
        print(f"[QLAgent] Updated Q[{key}][{action}]: {q_current:.4f} -> {new_q:.4f} (reward: {reward}, next_max: {q_next_max})")

    def save(self, path: str):
        """
        Save the Q-table to disk and print confirmation.
        """
        try:
            # Ensure parent directory is there (if any)
            parent = os.path.dirname(path) or "."
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.q_table, f, indent=2)
            print(f"[QLAgent] Q-table saved to: {path}")
        except Exception as e:
            print(f"⚠ Save error: {e} — retrying with fallback path.")
            # Fallback to current directory
            fallback = "q_table.json"
            try:
                with open(fallback, "w") as f:
                    json.dump(self.q_table, f)
                print(f"[QLAgent] Q-table saved to fallback: {fallback}")
            except Exception as e2:
                print(f"❌ Final save failure: {e2}")
                    
    @classmethod
    def load(cls, path: str, **kwargs) -> 'QLearningAgent':
        """
        Load a Q-table from disk and return a new agent instance.
        Prints confirmation of load.
        """
        with open(path, "r") as f:
            q_table = json.load(f)
        agent = cls(q_table=q_table, **kwargs)
        print(f"[QLAgent] Q-table loaded from: {path} (states: {len(q_table)})")
        return agent

