from tqdm import tqdm
from nltk.corpus import stopwords as sw

from centaur.machine_client import GuesserBuzzer
from centaur.models import Question, QantaCache
from centaur.db.session import SessionLocal

stopwords = set(sw.words('english'))


def generate_cache():
    session = SessionLocal()
    model = GuesserBuzzer()

    questions = session.query(Question).filter(Question.tournament.startswith('spring_novice_round'))
    for q in tqdm(questions, total=questions.count()):
        model.new_question(q.id)
        guesses, buzz_scores, matches, text_highlight, matches_highlight = None, None, None, None, None
        for i in range(1, q.length + 1):  # +1 because we take [:i]
            if i % 5 == 1:
                guesses = [(x.replace('_', ' '), s) for x, s in model.guesses]
                buzz_scores = model.buzz(q.tokens[:i], i)
                matches = model.tokenized_matches
                text_highlight = model.text_highlight
                matches_highlight = model.matches_highlight
            else:
                text_highlight.append(False)
            entry = QantaCache(
                question_id=q.id,
                position=i,
                answer=q.answer,
                guesses=guesses,
                buzz_scores=buzz_scores,
                matches=matches,
                text_highlight=text_highlight,
                matches_highlight=matches_highlight,
            )
            session.add(entry)
            session.commit()

    session.commit()
    session.close()


def test():
    model = GuesserBuzzer()
    session = SessionLocal()
    q = session.query(Question).filter(Question.tournament.startswith('spring_novice')).first()
    print(q.id)
    print(q.tournament)
    print(q.answer)

    model.new_question(q.id)
    sentence = ' '.join(q.raw_text[:10])
    buzz_scores = model.buzz(sentence, 10)
    print(model.guesses)
    print(model.text_highlight)


def clear_cache():
    db = SessionLocal()
    db.query(QantaCache).delete()
    db.commit()


if __name__ == '__main__':
    # test()
    clear_cache()
    generate_cache()
