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
var guesses_card       = document.getElementById("guesses_card");
var guesses_table      = document.getElementById("guesses_table");
var matches_card       = document.getElementById("matches_card");
var matches_area       = document.getElementById("matches_area");
var answer_button      = document.getElementById("answer_button");
var buzz_button        = document.getElementById("buzz_button");
var guesses_checkbox   = document.getElementById("guesses_checkbox");
var highlight_checkbox = document.getElementById("highlight_checkbox");
var matches_checkbox   = document.getElementById("matches_checkbox");
var voice_checkbox     = document.getElementById("voice_checkbox");
var answer_group       = document.getElementById("answer_area_button");
var history_div = document.getElementById('history');


///////// State variables ///////// 
var question_text       = "";
var question_text_color = "";
var info_text           = "";
var is_buzzing          = false;
var position            = 0;
var qid                 = 0;
var score               = 0;
var history_number      = 0;
var timer_set           = false;
var timer_timeout;
var bell_str = ' <i class="fa fa-bell" aria-hidden="true"></i> ';

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
        guesses_card.style.display = "block";
    } else {
        guesses_card.style.display = "none";
    }
};
// show hide matches panel
matches_checkbox.onclick = function() {
    if (matches_checkbox.checked) {
        matches_card.style.display = "block";
    } else {
        matches_card.style.display = "none";
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

function update_question_display() {
    if (highlight_checkbox.checked) {
        question_area.innerHTML = question_text_color + '<br />' + info_text;
    } else {
        question_area.innerHTML = question_text + '<br />' + info_text;
    }
}

function update_info_display() {
    if (highlight_checkbox.checked) {
        question_area.innerHTML = question_text_color + '<br />' + info_text;
    } else {
        question_area.innerHTML = question_text + '<br />' + info_text;
    }
}

function new_question(msg) {
    qid = msg.qid;
    position = 0;
    question_text = '';
    question_text_color = '';
    update_question_display();
    info_text = '';
    update_info_display();
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
    position = msg.position;
    var m = {
        type: MSG_TYPE_RESUME,
        qid: msg.qid,
        position: position
    };
    if (is_buzzing === false) {
        sockt.send(JSON.stringify(m));
    } else {
        m.type = MSG_TYPE_BUZZING_REQUEST;
        m.helps = get_helps()
        sockt.send(JSON.stringify(m));
    }
}

function get_helps() {
    // get the list of enabled interpretations
    var helps = {
        guesses: guesses_checkbox.checked,
        highlight: highlight_checkbox.checked,
        matches: matches_checkbox.checked,
        voice: voice_checkbox.checked}
    return helps
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
        text: answer,
        helps: get_helps()
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
        text += '<span class="badge badge-success">Correct</span><br />';
    } else {
        text += '<span class="badge badge-warning">Wrong</span><br />';
    }
    info_text += text;
    update_info_display();

    if (msg.type === MSG_TYPE_RESULT_MINE) {
        score += msg.score;
        score_area.innerHTML = 'Your score: ' + score;
    }
}

function toggle_history_visability(history_id) {
    var hist_div = document.getElementById('history_' + history_id);
    if (hist_div.style.display == 'none') {
        hist_div.style.display = 'block';
    } else {
        hist_div.style.display = 'none';
    }
}

function add_history(real_answer) {
    if (question_text == '' && info_text == '') { return; }
    history_number += 1;
    
    var elem_id = 'history_' + history_number;
    var head_id = 'heading_' + elem_id;
    var header = '<div class="card-header" role="tab" id="' + head_id + '">';
    header += '<a data-toggle="collapse" href="#' + elem_id + '" aria-expanded="false" aria-controls="' + elem_id + '">';
    header += real_answer + '</a></div>';

    var content = '<div id="' + elem_id + '" class="collapse" role="tabpanel" aria-labelledby="' + head_id + '">';
    content += '<div class="card-body mx-2 my-2">';
    content += question_text + '<br />' + info_text + '</div></div>';

    history_div.innerHTML = header + content + history_div.innerHTML;
}


function set_guess(guess) {
    answer_area.value = guess;
    answer_area.focus();
}

function update_interpretation(msg) {
    // update text and colored text
    if (typeof msg.evidence != 'undefined' 
        && typeof msg.evidence.highlight != 'undefined') {
        question_text_color = msg.evidence.highlight;
        update_question_display()
    }
    if (typeof msg.text != 'undefined') {
        question_text = msg.text;
        update_question_display();
    }

    // speech synthesis
    if (voice_checkbox.checked) {
        voice_msg.text = msg.text;
        speechSynthesis.speak(voice_msg);
    }

    if (typeof msg.evidence == 'undefined') { return; }
    var evidence = msg.evidence;

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

    //update the matches
    if (typeof evidence.matches !== 'undefined') {
        var qb_matches = evidence.matches.qb, wiki_matches = evidence.matches.wiki;
        matches_area.innerHTML = '<b>QB</b> ' + qb_matches[0];
        matches_area.innerHTML += '</br><b>WIKI</b> ' + wiki_matches[0];
    }
}

function end_of_question(msg) {
    var real_answer = 'Question';
    if (typeof msg.evidence.answer !== 'undefined') {
        info_text += "<br />Correct answer: " + msg.evidence.answer;
        update_info_display();
        real_answer = msg.evidence.answer;
    }
    add_history(real_answer);
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
        answer_area.value = "";
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
    question_text += bell_str;
    question_text_color += bell_str;
    update_question_display();
    var text = '</br><span class="badge badge-danger">Buzz</span> <span> ' 
        + user_text + ' answer: </span>';
    info_text += text;
    update_info_display();
}

sockt.onmessage = function(event) {
    var msg = JSON.parse(event.data);
    if (msg.type === MSG_TYPE_NEW) {
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
        end_of_question(msg);
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
