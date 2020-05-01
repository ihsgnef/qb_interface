import os
import pickle
import numpy as np

class ExpectedWins:

    def __init__(self):
        ckp_dir = 'data/curve_pipeline.pkl'
        if os.path.isfile(ckp_dir):
            with open(ckp_dir, 'rb') as f:
                self.pipeline = pickle.load(f)
        else:
            raise ValueError('curve_pipeline.pkl does not exist')

    def score(self, buzzing_position, question_length):
        rel_position = buzzing_position / question_length
        return self.pipeline.predict(np.asarray([[rel_position]]))[0]


if __name__ == '__main__':
    ew = ExpectedWins()
    print(ew.score(20, 100))
