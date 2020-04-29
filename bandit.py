import dill
import numpy as np
from sklearn.linear_model import LogisticRegression
from contextualbandits.linreg import LinearRegression
from contextualbandits.online import AdaptiveGreedy, BootstrappedUCB, LinUCB


class BanditControl:

    def __init__(self, nchoices, streaming=False):
        self.nchoices = nchoices
        self.streaming = streaming

        if streaming:
            self.model = LinUCB(
                nchoices=nchoices,
                beta_prior=None,
                alpha=0.1,
                ucb_from_empty=False,
                random_state=1111)
            # self.model = AdaptiveGreedy(
            #     LinearRegression(lambda_=10, fit_intercept=True, method="sm"),
            #     nchoices=nchoices,
            #     smoothing=None,
            #     beta_prior=((3 / nchoices, 4.), 2),
            #     active_choice='weighted',
            #     decay_type='percentile',
            #     decay=0.9997,
            #     batch_train=True,
            #     random_state=2222)
        else:
            self.model = BootstrappedUCB(LogisticRegression(solver='lbfgs', warm_start=True),
                                         nchoices=nchoices,
                                         beta_prior=((5. / nchoices, 4), 2),
                                         percentile=80,
                                         random_state=1111)
            # self.model = AdaptiveGreedy(LogisticRegression(solver='lbfgs', warm_start=True),
            #                             nchoices=nchoices,
            #                             decay_type='threshold',
            #                             beta_prior=((3. / nchoices, 4), 2),
            #                             random_state=6666)

    def fit(self, x_batch, actions, y_batch):
        if self.streaming:
            self.model.partial_fit(x_batch, actions, y_batch)
        else:
            self.model.fit(x_batch, actions, y_batch, warm_start=True)

    def predict(self, x_batch):
        return self.model.predict(x_batch).astype('int')

    def save(self, save_dir):
        with open(save_dir, 'wb') as f:
            dill.dump(self.model, f)

    def load(self, save_dir):
        with open(save_dir, 'rb') as f:
            self.model = dill.load(f)


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


def bibtext():
    X, y = parse_bibtex_data("Bibtex_data.txt")

    batch_size = 50
    nchoices = y.shape[1]

    streaming = True
    model = BanditControl(nchoices, streaming=streaming)

    rewards_average = []
    rewards = np.array([])
    actions = np.array([]).astype('int')
    for batch_start in range(0, X.shape[0], batch_size):
        batch_end = min(X.shape[0], batch_start + batch_size)
        x_batch = X[batch_start: batch_end, :]

        if batch_start == 0:
            actions_batch = np.random.randint(nchoices, size=batch_size)
        else:
            actions_batch = model.predict(x_batch)
        rewards_batch = y[np.arange(batch_start, batch_end), actions_batch]
        actions = np.concatenate((actions, actions_batch))
        rewards = np.concatenate((rewards, rewards_batch))
        rewards_average.append(np.mean(rewards_batch).item())

        if streaming:
            model.fit(x_batch, actions_batch, rewards_batch)
        else:
            model.fit(X[:batch_end], actions, rewards)

    import matplotlib.pyplot as plt
    ax = plt.subplot(111)
    ax.plot(np.convolve(rewards_average, np.ones((50,)) / 50, mode='valid'), label="LinUCB (OLS)")
    plt.savefig('a.pdf')


if __name__ == '__main__':
    model = BanditControl(nchoices=8, streaming=True)
    context_vector = np.array([1])[:, np.newaxis]
    actions = model.predict(context_vector)
    print(actions)
    rewards = np.array([0])[:, np.newaxis]
    model.fit(context_vector, actions, rewards)
    actions = model.predict(context_vector)
    print(actions)
