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

EXPLANATIONS = ['Guesses', 'Highlight', 'Evidence', 'Buzzer']
ALLOW_PLAYER_CHOICE = True

highlight_color = '#43c6fc'
highlight_prefix = '<span style="background-color: ' + highlight_color + '">'
highlight_suffix = '</span>'
highlight_template = highlight_prefix + '{}' + highlight_suffix
# highlight_template = '<mark data-entity=\"norp\">{}</mark>'


def boldify(text):
    return '<b>{}</b>'.format(text)
