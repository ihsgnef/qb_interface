CODE_DIR = '/fs/clip-quiz/shifeng/centaur'
DATA_DIR = f'{CODE_DIR}/data'
# SQLALCHEMY_DATABASE_URL = 'postgresql+psycopg2://shifeng@localhost:5433/augment'
SQLALCHEMY_DATABASE_URL = 'postgresql+psycopg2://shifeng@0.tcp.ngrok.io:13974/augment'
USE_MULTIPROCESSING = True
USER_STATS_CACHE = True
MP_CONTEXT = 'fork'
