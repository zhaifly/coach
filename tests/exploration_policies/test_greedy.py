import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest

from spaces import Discrete, Box
from exploration_policies.greedy import Greedy
import numpy as np


@pytest.mark.unit_test
def test_get_action():
    # discrete control
    action_space = Discrete(3)
    policy = Greedy(action_space)

    best_action = policy.get_action(np.array([10, 20, 30]))
    assert best_action == 2

    # continuous control
    action_space = Box(np.array([10]))
    policy = Greedy(action_space)

    best_action = policy.get_action(np.array([1, 1, 1]))
    assert np.all(best_action == np.array([1, 1, 1]))


@pytest.mark.unit_test
def test_get_control_param():
    action_space = Discrete(3)
    policy = Greedy(action_space)
    assert policy.get_control_param() == 0

