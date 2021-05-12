from augment.db.session import SessionLocal
from tqdm import tqdm
from nltk.corpus import stopwords as sw
from bs4 import BeautifulSoup

from augment.machine_client import GuesserBuzzer
from augment.models import Question, QantaCache
from augment.utils import tokenize_question

stopwords = set(sw.words('english'))


def get_matched(q: Question, position, matches):
    '''
    For a (partial) question and a list of matched documents (with highlights)
    Args:
        q: the Question.
        position (int): so the partial question is `q.tokens[:position]`
        matches: list of matches
    '''
    # take the top 2 mathces from both qb and wiki
    matches = matches['wiki'][:4]
    # matches = matches['qb'][:2] + matches['wiki'][:2]

    # find words highligted in the matches
    highlighted_words = set()  # words highlighted in the matches
    for match in matches:
        soup = BeautifulSoup(match)
        match = [
            x.text.lower() for x in soup.find_all('em')
            if x.text.lower() not in stopwords and len(x.text) > 2
        ]
        highlighted_words.update(match)

    # find the highlighted words in the question
    matched_words = set()  # words matched in the question
    text_highlight = []  # mark highlight or not in the displayed text
    for ts in q.tokens[:position]:
        matched = [t in highlighted_words for t in ts]
        text_highlight.append(any(matched))
        matched_words.update(t for t, m in zip(ts, matched) if m)

    # mark words in the matches
    tokenized_matches = []
    matches_highlight = []
    for m in matches:
        tokenized_matches.append([])
        matches_highlight.append([])
        m = m.replace('<em>', '__').replace('</em>', ' ')
        for word in m.split():
            if not word.startswith('__'):
                tokenized_matches[-1].append(word)
                matches_highlight[-1].append(False)
            else:
                word = word[2:]  # remove __ prefix
                ts = tokenize_question(word)
                matched = [t in matched_words for t in ts]
                matches_highlight[-1].append(any(matched))
                tokenized_matches[-1].append(word)
    return text_highlight, tokenized_matches, matches_highlight


def generate_cache():
    session = SessionLocal()
    model = GuesserBuzzer()

    questions = session.query(Question).filter(Question.tournament.startswith('spring_novice'))
    for q in tqdm(questions, total=questions.count()):
        model.new_question(q.id)
        for i in range(1, q.length + 1):  # +1 because we take [:i]
            if i % 5 == 1:
                sentence = ' '.join(q.raw_text[:i])
                buzz_scores = model.buzz(sentence, i)
                text_highlight, tokenized_matches, matches_highlight = get_matched(q, i, model.matches)
                guesses = [(x.replace('_', ' '), s) for x, s in model.guesses]
                entry = QantaCache(
                    question_id=q.id,
                    position=i,
                    answer=q.answer,
                    guesses=guesses,
                    buzz_scores=buzz_scores,
                    matches=tokenized_matches,
                    text_highlight=text_highlight,
                    matches_highlight=matches_highlight,
                )
                session.add(entry)
            else:
                entry.text_highlight.append(False)

    session.commit()
    session.close()


if __name__ == '__main__':
    model = GuesserBuzzer()
    session = SessionLocal()
    q = session.query(Question).filter(Question.tournament.startswith('spring_novice')).first()
    print(q.id)
    print(q.tournament)
    print(q.answer)
    print(q.raw_text)

    model.new_question(q.id)
    sentence = ' '.join(q.raw_text[:10])
    buzz_scores = model.buzz(sentence, 10)
    print(model.guesses)
