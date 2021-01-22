import numpy as np
from augment.bandit import BanditModel
from augment.utils import VIZ_COMBOS


class Mediator:

    def get_enabled_combo(self, player) -> int:
        pass

    def update(self, player, action: int, reward: float) -> None:
        pass


class BanditMediator(Mediator):

    def __init__(self, nchoices: int, streaming: bool = False):
        self.bandit_model = BanditModel(nchoices, streaming)

    def get_enabled_combo(self, player) -> int:
        features = player.featurize()
        return self.bandit_model.predict(features)[0].item()

    def update(self, player, action: int, reward: float):
        features = player.featurize()
        self.bandit_model.fit(
            features,
            np.array([[action]]),
            np.array([[reward]]),
        )


class RandomMediator(Mediator):

    def __init__(self, n_questions):
        self.expected_each = n_questions / len(VIZ_COMBOS)

    def get_enabled_combo(self, player) -> int:
        params = [max(self.expected_each - player.combo_count[x], 0) for x in VIZ_COMBOS]
        return np.argmax(np.random.dirichlet(params)).tolist()
