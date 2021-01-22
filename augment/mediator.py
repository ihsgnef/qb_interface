import random
import numpy as np
from augment.bandit import BanditModel
from augment.utils import EXPLANATIONS


class Mediator:

    def get_explanation_config(self, player) -> int:
        pass

    def update(self, player, reward: float) -> None:
        pass

    def config_id_to_config(self, config_id: int):
        config = {}
        for x in EXPLANATIONS:
            config[x] = (config_id % 2) != 0
            config_id = config_id // 2
        return config

    def config_to_config_id(self, config: dict):
        config_id = 0
        multiplier = 1
        for x in EXPLANATIONS:
            config_id += multiplier * config[x]
            multiplier *= 2
        return config_id


class RandomMediator(Mediator):

    def get_explanation_config(self, player) -> int:
        n_configs = 2 ** len(EXPLANATIONS)
        return self.config_id_to_config(random.choice(range(n_configs)))


class DirichletMediator(Mediator):

    def __init__(self, n_questions):
        n_configs = 2 ** len(EXPLANATIONS)
        self.expected_each = n_questions / n_configs

    def get_explanation_config(self, player) -> int:
        params = [max(self.expected_each - player.combo_count[x], 0) for x in EXPLANATIONS]
        return self.config_id_to_config(np.argmax(np.random.dirichlet(params)).item())


class BanditMediator(Mediator):

    def __init__(self, nchoices: int, streaming: bool = False):
        self.bandit_model = BanditModel(nchoices, streaming)

    def get_explanation_config(self, player) -> int:
        features = player.featurize()
        return self.config_id_to_config(self.bandit_model.predict(features)[0].item())

    def get_features(self, player):
        return []

    def update(self, player, reward: float):
        action = self.config_to_config_id(player.explanation_config)
        features = self.get_features(player)
        self.bandit_model.fit(
            features,
            np.array([[action]]),
            np.array([[reward]]),
        )
