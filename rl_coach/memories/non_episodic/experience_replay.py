#
# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import List, Tuple, Union, Dict, Any

import numpy as np
from rl_coach.utils import ReaderWriterLock

from rl_coach.core_types import Transition
from rl_coach.memories.memory import Memory, MemoryGranularity, MemoryParameters


class ExperienceReplayParameters(MemoryParameters):
    def __init__(self):
        super().__init__()
        self.max_size = (MemoryGranularity.Transitions, 1000000)
        self.allow_duplicates_in_batch_sampling = True

    @property
    def path(self):
        return 'rl_coach.memories.non_episodic.experience_replay:ExperienceReplay'


class ExperienceReplay(Memory):
    """
    A regular replay buffer which stores transition without any additional structure
    """
    def __init__(self, max_size: Tuple[MemoryGranularity, int], allow_duplicates_in_batch_sampling: bool=True):
        """
        :param max_size: the maximum number of transitions or episodes to hold in the memory
        :param allow_duplicates_in_batch_sampling: allow having the same transition multiple times in a batch
        """
        super().__init__(max_size)
        if max_size[0] != MemoryGranularity.Transitions:
            raise ValueError("Experience replay size can only be configured in terms of transitions")
        self.transitions = []
        self._num_transitions = 0
        self.allow_duplicates_in_batch_sampling = allow_duplicates_in_batch_sampling

        self.reader_writer_lock = ReaderWriterLock()

    def length(self) -> int:
        """
        Get the number of transitions in the ER
        """
        return self.num_transitions()

    def num_transitions(self) -> int:
        """
        Get the number of transitions in the ER
        """
        return self._num_transitions

    def sample(self, size: int) -> List[Transition]:
        """
        Sample a batch of transitions form the replay buffer. If the requested size is larger than the number
        of samples available in the replay buffer then the batch will return empty.
        :param size: the size of the batch to sample
        :param beta: the beta parameter used for importance sampling
        :return: a batch (list) of selected transitions from the replay buffer
        """
        self.reader_writer_lock.lock_writing()

        if self.allow_duplicates_in_batch_sampling:
            transitions_idx = np.random.randint(self.num_transitions(), size=size)

        else:
            if self.num_transitions() >= size:
                transitions_idx = np.random.choice(self.num_transitions(), size=size, replace=False)
            else:
                raise ValueError("The replay buffer cannot be sampled since there are not enough transitions yet. "
                                 "There are currently {} transitions".format(self.num_transitions()))

        batch = [self.transitions[i] for i in transitions_idx]

        self.reader_writer_lock.release_writing()

        return batch

    def _enforce_max_length(self) -> None:
        """
        Make sure that the size of the replay buffer does not pass the maximum size allowed.
        If it passes the max size, the oldest transition in the replay buffer will be removed.
        This function does not use locks since it is only called internally
        :return: None
        """
        granularity, size = self.max_size
        if granularity == MemoryGranularity.Transitions:
            while size != 0 and self.num_transitions() > size:
                self.remove_transition(0, False)
        else:
            raise ValueError("The granularity of the replay buffer can only be set in terms of transitions")

    def store(self, transition: Transition, lock: bool=True) -> None:
        """
        Store a new transition in the memory.
        :param transition: a transition to store
        :param lock: if true, will lock the readers writers lock. this can cause a deadlock if an inheriting class
                     locks and then calls store with lock = True
        :return: None
        """
        if lock:
            self.reader_writer_lock.lock_writing_and_reading()

        self._num_transitions += 1
        self.transitions.append(transition)
        self._enforce_max_length()

        if lock:
            self.reader_writer_lock.release_writing_and_reading()

    def get_transition(self, transition_index: int, lock: bool=True) -> Union[None, Transition]:
        """
        Returns the transition in the given index. If the transition does not exist, returns None instead.
        :param transition_index: the index of the transition to return
        :param lock: use write locking if this is a shared memory
        :return: the corresponding transition
        """
        if lock:
            self.reader_writer_lock.lock_writing()

        if self.length() == 0 or transition_index >= self.length():
            transition = None
        else:
            transition = self.transitions[transition_index]

        if lock:
            self.reader_writer_lock.release_writing()

        return transition

    def remove_transition(self, transition_index: int, lock: bool=True) -> None:
        """
        Remove the transition in the given index.
        This does not remove the transition from the segment trees! it is just used to remove the transition
        from the transitions list
        :param transition_index: the index of the transition to remove
        :return: None
        """
        if lock:
            self.reader_writer_lock.lock_writing_and_reading()

        if self.num_transitions() > transition_index:
            self._num_transitions -= 1
            del self.transitions[transition_index]

        if lock:
            self.reader_writer_lock.release_writing_and_reading()

    # for API compatibility
    def get(self, transition_index: int, lock: bool=True) -> Union[None, Transition]:
        """
        Returns the transition in the given index. If the transition does not exist, returns None instead.
        :param transition_index: the index of the transition to return
        :return: the corresponding transition
        """
        return self.get_transition(transition_index, lock)

    # for API compatibility
    def remove(self, transition_index: int, lock: bool=True):
        """
        Remove the transition in the given index
        :param transition_index: the index of the transition to remove
        :return: None
        """
        self.remove_transition(transition_index, lock)

    def update_last_transition_info(self, info: Dict[str, Any]) -> None:
        """
        Update the info of the last transition stored in the memory
        :param info: the new info to append to the existing info
        :return: None
        """
        self.reader_writer_lock.lock_writing_and_reading()

        if self.length() == 0:
            raise ValueError("There are no transition in the replay buffer")
        self.transitions[-1].info.update(info)

        self.reader_writer_lock.release_writing_and_reading()

    def clean(self, lock: bool=True) -> None:
        """
        Clean the memory by removing all the episodes
        :return: None
        """
        if lock:
            self.reader_writer_lock.lock_writing_and_reading()

        self.transitions = []
        self._num_transitions = 0

        if lock:
            self.reader_writer_lock.release_writing_and_reading()

    def mean_reward(self) -> np.ndarray:
        """
        Get the mean reward in the replay buffer
        :return: the mean reward
        """
        self.reader_writer_lock.lock_writing()

        mean = np.mean([transition.reward for transition in self.transitions])

        self.reader_writer_lock.release_writing()

        return mean
