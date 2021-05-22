import json
from nltk import word_tokenize

from centaur.models import Question, QantaCache
from centaur.db.session import SessionLocal
from centaur.utils import remove_power


def load_question_to_db():
    with open('data/old/pace_questions.json') as f:
        questions = json.load(f)[:1]
    question = questions[0]
    print(question)

    db = SessionLocal()

    qid = str(question['qid'])
    text = ' '.join(question['raw_text'])
    text = remove_power(text)
    raw_text = text.split()
    tokens = word_tokenize(text)

    new_question = Question(
        id=f'pace_question_{qid}',
        answer=question['answer'],
        raw_text=raw_text,  # it's actually question.split()
        length=len(tokens),
        tokens=tokens,
        tournament='pace',
    )

    db.add(new_question)
    db.commit()

    with open('data/old/pace_cache_one.json') as f:
        cache = json.load(f)
    cache_entries = cache[qid]
    for i, x in cache_entries.items():
        print(x['position'])
        entry = QantaCache(
            question_id=f'pace_question_{qid}',
            position=int(i),
            answer=x['answer'],
            guesses=x['guesses'],
            buzz_scores=x['buzz_scores'],
            matches=x['matches'],
            text_highlight=x['text_highlight'],
            matches_highlight=x['matches_highlight'],
        )
        db.add(entry)
        db.commit()
    db.close()


if __name__ == '__main__':
    db = SessionLocal()
    entries = db.query(QantaCache).filter(QantaCache.question_id.startswith('pace'))
    for x in entries:
        db.delete(x)
    db.commit()
    db.close()

    db = SessionLocal()
    questions = db.query(Question).filter(Question.id.startswith('pace'))
    for x in questions:
        db.delete(x)
    db.commit()
    db.close()

    load_question_to_db()
