from tqdm import tqdm
from nltk.corpus import stopwords as sw

from centaur.machine_client import GuesserBuzzer
from centaur.models import Question, QantaCache
from centaur.db.session import SessionLocal

stopwords = set(sw.words('english'))


def generate_cache():
    session = SessionLocal()
    model = GuesserBuzzer()

    questions = session.query(Question).filter(Question.tournament.startswith('spring_novice'))
    for q in tqdm(questions, total=questions.count()):
        model.new_question(q.id)
        for i in range(1, q.length + 1):  # +1 because we take [:i]
            if i % 5 == 1:
                buzz_scores = model.buzz(q.tokens[:i], i)
                guesses = [(x.replace('_', ' '), s) for x, s in model.guesses]
                entry = QantaCache(
                    question_id=q.id,
                    position=i,
                    answer=q.answer,
                    guesses=guesses,
                    buzz_scores=buzz_scores,
                    matches=model.tokenized_matches,
                    text_highlight=model.text_highlight,
                    matches_highlight=model.matches_highlight,
                )
                session.add(entry)
            else:
                entry.text_highlight.append(False)

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


if __name__ == '__main__':
    # test()
    generate_cache()
