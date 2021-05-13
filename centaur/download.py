import os
import wget
import pathlib

DATA_DIR = 'data/'
S3_DIR = 'https://pinafore-us-west-2.s3-us-west-2.amazonaws.com/augment/data/'

pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

files = [
    # 'guesser',
    'cache.pkl',
    'cache_expo.pkl',
    'db.sqlite',
    'pace_questions.pkl',
    'expo_questions.pkl',
    'kurtis_2019_10_08.answers.txt',
    'kurtis_2019_10_08.questions.txt',
    'kurtis_2019_10_08.pkl',
    'db.sqlite.20181116',
    'db.sqlite.20180517',
    'curve_pipeline.pkl',
]

for f in files:
    if not os.path.exists(DATA_DIR + f):
        print('downloading {} from s3'.format(f))
        wget.download(os.path.join(S3_DIR, f), os.path.join(DATA_DIR + f))
        print()
