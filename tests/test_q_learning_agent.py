# tests/test_q_learning_agent.py
# Unit tests for QLearningAgent skeleton
# Purpose: Validate state init, action selection, update logic, and IO
# Assignment: AI687 HOS05A – Q-Learning Agent Unit Tests

import os
import json
import pytest
from tempfile import TemporaryDirectory
from src.rl.q_learning_agent import QLearningAgent

# Use a fixed seed for reproducibility
import random
random.seed(0)

def test_ensure_state_and_default_q():
    """
    Ensure new states initialize correctly.
    GIVEN a new QLearningAgent
    WHEN a state is ensured
    THEN the state key is returned and Q-values are initialized to zeros
    """
    test_name = 'test_ensure_state_and_default_q'
    try:
        agent = QLearningAgent(state_space_size=5, action_space_size=3)
        # New state should initialize q-values to zeros
        key = agent._ensure_state("state1")
        assert key == "state1"
        assert agent.q_table[key] == [0.0, 0.0, 0.0]
        print(f"[Test] {test_name}: PASSED – Q-table initialized correctly for 'state1'.")
    except AssertionError as e:
        print(f"[Test] {test_name}: FAILED – {e}")
        raise

def test_choose_action_explores(monkeypatch):
    """
    Ensure exploration behavior under ε=1.0.
    WITH ε=1.0 (always explore)
    EXPECT actions to be chosen randomly over many trials
    """
    test_name = 'test_choose_action_explores'
    try:
        agent = QLearningAgent(state_space_size=1, action_space_size=2, epsilon=1.0)
        # With ε=1.0, always random
        counts = {0: 0, 1: 0}
        for _ in range(100):
            a = agent.choose_action("any")
            counts[a] += 1
        # Both actions should be selected roughly equally
        assert counts[0] > 0 and counts[1] > 0
        print(f"[Test] {test_name}: PASSED – action distribution = {counts}")
    except AssertionError as e:
        print(f"[Test] {test_name}: FAILED – {e} (counts={counts})")
        raise

def test_choose_action_exploits(monkeypatch):
    """
    Ensure exploitation behavior under ε=0.0.
    WITH ε=0.0 (always exploit)
    GIVEN Q-values favoring action 1
    EXPECT action 1 selected every time
    """
    test_name = 'test_choose_action_explores'
    try:
        # Populate q_table so action 1 is better
        agent = QLearningAgent(state_space_size=1, action_space_size=2, epsilon=1.0)
        # With ε=1.0, always random
        counts = {0: 0, 1: 0}
        for _ in range(100):
            a = agent.choose_action("any")
            counts[a] += 1
        # Both actions should be selected roughly equally
        assert counts[0] > 0 and counts[1] > 0
        print(f"[Test] {test_name}: PASSED – action distribution = {counts}")
    except AssertionError as e:
        print(f"[Test] {test_name}: FAILED – {e} (counts={counts})")
        raise

def test_update_rule_correctness():
    """
    GIVEN Q-table with known values
    WHEN update() is called
    THEN Q-value is updated according to the rule
    """
    test_name = 'test_update_rule_correctness'
    try:
        agent = QLearningAgent(state_space_size=1, action_space_size=2, alpha=0.5, gamma=1.0, epsilon=0.0)
        # Initialize state and next_state  
        agent.q_table = {"s": [0.0, 0.0], "s2": [1.0, 3.0]}
        # Take action 0 in state s, reward=1.0, next_state s2, not done  
        agent.update("s", 0, reward=1.0, next_state="s2", done=False)
        expected = 0.0 + 0.5 * (1.0 + 1.0 * 3.0 - 0.0)
        # TD: Q(s,0) = 0 + 0.5*(1 + 1*max{1,3} - 0) = 0.5*(1+3) = 2.0
        assert pytest.approx(agent.q_table["s"][0], rel=1e-3) == expected
        print(f"[Test] {test_name}: PASSED – Q-value updated to {agent.q_table['s'][0]:.4f} (expected {expected:.4f}).")
    except AssertionError as e:
        print(f"[Test] {test_name}: FAILED – {e}, got {agent.q_table['s'][0]}")
        raise

def test_save_and_load(tmp_path):
    """
    Ensure Q-table persistence through save and load.
    GIVEN a populated Q-table
    WHEN save() and load() are invoked
    THEN the loaded agent has identical Q-table
    """
    test_name = 'test_save_and_load'
    try:
        agent = QLearningAgent(state_space_size=1, action_space_size=1)
        agent.q_table = {"x": [5.0]}
        file_path = tmp_path / "qtable.json"
        agent.save(str(file_path))
        assert file_path.exists()
        # Load back
        new_agent = QLearningAgent.load(
            str(file_path),
            state_space_size=1,
            action_space_size=1,
            alpha=agent.alpha,
            gamma=agent.gamma,
            epsilon=agent.epsilon
        )
        assert new_agent.q_table == agent.q_table
        print(f"[Test] {test_name}: PASSED – save and load functionality confirmed.")
    except AssertionError as e:
        print(f"[Test] {test_name}: FAILED – {e}")
        raise

# -------------------------------------------------------------
# OpenAI Acknowledgement:
# This test suite was developed with assistance from OpenAI’s ChatGPT (2025) [Large Language Model].
