from rl_coach.agents.actor_critic_agent import ActorCriticAgentParameters
from rl_coach.architectures.tensorflow_components.architecture import Dense
from rl_coach.architectures.tensorflow_components.middlewares.lstm_middleware import LSTMMiddlewareParameters
from rl_coach.base_parameters import VisualizationParameters, InputEmbedderParameters, MiddlewareScheme, PresetValidationParameters
from rl_coach.environments.environment import MaxDumpMethod, SelectedPhaseOnlyDumpMethod, SingleLevelSelection
from rl_coach.environments.gym_environment import Mujoco, mujoco_v2, MujocoInputFilter
from rl_coach.exploration_policies.continuous_entropy import ContinuousEntropyParameters
from rl_coach.filters.observation.observation_normalization_filter import ObservationNormalizationFilter
from rl_coach.graph_managers.basic_rl_graph_manager import BasicRLGraphManager
from rl_coach.graph_managers.graph_manager import ScheduleParameters

from rl_coach.core_types import TrainingSteps, EnvironmentEpisodes, EnvironmentSteps, RunPhase
from rl_coach.filters.reward.reward_rescale_filter import RewardRescaleFilter

####################
# Graph Scheduling #
####################
schedule_params = ScheduleParameters()
schedule_params.improve_steps = TrainingSteps(10000000000)
schedule_params.steps_between_evaluation_periods = EnvironmentEpisodes(20)
schedule_params.evaluation_steps = EnvironmentEpisodes(1)
schedule_params.heatup_steps = EnvironmentSteps(0)

#########
# Agent #
#########
agent_params = ActorCriticAgentParameters()
agent_params.algorithm.apply_gradients_every_x_episodes = 1
agent_params.algorithm.num_steps_between_gradient_updates = 20
agent_params.algorithm.beta_entropy = 0.005
agent_params.network_wrappers['main'].learning_rate = 0.00002
agent_params.network_wrappers['main'].input_embedders_parameters['observation'] = \
    InputEmbedderParameters(scheme=[Dense([200])])
agent_params.network_wrappers['main'].middleware_parameters = LSTMMiddlewareParameters(scheme=MiddlewareScheme.Empty,
                                                                                       number_of_lstm_cells=128)

agent_params.input_filter = MujocoInputFilter()
agent_params.input_filter.add_reward_filter('rescale', RewardRescaleFilter(1/20.))
agent_params.input_filter.add_observation_filter('observation', 'normalize', ObservationNormalizationFilter())

agent_params.exploration = ContinuousEntropyParameters()

###############
# Environment #
###############
env_params = Mujoco()
env_params.level = SingleLevelSelection(mujoco_v2)

vis_params = VisualizationParameters()
vis_params.video_dump_methods = [SelectedPhaseOnlyDumpMethod(RunPhase.TEST), MaxDumpMethod()]
vis_params.dump_mp4 = False

########
# Test #
########
preset_validation_params = PresetValidationParameters()
preset_validation_params.test = True
preset_validation_params.min_reward_threshold = 400
preset_validation_params.max_episodes_to_achieve_reward = 1000
preset_validation_params.num_workers = 8
preset_validation_params.reward_test_level = 'inverted_pendulum'
preset_validation_params.trace_test_levels = ['inverted_pendulum', 'hopper']

graph_manager = BasicRLGraphManager(agent_params=agent_params, env_params=env_params,
                                    schedule_params=schedule_params, vis_params=vis_params,
                                    preset_validation_params=preset_validation_params)


