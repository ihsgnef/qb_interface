import numpy as np
from sklearn.linear_model import LogisticRegression
from contextualbandits.online import AdaptiveGreedy


class BanditControl:

    def __init__(self, nchoices: int):
        self.nchoices = nchoices
        base_algorithm = LogisticRegression(solver='lbfgs', warm_start=True)
        # use beta_prior until at least 2 observations of each class
        beta_prior = ((3. / nchoices, 4), 2)
        # UCB gives higher numbers, thus the higher positive prior
        beta_prior_ucb = ((5./nchoices, 4), 2)

        self.model = BootstrappedUCB(base_algorithm, nchoices=nchoices,
                                     beta_prior = beta_prior_ucb, percentile=80,
                                     random_state = 1111)
        self.model = AdaptiveGreedy(base_algorithm,
                                    nchoices=nchoices,
                                    decay_type='threshold',
                                    beta_prior=beta_prior,
                                    random_state=6666)

    def fit(self, x_batch, actions, y_batch, warm_start=False):
        self.model.fit(x_batch, actions, y_batch, warm_start=warm_start)

    def predict(self, x_batch):
        return self.model.predict(x_batch).astype('int')


def parse_bibtex_data(filename):
    import re
    from sklearn.preprocessing import MultiLabelBinarizer
    from sklearn.datasets import load_svmlight_file

    with open(filename, "rb") as f:
        infoline = f.readline()
        infoline = re.sub(r"^b'", "", str(infoline))
        n_features = int(re.sub(r"^\d+\s(\d+)\s\d+.*$", r"\1", infoline))
        features, labels = load_svmlight_file(f, n_features=n_features, multilabel=True)

    mlb = MultiLabelBinarizer()
    labels = mlb.fit_transform(labels)
    features = np.array(features.todense())
    features = np.ascontiguousarray(features)
    return features, labels


if __name__ == '__main__':
    X, y = parse_bibtex_data("Bibtex_data.txt")

    batch_size = 50
    nchoices = y.shape[1]

    model = BanditControl(nchoices=nchoices)

    rewards_average = []
    rewards = np.array([])
    actions = np.array([]).astype('int')
    for batch_start in range(0, X.shape[0], batch_size):
        batch_end = min(X.shape[0], batch_start + batch_size)
        x_batch = X[batch_start: batch_end, :]
        y_batch = y[batch_start: batch_end, :]

        if batch_start == 0:
            batch_actions = np.random.randint(nchoices, size=batch_size)
        else:
            batch_actions = model.predict(x_batch)
        batch_rewards = y[np.arange(batch_start, batch_end), batch_actions]
        actions = np.concatenate((actions, batch_actions))
        rewards = np.concatenate((rewards, batch_rewards))
        rewards_average.append(np.mean(batch_rewards).item())
        model.fit(X[:batch_end], actions, rewards, warm_start=True)
