var sockt = new WebSocket("ws://34.209.31.242:9000");
// var answer_json_dir = "http://qbinterface.club/answers.json";
var answer_json_dir = "http://localhost/answers.json";

///////// Message types ///////// 
var MSG_TYPE_NEW = 0; // beginning of a new question
var MSG_TYPE_RESUME = 1; // continue
var MSG_TYPE_END = 2; // end of question
var MSG_TYPE_BUZZING_REQUEST = 3; // user: I'd like to buzz
var MSG_TYPE_BUZZING_ANSWER = 4; // user providing an answer
var MSG_TYPE_BUZZING_GREEN = 5; // tell user you win the buzz and can answer now
var MSG_TYPE_BUZZING_RED = 6; // tell user you cannot buzz now
var MSG_TYPE_RESULT_MINE = 7; // result of my answer
var MSG_TYPE_RESULT_OTHER = 8; // result of someone else's answer


///////// HTML Elements ///////// 
var question_area      = document.getElementById('question_area');
var answer_area        = document.getElementById('answer_area');
var score_area         = document.getElementById('score_area');
var evidence_tabs      = document.getElementById("evidence_tabs");
var guesses_table      = document.getElementById("guesses_table");
var answer_button      = document.getElementById("answer_button");
var buzz_button        = document.getElementById("buzz_button");
var guesses_checkbox   = document.getElementById("guesses_checkbox");
var highlight_checkbox = document.getElementById("highlight_checkbox");
var evidence_checkbox  = document.getElementById("evidence_checkbox");
var voice_checkbox     = document.getElementById("voice_checkbox");
var answer_group       = document.getElementById("answer_area_button");


///////// State variables ///////// 
var question_text       = "";
var question_text_color = "";
var info_text           = "";
var is_buzzing          = false;
var position            = 0;
var qid                 = 0;
var score               = 0;
var timer_set           = false;
var timer_timeout;
var bell_str = ' <span class="inline-icon"><i class="glyphicon glyphicon-bell"></i></span> ';


///////// Keyboard operations  ///////// 
// Use space bar for buzzing & avoid scrolling
window.onkeydown = function(e) {
    if (e.keyCode == 32 && e.target == document.body) {
        buzz_button.click();
        e.preventDefault();
    }
}

buzz_button.onclick = function() {
    is_buzzing = true;
    buzz_button.disabled = true;
};
answer_button.onclick = function() { send_answer(); };
// show hide guesses panel
guesses_checkbox.onclick = function() {
    if (guesses_checkbox.checked) {
        evidence_tabs.style.display = "block";
    } else {
        evidence_tabs.style.display = "none";
    }
};
// use enter to submit answer
answer_area.onkeydown = function(event) {
    if (event.keyCode === 13) {
        if (is_buzzing) { answer_button.click(); }
    }
};


///////// Autocomplete ///////// 
var fuzzyhound = new FuzzySearch();

fuzzyhound.setOptions({
    score_test_fused: true
});

$('#answer_area').typeahead({
    minLength: 2,
    highlight: false //let FuzzySearch handle highlight
}, {
    name: 'answers',
    source: fuzzyhound,
    templates: {
        suggestion: function(result) {
            return "<div>" + fuzzyhound.highlight(result) + "</div>"
        }
    }
});

$.ajaxSetup({
    cache: true
});

function setsource(url, keys, output) {
    $.getJSON(url).then(function(response) {
        fuzzyhound.setOptions({
            source: response,
            keys: keys,
            output_map: output
        })
    });
}

setsource(answer_json_dir);


///////// Speech synthesis ///////// 
var voice_msg = new SpeechSynthesisUtterance();
var voices = window.speechSynthesis.getVoices();
voice_msg.voice = voices[10]; // Note: some voices don't support altering params
voice_msg.voiceURI = 'native';
voice_msg.volume = 1; // 0 to 1
voice_msg.rate = 1.5; // 0.1 to 10
voice_msg.pitch = 1; //0 to 2
voice_msg.text = 'Hello World';
voice_msg.lang = 'en-US';


function update_question_display(text, append = true, bg_color = "#f4f4f4") {
    var colored_text = '<span style="background-color: ' + bg_color + '">' + text + '</span>';
    if (append) {
        question_text += text;
        question_text_color += colored_text;
    } else {
        question_text = text;
        question_text_color = colored_text;
    }
    if (highlight_checkbox.checked) {
        question_area.innerHTML = question_text_color + '<br />' + info_text;
    } else {
        question_area.innerHTML = question_text + '<br />' + info_text;
    }
}

function update_info_display(text, append = true) {
    if (append) {
        info_text += text;
    } else {
        info_text = text;
    }
    if (highlight_checkbox.checked) {
        question_area.innerHTML = question_text_color + '<br />' + info_text;
    } else {
        question_area.innerHTML = question_text + '<br />' + info_text;
    }
}

function new_question(msg) {
    qid = msg.qid;
    position = 0;
    update_question_display("", false);
    update_info_display("", false);
    buzz_button.disabled = false;
    answer_button.disabled = true;
    buzz_button.style.display = "initial";
    answer_group.style.display = "none";

    is_buzzing = false;
    timer_set = false;
    var m = {
        type: MSG_TYPE_NEW,
        qid: msg.qid
    };
    sockt.send(JSON.stringify(m));
}

function update_question(msg) {
    update_interpretation(msg);
    position += 1;
    var m = {
        type: MSG_TYPE_RESUME,
        qid: msg.qid,
        position: position
    };
    if (is_buzzing === false) {
        sockt.send(JSON.stringify(m));
    } else {
        m.type = MSG_TYPE_BUZZING_REQUEST;
        sockt.send(JSON.stringify(m));
    }
}


function send_answer() {
    if (answer_button.disabled) {
        return;
    }
    var answer = answer_area.value;
    var m = {
        type: MSG_TYPE_BUZZING_ANSWER,
        qid: qid,
        position: position,
        text: answer
    };
    sockt.send(JSON.stringify(m));
    answer_button.disabled = true;
    answer_area.value = "";
    answer_group.style.display = "none";
    is_buzzing = false;
}

function handle_result(msg) {
    clearTimeout(timer_timeout);
    var text = msg.guess + ' ';
    if (msg.result === true) {
        text += '<span class="label label-success">Correct</span><br />';
    } else {
        text += '<span class="label label-warning">Wrong</span><br />';
    }
    update_info_display(text);

    if (msg.type === MSG_TYPE_RESULT_MINE) {
        score += msg.score;
        score_area.innerHTML = 'Your score: ' + score;
    }
}

function add_history() {
    if (question_text == '' && info_text == '') { return; }
    var iDiv = document.createElement('div');
    iDiv.className = 'well';
    iDiv.innerHTML = question_text + '<br />' + info_text;
    var history_div = document.getElementById('history');
    history_div.insertBefore(iDiv, history_div.childNodes[0]);
}


function set_guess(guess) {
    answer_area.value = guess;
    answer_area.focus();
}

function update_interpretation(msg) {
    // update text and colored text
    var color = "#f4f4f4";
    if (typeof msg.evidence != 'undefined' 
        && typeof msg.evidence.highlight != 'undefined') {
        color = msg.evidence.highlight;
    }
    if (typeof msg.text != 'undefined') {
        update_question_display(" " + msg.text, true, color);
    }

    // speech synthesis
    if (voice_checkbox.checked) {
        voice_msg.text = msg.text;
        speechSynthesis.speak(voice_msg);
    }

    if (typeof msg.evidence == 'undefined') { return; }
    var evidence = msg.evidence;

    // show correct answer
    if (typeof evidence.answer !== 'undefined') {
        var text = "<br />Correct answer: " + evidence.answer;
        update_info_display(text);
    }

    // update the list of guesses
    if (typeof evidence.guesses !== 'undefined') {
        var guesses = evidence.guesses;
        for (var i = 0; i < Math.min(5, guesses.length); i++) {
            var guess = guesses[i][0];
            var button_text = '<a id="guesses_' + i + '"';
            var guess_score = guesses[i][1].toFixed(4);
            button_text += 'onclick=set_guess("' + guess + '")';
            button_text += '>' + guess.substr(0, 20) + '</a>';
            guesses_table.rows[i + 1].cells[1].innerHTML = button_text;
            guesses_table.rows[i + 1].cells[2].innerHTML = guess_score;
        }
    }
}

function progress(timeleft, timetotal, is_red) {
    var percentage = timeleft / timetotal * 100;
    $('.progress-bar').css('width', percentage + '%');
    if (is_red == true) {
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
    document.getElementById("bar").innerHTML = Math.floor(timeleft / 60) + ":" + Math.floor(timeleft % 60);
    if (timeleft > 0) {
        timer_timeout = setTimeout(function() {
            progress(timeleft - 1, timetotal, is_red);
        }, 1000);
    }
}

function handle_buzzing(msg) {
    var user_text = "";
    if (msg.type === MSG_TYPE_BUZZING_GREEN) {
        console.log(answer_area.value);
        answer_group.style.display = "initial";
        answer_area.focus();
        answer_area.value = "";
        answer_button.disabled = false;
        user_text = "Your";
    } else {
        user_text = "Player " + msg.uid;
    }

    buzz_button.disabled = true;
    buzz_button.style.display = "none";
    clearTimeout(timer_timeout);
    progress(7, 7, true);
    update_question_display(bell_str);
    var text = '</br><span class="label label-danger">Buzz</span> <span> ' 
        + user_text + ' answer: </span>';
    update_info_display(text);
}

sockt.onmessage = function(event) {
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
    } else if (msg.type === MSG_TYPE_END) {
        update_question(msg);
    } else if (msg.type === MSG_TYPE_BUZZING_GREEN) {
        handle_buzzing(msg);
    } else if (msg.type === MSG_TYPE_BUZZING_RED) {
        handle_buzzing(msg);
    } else if (msg.type === MSG_TYPE_RESULT_MINE) {
        handle_result(msg);
    } else if (msg.type === MSG_TYPE_RESULT_OTHER) {
        handle_result(msg);
    }
};
