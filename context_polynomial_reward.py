import numpy as np 
import random
import matplotlib.pyplot as plt
from bandit_solver import BANDIT_SOLVER

experiment_bandit = [
        'LinUCB',
        'LinThompSamp', 
        # 'Exp4P', # Takes very long as train expert is LOO Cross Validation
        'UCB1', 
        'Exp3', 
        'random' 
    ]

bandit = 'UCB1'
i = 2

class Simulated_Player():
    def __init__(self):
        self.p1 = np.asarray([random.randint(0, 11) / 10 for i in range(10)])
        self.p2 = np.asarray([random.randint(0, 11) / 10 for i in range(50)])
        self.p3 = np.asarray([random.randint(0, 11) / 10 for i in range(8)])
        print("p1: ", self.p1)
        print("p2: ", self.p2)
        print("p3: ", self.p3)

    def get_context_vector(self, uid, qid):
        uvector = [1 if uid==k else 0 for k in range(10)]
        qvector = [1 if uid==k else 0 for k in range(50)]
        return np.concatenate((uvector, qvector), axis=None)

    def get_reward(self, action_id, uid, qid):
        uvector = np.asarray([1 if uid==k else 0 for k in range(10)])
        qvector = np.asarray([1 if uid==k else 0 for k in range(50)])
        avector = np.asarray([1 if action_id==k else 0 for k in range(8)])
        reward = uvector @ self.p1 + qvector @ self.p2 + avector @ self.p3
        # reward = reward * 2 / 3
        # if reward <= 0.5:
        #     reward = 0
        # else:
        #     reward = 1
        return reward

def regret_calculation(seq_error):
    t = len(seq_error)
    regret = [x / y for x, y in zip(seq_error, range(1, t + 1))]
    return regret

def reward_calculation(seq_reward):
    t = len(seq_reward)
    reward = [x / y for x, y in zip(seq_error, range(1, t + 1))]
    return reward

bandit_solver = BANDIT_SOLVER()
regret = {}
col = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']
times = 1000
seq_error = np.zeros(shape=(times, 1))
players = Simulated_Player()
for t in range(times):
    print('===================== ', t, ' =====================')
    uid = random.randint(0, 10)
    qid = random.randint(0, 50)
    context_vector = players.get_context_vector(uid, qid)
    action_id = bandit_solver.get_action(context_vector)
    reward = players.get_reward(action_id, uid, qid)
    bandit_solver.update(action_id, reward)
    if t == 0:
        seq_error[t] = 1 - reward
    else:
        seq_error[t] = seq_error[t - 1] + (1 - reward)
regret[bandit] = regret_calculation(seq_error)
bandit_solver.policy.plot_avg_reward()
# plt.plot(
#         range(times),
#         regret[bandit],
#         c=col[i],
#         ls='-',
#         label=bandit)
# plt.xlabel('time')
# plt.ylabel('regret')
# plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
# axes = plt.gca()
# axes.set_ylim([0, 1])
# plt.title("Regret Bound with respect to T")
plt.show()