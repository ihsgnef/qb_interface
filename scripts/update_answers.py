import json
from tqdm import tqdm
from centaur.db.session import SessionLocal
from centaur.models import Question

db = SessionLocal()
tournament_str = 'spring_novice'
questions = db.query(Question).filter(Question.tournament.startswith(tournament_str)).all()

with open('fixtures/elasticsearch_instance_of_answers.json') as f:
    answers = json.load(f)

print(len(answers))
for question in tqdm(questions):
    answer = question.answer.strip().title()
    if answer not in answers:
        answers.append(answer)
    for answer in question.meta.get('alternative_answers', []):
        answer = answer.strip().title()
        if answer not in answers:
            answers.append(answer)
print(len(answers))

with open('web/answers.0515.json', 'w') as f:
    json.dump(answers, f)
