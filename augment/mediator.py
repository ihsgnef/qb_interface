import json
import random
import numpy as np
from augment.bandit import BanditModel
from augment.utils import EXPLANATIONS, ID_TO_CONFIG, CONFIG_TO_ID


class Mediator:

    def get_explanation_config(self, player) -> dict:
        pass

    def update(self, player, reward: float) -> None:
        pass


class NoneFixedMediator(Mediator):

    def __init__(self):
        self.config = {x: False for x in EXPLANATIONS}

    def get_explanation_config(self, player) -> dict:
        return self.config


class EverythingFixedMediator(Mediator):

    def __init__(self):
        self.config = {x: True for x in EXPLANATIONS}

    def get_explanation_config(self, player) -> dict:
        return self.config


class RandomFixedMediator(Mediator):

    def __init__(self):
        self.config = random.choice(ID_TO_CONFIG)

    def get_explanation_config(self, player) -> dict:
        return self.config


class RandomDynamicMediator(Mediator):

    def get_explanation_config(self, player) -> int:
        return random.choice(ID_TO_CONFIG)


class DirichletMediator(Mediator):

    def __init__(self, expected_each):
        self.expected_each = expected_each

    def get_explanation_config(self, player) -> int:
        params = [max(self.expected_each - player.combo_count[x], 0) for x in EXPLANATIONS]
        return ID_TO_CONFIG(np.argmax(np.random.dirichlet(params)).item())


class RealBanditMediator(Mediator):

    def __init__(self, streaming: bool = False):
        self.bandit_model = BanditModel(len(ID_TO_CONFIG), streaming)

    def get_explanation_config(self, player) -> int:
        features = player.featurize()
        return ID_TO_CONFIG(self.bandit_model.predict(features)[0].item())

    def get_features(self, player):
        return []

    def update(self, player, reward: float):
        action = CONFIG_TO_ID(json.dumps(player.explanation_config))
        features = self.get_features(player)
        self.bandit_model.fit(
            features,
            np.array([[action]]),
            np.array([[reward]]),
        )


class BanditMediator(Mediator):

    def get_explanation_config(self, player) -> int:
        return random.choice(ID_TO_CONFIG)


class SemiAutopilotMediator(Mediator):

    def __init__(self):
        self.config = {x: False for x in EXPLANATIONS}
        self.config['Autopilot'] = True

    def get_explanation_config(self, player):
        return self.config
