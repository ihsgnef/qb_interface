import json
from qanta.util.constants import GUESSER_DEV_FOLD
from qanta.datasets.quiz_bowl import QuizBowlDataset

dataset = QuizBowlDataset(guesser_train=True, qb_question_db='data/naqt.db')
questions = dataset.questions_by_fold([GUESSER_DEV_FOLD])[GUESSER_DEV_FOLD]

def convert(q):
    return {'qid': q.qnum, 'text': ' '.join(q.text.values()), 'answer': q.page}

questions = [convert(q) for q in questions]
with open('data/sample_questions.json', 'w') as f:
    f.write(json.dumps(questions))
