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
from typing import Union

from agents.value_optimization_agent import ValueOptimizationAgent
from exploration_policies.ou_process import OUProcessParameters
import numpy as np
from core_types import ActionInfo, EnvironmentSteps
from spaces import Box
from configurations import AlgorithmParameters, AgentParameters, MiddlewareTypes, OutputTypes, \
    NetworkParameters, InputEmbedderParameters
from memories.episodic_experience_replay import EpisodicExperienceReplayParameters


class NAFNetworkParameters(NetworkParameters):
    def __init__(self):
        super().__init__()
        self.input_types = {'observation': InputEmbedderParameters()}
        self.middleware_type = MiddlewareTypes.FC
        self.output_types = [OutputTypes.NAF]
        self.loss_weights = [1.0]
        self.hidden_layers_activation_function = 'relu'
        self.optimizer_type = 'Adam'
        self.learning_rate = 0.001
        self.async_training = True
        self.create_target_network = True


class NAFAlgorithmParameters(AlgorithmParameters):
    def __init__(self):
        super().__init__()
        self.num_consecutive_training_steps = 5
        self.num_steps_between_copying_online_weights_to_target = EnvironmentSteps(1)
        self.rate_for_copying_weights_to_target = 0.001


class NAFAgentParameters(AgentParameters):
    def __init__(self):
        super().__init__(algorithm=NAFAlgorithmParameters(),
                         exploration=OUProcessParameters(),
                         memory=EpisodicExperienceReplayParameters(),
                         networks={"main": NAFNetworkParameters()})

    @property
    def path(self):
        return 'agents.naf_agent:NAFAgent'


# Normalized Advantage Functions - https://arxiv.org/pdf/1603.00748.pdf
class NAFAgent(ValueOptimizationAgent):
    def __init__(self, agent_parameters, parent: Union['LevelManager', 'CompositeAgent']=None):
        super().__init__(agent_parameters, parent)
        self.l_values = self.register_signal("L")
        self.a_values = self.register_signal("Advantage")
        self.mu_values = self.register_signal("Action")
        self.v_values = self.register_signal("V")
        self.TD_targets = self.register_signal("TD targets")

    def learn_from_batch(self, batch):
        current_states, next_states, actions, rewards, game_overs, _ = self.extract_batch(batch, 'main')

        # TD error = r + discount*v_st_plus_1 - q_st
        v_st_plus_1 = self.networks['main'].target_network.predict(
            next_states,
            self.networks['main'].target_network.output_heads[0].V,
            squeeze_output=False,
        )
        TD_targets = np.expand_dims(rewards, -1) + \
                     (1.0 - np.expand_dims(game_overs, -1)) * self.ap.algorithm.discount * v_st_plus_1

        if len(actions.shape) == 1:
            actions = np.expand_dims(actions, -1)

        self.TD_targets.add_sample(TD_targets)

        result = self.networks['main'].train_and_sync_networks({**current_states, 'output_0_0': actions}, TD_targets)
        total_loss, losses, unclipped_grads = result[:3]

        return total_loss, losses, unclipped_grads

    def choose_action(self, curr_state):
        if type(self.spaces.action) != Box:
            raise ValueError('NAF works only for continuous control problems')

        # convert to batch so we can run it through the network
        tf_input_state = self.dict_state_to_batches_dict(curr_state, 'main')
        naf_head = self.networks['main'].online_network.output_heads[0]
        action_values = self.networks['main'].online_network.predict(tf_input_state, outputs=naf_head.mu,
                                                                     squeeze_output=False)

        # get the actual action to use
        action = self.exploration_policy.get_action(action_values)

        # get the internal values for logging
        outputs = [naf_head.mu, naf_head.Q, naf_head.L, naf_head.A, naf_head.V]
        result = self.networks['main'].online_network.predict(
            {**tf_input_state, 'output_0_0': action_values},
            outputs=outputs
        )
        mu, Q, L, A, V = result

        # store the q values statistics for logging
        self.q_values.add_sample(Q)
        self.l_values.add_sample(L)
        self.a_values.add_sample(A)
        self.mu_values.add_sample(mu)
        self.v_values.add_sample(V)

        action_info = ActionInfo(action=action, action_value=Q)
        
        return action_info
