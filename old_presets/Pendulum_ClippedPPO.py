from configurations import *
from block_factories.basic_rl_factory import BasicRLFactory


class AgentParams(AgentParameters):
    def __init__(self):
        AgentParameters.__init__(self, ClippedPPO, ExplorationParameters, None)
        pass
        self.learning_rate = 0.00005
        self.num_heatup_steps = 0
        self.algorithm.num_consecutive_training_steps = 1
        self.algorithm.num_consecutive_playing_steps = 2048
        self.algorithm.discount = 0.99
        self.batch_size = 64
        self.algorithm.policy_gradient_rescaler = 'GAE'
        self.algorithm.gae_lambda = 0.95
        pass
        self.algorithm.optimizer_type = 'Adam'
        pass
        self.algorithm.beta_entropy = 0.01


class EnvParams(Mujoco):
    def __init__(self):
        super().__init__()
        self.level = 'Pendulum-v0'
        self.normalize_observation = True


class VisParams(VisualizationParameters):
    def __init__(self):
        super().__init__()
        self.dump_csv = True

factory = BasicRLFactory(agent_params=AgentParams, env_params=EnvParams, vis_params=VisParams)
