import json
import random
from tqdm import tqdm
from datetime import datetime

from augment.db.session import SessionLocal
from augment.expected_wins import ExpectedWins
from augment.models import Question, Player, Record
from augment.mediator import (
    NoneFixedMediator,
    EverythingFixedMediator,
    RandomFixedMediator,
    RandomDynamicMediator,
    SemiAutopilotMediator,
    BanditMediator,
)

mediator_classes = [
    NoneFixedMediator,
    EverythingFixedMediator,
    RandomFixedMediator,
    RandomDynamicMediator,
    SemiAutopilotMediator,
    BanditMediator,
]

EW = ExpectedWins()


def get_result(player, question):
    # return result and buzzing position
    exp_config = player.mediator.get_explanation_config(player)
    player.explanation_config = exp_config
    return random.choice([0, 1]), question.length // 2


class DummyPlayer:

    def __init__(self, player_id, mediator):
        self.player_id = player_id
        self.score = 0
        self.questions_seen = []
        self.questions_answered = []
        self.questions_correct = []
        self.mediator = mediator
        self.explanation_config = None

    def featurize(self):
        return


def reset_player_records(player_id, session):
    records = session.query(Record).filter(Record.player_id == player_id)
    cnt = records.count()
    records.delete()
    print(f'deleted {cnt} records of {player_id}')


db = SessionLocal()
dummy_players = []
for k in range(70):
    # TODO random assign mediator
    mediator = random.choice(mediator_classes)()
    player = DummyPlayer(player_id=f'dummy_{k}', mediator=mediator)
    dummy_players.append(player)
    player_in_db = db.query(Player).get(player.player_id)
    if player_in_db is not None:
        reset_player_records(player_in_db.id, db)
    else:
        player_in_db = Player(
            id=player.player_id,
            ip_addr=f'dummy ip addr {k}',
            name=f'dummy_{k}',
            mediator_name=player.mediator.__class__.__name__,
            score=0,
            questions_seen=[],
            questions_answered=[],
            questions_correct=[],
        )
        db.add(player_in_db)
    db.commit()

questions = db.query(Question).all()
random.shuffle(questions)
questions = questions[:60]
for player in tqdm(dummy_players):
    random.shuffle(questions)
    for question in questions:
        result, position_buzz = get_result(player, question)
        qb_score = 10 if result > 0 else -5
        ew_score = EW.score(position_buzz, question.length) if result > 0 else 0

        date = datetime.now()
        record_id = json.dumps({
            'question_id': question.id,
            'player_id': player_in_db.id,
            'date': str(date),
        })

        # TODO update player stats

        player_in_db = db.query(Player).get(player.player_id)
        player_in_db.score = player.score
        player_in_db.questions_seen = player.questions_seen
        player_in_db.questions_answered = player.questions_answered
        player_in_db.questions_correct = player.questions_correct

        record = Record(
            id=record_id,
            player_id=player.player_id,
            question_id=question.id,
            position_start=0,
            position_buzz=position_buzz,
            guess=question.answer if result else 'WRONG GUESS',
            result=result,
            qb_score=qb_score,
            ew_score=ew_score,
            explanation_config=json.dumps(player.explanation_config),
            mediator_name=player.mediator.__class__.__name__,
            date=date,
        )
        db.add(record)

db.commit()
