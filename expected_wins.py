import os
import pickle
import numpy as np

class ExpectedWins:

    def __init__(self):
        ckp_dir = 'data/curve_pipeline.pkl'
        if not os.path.isfile(ckp_dir):
            raise ValueError('curve_pipeline.pkl does not exist')
        
        with open(ckp_dir, 'rb') as f:
            self.pipeline = pickle.load(f)
        linear_regression = self.pipeline.named_steps['linear_regression']
        # coefficients in decreasing powers, to be consistent with poly1d
        self.coef = linear_regression.coef_[::-1].tolist()
        self.intercept = linear_regression.intercept_

    def score_(self, buzzing_position: int, question_length: int) -> float:
        """calculate EW at buzzing position"""
        rel_position = buzzing_position / question_length
        return self.pipeline.predict(np.asarray([[rel_position]]))[0]

    def score(self, buzzing_position: int, question_length: int) -> float:
        """calculate EW at buzzing position"""
        r = buzzing_position / question_length
        x = np.array([r ** 3, r ** 2, r])
        return self.coef @ x + self.intercept

    def solve(self, score: float, question_length: int) -> int:
        """given EW and question length, solve for buzzing position"""
        p = np.poly1d(self.coef + [self.intercept - score])
        # find the root between 0 & 1
        x = np.logical_and(p.r > 0, p.r < 1)
        x = p.r[np.where(x)[0][0]]
        return int(question_length * x)


if __name__ == '__main__':
    ew = ExpectedWins()
    score = ew.score(20, 100)
    print('score', score)
    print('solve', ew.solve(score, 100))
