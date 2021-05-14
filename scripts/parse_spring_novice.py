import os
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
from nltk import word_tokenize

from centaur.models import Question, QantaCache, Record
from centaur.db.session import SessionLocal
from centaur.utils import shell, remove_power


def parse_questions_for_inspection():
    data_dir = 'data/spring-novice-htmls'
    for round in range(1, 11):
        round_name = f'0{round}' if round < 10 else str(round)
        input_filename = f'{data_dir}/{round_name}.f.html'
        question_texts, answers = [], []
        with open(input_filename) as f:
            soup = BeautifulSoup(f, 'html.parser')
            for p in soup.find_all('p'):
                if p:
                    if 'class' in p.attrs:
                        if 'tu' in p['class']:  # toss-up
                            question_texts.append(p.get_text())
                        elif 'answer' in p['class']:
                            answers.append(p.get_text())

        output_question_filename = f'{data_dir}/{round_name}_question.txt'
        with open(output_question_filename, 'w') as f:
            for text in question_texts:
                f.write(text)
                f.write('\n')

        output_answer_filename = f'{data_dir}/{round_name}_answer.txt'
        with open(output_answer_filename, 'w') as f:
            for answer in answers:
                f.write(answer)
                f.write('\n')


def load_question_to_db():
    data_dir = 'data/spring-novice-htmls-cleaned'
    if not os.path.exists(data_dir):
        s3_dir = 's3://pinafore-us-west-2/public/spring-novice-htmls-cleaned.zip'
        shell(f'aws s3 cp {s3_dir} {data_dir}.zip')
        shell(f'unzip {data_dir}.zip -d data/')

    db = SessionLocal()

    for round in range(1, 11):
        round_name = f'0{round}' if round < 10 else str(round)
        with open(f'{data_dir}/{round_name}_question.txt') as f:
            question_texts = f.readlines()
        with open(f'{data_dir}/{round_name}_answer.txt') as f:
            answers = f.readlines()

        assert len(question_texts) == 24
        assert len(answers) == 24

        for i, (text, answers) in enumerate(zip(question_texts, answers)):
            text = remove_power(text)
            raw_text = text.split()
            tokens = word_tokenize(text)

            answers = answers.strip().split(',')
            answer = answers[0].title()
            alternative_answers = [] if len(answers) == 1 else [x.title() for x in answers[1:]]
            new_question = Question(
                id=f'spring_novice_round_{round_name}_question_{i + 1}',
                answer=answer,
                raw_text=raw_text,  # it's actually question.split()
                length=len(tokens),
                tokens=tokens,
                tournament=f'spring_novice_round_{round_name}',
                meta={'alternative_answers': alternative_answers}
            )
            try:
                db.add(new_question)
            except IntegrityError:
                pass

        db.commit()
        db.close()


if __name__ == '__main__':
    # parse_questions_for_inspection()

    db = SessionLocal()
    db.query(QantaCache).delete()
    db.commit()

    db.query(Record).delete()
    db.commit()

    questions = db.query(Question).filter(Question.tournament.startswith('spring_novice'))
    for q in questions:
        db.delete(q)
    db.commit()

    load_question_to_db()

    questions = db.query(Question).filter(Question.tournament.startswith('spring_novice'))
    print(questions.count())
