import numpy as np 
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

def get_reward(action_id, uid = None, qid = None):
    mean = 0.1 * (action_id + 1)
    reward = np.random.normal(mean, 0.1)
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
times = 100
seq_error = np.zeros(shape=(times, 1))
for t in range(times):
    if t == 20:
        bandit_solver.save_model()
        bandit_solver.load_model()
    print('===================== ', t, ' =====================')
    action_id = bandit_solver.get_action()
    reward = get_reward(action_id)
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