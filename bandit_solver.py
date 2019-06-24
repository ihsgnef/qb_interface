import numpy as np
from db import QBDB
from striatum.storage import history
from striatum.storage import model
#from striatum.storage import Action
from striatum.storage import (
    MemoryHistoryStorage,
    MemoryModelStorage,
    MemoryActionStorage,
    Action,
)
from striatum.bandit import ucb1
from striatum.bandit import linucb
from striatum.bandit import linthompsamp
from striatum.bandit import exp4p
from striatum.bandit import exp3

EXPERIMENT_BANDIT = ['LinUCB', 'LinThompSamp', 'UCB1', 'Exp3', 'random']
MODEL_PATH = "bandit_model"

class BANDIT_SOLVER:

    def __init__(self):
        self.bandit = EXPERIMENT_BANDIT[2]
        self.history_id = 0
        user_feature = None
        action_context = None
        # self.bandit_list = EXPERIMENT_BANDIT
        self.actions_id = [i for i in range(8)]
        self.get_data()
        self.policy_generation()

    def get_data(self):
        # streaming_batch = None
        # user_feature = self.uid
        # reward_list = None

        tempactions = []
        for key in self.actions_id:
            action = Action(key)
            tempactions.append(action)
        actions = MemoryActionStorage()
        actions.add(tempactions)
        self.actions = actions

    def policy_generation(self):
        bandit = self.bandit
        actions = self.actions
        historystorage = history.MemoryHistoryStorage()
        modelstorage = model.MemoryModelStorage()

        if bandit == 'Exp4P':
            policy = exp4p.Exp4P(
                historystorage, modelstorage, actions, delta=0.5, p_min=None)

        elif bandit == 'LinUCB':
            #policy = linucb.LinUCB(historystorage, modelstorage, actions, 0.3, 20)
            policy = linucb.LinUCB(history_storage = historystorage, model_storage = modelstorage,action_storage = actions, alpha = 0.3, context_dimension = 18)

        elif bandit == 'LinThompSamp':
            policy = linthompsamp.LinThompSamp(
                historystorage,
                modelstorage,
                actions,
                #d=20, Supposed to be context dimension
                context_dimension=18,
                delta=0.61,
                R=0.01,
                epsilon=0.71)

        elif bandit == 'UCB1':
            policy = ucb1.UCB1(historystorage, modelstorage, actions)

        elif bandit == 'Exp3':
            policy = exp3.Exp3(historystorage, modelstorage, actions, gamma=0.2)

        elif bandit == 'random':
            policy = 0

        self.policy = policy

    def get_action(self, context_vector = None):
        # full_context = {}
        # for action_id in actions_id:
        #     full_context[action_id] = uid
        history_id, action_list = self.policy.get_action(context_vector, 8)
        for action in action_list:
            print("action id: ", action.action.id, "\testimate reward: ", action.estimated_reward)
        if history_id > self.history_id:
            self.history_id = history_id
        return action_list[0].action.id

    def update(self, action_id, reward):
        '''
        Parameters
        ----------
        action_id : 0-7
        reward: float num, eg. 0/1
        '''
        self.policy.reward(self.history_id, {action_id: reward})
        self.history_id += 1

    def save_model(self, model_path = None):
        self.policy.save_policy(model_path or MODEL_PATH)
        print("Save model succefully at: ", model_path or MODEL_PATH)

    def load_model(self, model_path = None):
        self.policy.load_policy(model_path or MODEL_PATH)
        print("Load model succefully from: ", model_path or MODEL_PATH)