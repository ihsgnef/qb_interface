// Empty JS for your own code to be here
var sockt = new WebSocket("ws://34.209.31.242:9000");

var question_area = document.getElementById('question_area');
var answer_area = document.getElementById('answer_area');
var score_area = document.getElementById('score_area');
var evidence_tabs = document.getElementById("evidence_tabs");
var guesses_table = document.getElementById("guesses_table");

var answer_button = document.getElementById("answer_button");
var buzz_button = document.getElementById("buzz_button");
var guesses_checkbox = document.getElementById("guesses_checkbox");
var highlight_checkbox = document.getElementById("highlight_checkbox");
var evidence_checkbox = document.getElementById("evidence_checkbox");
var voice_checkbox = document.getElementById("voice_checkbox");

var question_text = "";
var question_text_highlight = "";
var info_text = "";
var is_buzzing = false;
var position = 0;
var qid = 0;
var score = 0;
var timer_set = false;
var timer_timeout;

var MSG_TYPE_NEW = 0; // beginning of a new question
var MSG_TYPE_RESUME = 1; // continue
var MSG_TYPE_END = 2; // end of question
var MSG_TYPE_BUZZING_REQUEST = 3; // user: I'd like to buzz
var MSG_TYPE_BUZZING_ANSWER = 4; // user providing an answer
var MSG_TYPE_BUZZING_GREEN = 5; // tell user you win the buzz and can answer now
var MSG_TYPE_BUZZING_RED = 6; // tell user you cannot buzz now
var MSG_TYPE_RESULT_MINE = 7; // result of my answer
var MSG_TYPE_RESULT_OTHER = 8; // result of someone else's answer

var bell_str = ' <span class="inline-icon"><i class="glyphicon glyphicon-bell"></i></span> ';

buzz_button.onclick = function () { buzzing(); };
answer_button.onclick = function () { send_answer(); };
guesses_checkbox.onclick = function () { toggle_guesses(); };
answer_area.onkeydown = function(event) {
    if (event.keyCode === 13) {
        if (is_buzzing) {
            answer_button.click();
        }
    }
};

sockt.onopen = function () {
    question_area.innerHTML = "Hello";
};

$(document).ready(function(){
  $("#answer_area").fuzzyComplete(all_answers);
});

var voice_msg = new SpeechSynthesisUtterance();
var voices = window.speechSynthesis.getVoices();
voice_msg.voice = voices[10]; // Note: some voices don't support altering params
voice_msg.voiceURI = 'native';
voice_msg.volume = 1; // 0 to 1
voice_msg.rate = 1.5; // 0.1 to 10
voice_msg.pitch = 1; //0 to 2
voice_msg.text = 'Hello World';
voice_msg.lang = 'en-US';

function update_question_display(text, append=true, bg_color="#f4f4f4") {
    var colored_text = '<span style="background-color: ' + bg_color + '">' + text + '</span>';
    if (append) {
        question_text += text;
        question_text_highlight += colored_text;
    } else {
        question_text = text;
        question_text_highlight = colored_text;
    }
    if (highlight_checkbox.checked) {
        question_area.innerHTML = question_text_highlight + '<br />' + info_text;
    }
    else {
        question_area.innerHTML = question_text + '<br />' + info_text;
    }
}

function update_info_display(text, append=true) {
    if (append) {
        info_text += text;
    }
    else {
        info_text = text;
    }
    if (highlight_checkbox.checked) {
        question_area.innerHTML = question_text_highlight + '<br />' + info_text;
    }
    else {
        question_area.innerHTML = question_text + '<br />' + info_text;
    }
}

function new_question(msg) {
    qid = msg.qid;
    position = 0;
    update_question_display("", false);
    update_info_display("", false);
    answer_area.value = "";
    buzz_button.disabled = false;
    answer_button.disabled = true;
    is_buzzing = false;
    timer_set = false;
    var m = {type: MSG_TYPE_NEW, qid: msg.qid};
    sockt.send(JSON.stringify(m));
}

function update_question(msg) {
    if (typeof msg.evidence != 'undefined' && typeof msg.evidence.highlight != 'undefined') {
        var hilight = msg.evidence.highlight;
        update_question_display(" " + msg.text, true, hilight);
        if (voice_checkbox.checked) {
            voice_msg.text = msg.text;
            // speechSynthesis.speak(voice_msg);
        }
    } else {
        update_question_display(" " + msg.text);
        if (voice_checkbox.checked) {
            voice_msg.text = msg.text;
            // speechSynthesis.speak(voice_msg);
        }
    }
    var m = {type: MSG_TYPE_RESUME, qid: msg.qid, position: position};
    if (is_buzzing === false) {
        sockt.send(JSON.stringify(m));
    } else {
        m.type = MSG_TYPE_BUZZING_REQUEST;
        sockt.send(JSON.stringify(m));
    }
}

function buzzing() {
    is_buzzing = true;
    buzz_button.disabled = true;
    answer_area.focus();
}

function send_answer() {
    if (answer_button.disabled) {
        return;
    }
    var answer = answer_area.value;
    var m = {type: MSG_TYPE_BUZZING_ANSWER, qid: qid, position: position, text: answer};
    sockt.send(JSON.stringify(m));
    answer_button.disabled = true;
    answer_area.value = "";
    is_buzzing = false;
}

function handle_result_mine(msg) {
    is_buzzing = false;
    answer_button.disabled = true;
    var text = msg.guess + ' ';
    if (msg.result === true) {
        text += '<span class="label label-success">Correct</span><br />';
    } else {
        text += '<span class="label label-warning">Wrong</span>';
    }
    update_info_display(text);
    score += msg.score;
    score_area.innerHTML = 'Your score: ' + score;
}

function handle_result_others(msg) {
    is_buzzing = false;
    answer_button.disabled = true;
    var text = msg.guess + ' ';
    if (msg.result === true) {
        text += '<span class="label label-success">Correct</span><br />';
    } else {
        text += '<span class="label label-warning">Wrong</span>';
    }
    update_info_display(text);
}

function add_history() {
    var iDiv = document.createElement('div');
    iDiv.className = 'well';
    iDiv.innerHTML = question_text + '<br />' + info_text;
    var history_div = document.getElementById('history');
    history_div.insertBefore(iDiv, history_div.childNodes[0]);
}

function toggle_guesses() {
    if (guesses_checkbox.checked) {
        evidence_tabs.style.display = "block";
    } else {
        evidence_tabs.style.display = "none";
    }
}

function set_guess(guess) {
    answer_area.value = guess;
    answer_area.focus();
}

function update_interpretation(msg) {
    var evidence = msg.evidence;
    if (typeof evidence === 'undefined') { return; }
    if (typeof evidence.answer !== 'undefined') {
        var text = "<br />Correct answer: " + evidence.answer;
        update_info_display(text);
    }
    if (typeof evidence.guesses !== 'undefined') {
        var guesses = evidence.guesses;
        for (var i = 0; i < Math.min(5, guesses.length); i++) {
            var guess = guesses[i][0]
            var guess_text = guess.substr(0, 20)
            var button_text = '<a id="guesses_' + i + '"';
            button_text += 'onclick=set_guess("' + guess + '")';
            button_text += '>' + guess_text + '</a>';
            guesses_table.rows[i+1].cells[1].innerHTML = button_text
            guesses_table.rows[i+1].cells[2].innerHTML = guesses[i][1].toFixed(4);
        }
    }
}

function add_bell() {
    update_question_display(bell_str);
}

function progress(timeleft, timetotal, buzzing) {
    var percentage = timeleft / timetotal * 100;
    $('.progress-bar').css('width', percentage+'%');
    if (buzzing == true) {
        $('.progress-bar').css({
            'background-image': 'none',
            'background-color': '#d9534f'
        });
    } else {
        $('.progress-bar').css({
            'background-image': 'none',
            'background-color': '#428bca'
        });
    }
    document.getElementById("bar").innerHTML = Math.floor(timeleft/60) + ":" + Math.floor(timeleft%60);
    if(timeleft > 0) {
        timer_timeout = setTimeout(function() {
            progress(timeleft - 1, timetotal, buzzing);
        }, 1000);
    }
}

function handle_buzzing_red(msg) {
    clearTimeout(timer_timeout);
    answer_button.disabled = true;
    buzz_button.disabled = true;
    progress(msg.length, msg.length, true);
    add_bell();
    var text = '</br><span class="label label-danger">Buzz</span> <span> Player ' + msg.uid + ' answer: </span>'
    update_info_display(text);
}

function handle_buzzing_green(msg) {
    clearTimeout(timer_timeout);
    answer_button.disabled = false;
    progress(msg.length, msg.length, true);
    add_bell();
    var text = '</br><span class="label label-danger">Buzz</span> <span> Your answer: </span>'
    update_info_display(text);
}

sockt.onmessage = function (event) {
    var msg = JSON.parse(event.data);
    if (msg.type === MSG_TYPE_NEW) {
        add_history();  
        new_question(msg);
    } else if (msg.type === MSG_TYPE_RESUME) {
        if (timer_set === false) {
            var timetotal = msg.length / 2;
            var timeleft = (msg.length - msg.position) / 2;
            progress(timeleft, timetotal, false);
            timer_set = true;
        }
        update_question(msg);
        update_interpretation(msg);
    } else if (msg.type === MSG_TYPE_END) {
        if (typeof msg.text != 'undefined') {
            update_question(msg);
        }
        update_interpretation(msg);
    } else if (msg.type === MSG_TYPE_BUZZING_GREEN) {
        handle_buzzing_green(msg);
    } else if (msg.type === MSG_TYPE_BUZZING_RED) {
        handle_buzzing_red(msg);
    } else if (msg.type === MSG_TYPE_RESULT_MINE) {
        clearTimeout(timer_timeout);
        handle_result_mine(msg);
    } else if (msg.type === MSG_TYPE_RESULT_OTHER) {
        clearTimeout(timer_timeout);
        handle_result_others(msg);
    }
};