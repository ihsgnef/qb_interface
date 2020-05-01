import os
import wget
import pathlib

DATA_DIR = 'data/'
S3_DIR = 'https://pinafore-us-west-2.s3-us-west-2.amazonaws.com/augment/data/'

pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

files = [
    # 'guesser',
    'cache_expo.pkl',
    'cache.pkl',
    'db.sqlite',
    'expo_questions.pkl',
    'kurtis_2019_10_08.answers.txt',
    'kurtis_2019_10_08.pkl',
    'kurtis_2019_10_08.questions.txt',
    'pace_questions.pkl',
    'policy_2019-11-07_22-05-43.pkl',
    'policy_2019-11-07_22-06-38.pkl',
    'data/cache.pkl',
]

for f in files:
    if not os.path.exists(DATA_DIR + f):
        print('downloading {} from s3'.format(f))
        wget.download(os.path.join(S3_DIR, f), os.path.join(DATA_DIR + f))
        print()
