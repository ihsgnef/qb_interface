import json
import itertools

MSG_TYPE_NEW = 0                # beginning of a new question
MSG_TYPE_RESUME = 1             # continue
MSG_TYPE_END = 2                # end of question
MSG_TYPE_BUZZING_REQUEST = 3    # user: I'd like to buzz
MSG_TYPE_BUZZING_ANSWER = 4     # user providing an answer
MSG_TYPE_BUZZING_GREEN = 5      # tell user you win the buzz and can answer now
MSG_TYPE_BUZZING_RED = 6        # tell user you cannot buzz now
MSG_TYPE_RESULT_MINE = 7        # result of my answer
MSG_TYPE_RESULT_OTHER = 8       # result of someone else's answer
MSG_TYPE_COMPLETE = 9           # answered all questions

BADGE_CORRECT = ' <span class="badge badge-success">Correct</span>'
BADGE_WRONG = ' <span class="badge badge-warning">Wrong</span>'
BADGE_BUZZ = '<span class="badge badge-danger">Buzz</span>'
BELL = ' <span class="fa fa-bell" aria-hidden="true"></span> '
NEW_LINE = '</br>'

ANSWER_TIME_OUT = 20
SECOND_PER_WORD = 0.4
PLAYER_RESPONSE_TIME_OUT = 3
HISTORY_LENGTH = 30
THRESHOLD = 0

ALLOW_PLAYER_CHOICE = True
EXPLANATIONS = ['Alternatives', 'Evidence', 'Highlights_Question', 'Highlights_Evidence', 'Autopilot']

ID_TO_CONFIG = []
CONFIG_TO_ID = {}
for config in itertools.product(*[[True, False] for x in EXPLANATIONS]):
    if (not config[1]) and config[3]:
        # evidence=False, highlight_evidence=True
        continue
    if (not config[2]) and config[3]:
        # highlight_question=False, highlight_evidence=True
        continue
    if config[4] and not any(config[:3]):
        # semi-autopilot
        continue
    id = len(ID_TO_CONFIG)
    config = {exp: option for exp, option in zip(EXPLANATIONS, config)}
    ID_TO_CONFIG.append(config)
    CONFIG_TO_ID[json.dumps(config)] = id

highlight_color = '#43c6fc'
highlight_prefix = '<span style="background-color: ' + highlight_color + '">'
highlight_suffix = '</span>'
highlight_template = highlight_prefix + '{}' + highlight_suffix
# highlight_template = '<mark data-entity=\"norp\">{}</mark>'


def boldify(text):
    return '<b>{}</b>'.format(text)
