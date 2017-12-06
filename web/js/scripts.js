var sockt;
var socket_addr = "ws://127.0.0.1:9000";
// var socket_addr = "ws://34.209.31.242:9000";
var answer_json_dir = "http://localhost/answers.json";
// var answer_json_dir = "http://qbinterface.club/answers.json";


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
var accept_button      = document.getElementById("accept_button");
var question_area      = document.getElementById("question_area");
var answer_area        = document.getElementById("answer_area");
// var score_area         = document.getElementById('score_area');
var guesses_card       = document.getElementById("guesses_card");
var guesses_table      = document.getElementById("guesses_table");
var players_table      = document.getElementById("players_table");
var matches_card       = document.getElementById("matches_card");
var matches_table      = document.getElementById("matches_table");
var guess_matches_area = document.getElementById("guess_of_matches");
var buzz_button        = document.getElementById("buzz_button");
var guesses_checkbox   = document.getElementById("guesses_checkbox");
var highlight_checkbox = document.getElementById("highlight_checkbox");
var matches_checkbox   = document.getElementById("matches_checkbox");
var voice_checkbox     = document.getElementById("voice_checkbox");
var machine_buzz_checkbox = document.getElementById("machine_buzz_checkbox");
var answer_group       = document.getElementById("answer_area_row");
var history_div        = document.getElementById('history');


///////// State variables ///////// 
var curr_answer         = "";
var question_text       = "";
var question_text_color = "";
var info_text           = "";
var is_buzzing          = false;
var buzzed              = false;
var position            = 0;
var qid                 = 0;
var score               = 0;
var history_number      = 0;
var timer_set           = false;
var timer_timeout;
var bell_str = ' <span class="fa fa-bell" aria-hidden="true"></span> ';


///////// Cookies ///////// 
function setCookie(cname, cvalue, exdays=1) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

function getCookie(cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

var player_name = getCookie("player_name");
var player_uid = getCookie("player_uid");
var consent_accepted = getCookie("consent_accepted");
if (consent_accepted == "") {
    ///////// Consent Form ///////// 
    $('#exampleModalLong').modal('show');
    accept_button.onclick = function(event) {
        $('#exampleModalLong').modal('hide');
        setCookie("consent_accepted", "True");
    };
} else {
    start();
}

///////// Keyboard operations  ///////// 
// Use space bar for buzzing & avoid scrolling
window.onkeydown = function(e) {
    if (e.keyCode == 32 && e.target == document.body) {
        buzz_button.click();
        is_buzzing = true;
        e.preventDefault();
    }
};
// use enter to submit answer
answer_area.onkeydown = function(event) {
    if (event.keyCode === 13) {
        if (is_buzzing) { send_answer(); }
    }
};
buzz_button.onclick = function() {
    is_buzzing = true;
    buzz_button.disabled = true;
};
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
// show hide guesses panel
highlight_checkbox.onclick = function() {
    update_question_display()
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

function new_question(msg) {
    qid = msg.qid;
    position = 0;
    curr_answer = ""
    question_text = '';
    question_text_color = '';
    info_text = '';
    update_question_display();
    guess_matches_area.innerHTML = '';
    buzz_button.disabled = false;
    answer_group.style.display = "none";

    for (var i = 0; i < 5; i++) {
        guesses_table.rows[i + 1].cells[1].innerHTML = '-';
        guesses_table.rows[i + 1].cells[2].innerHTML = '-';
    }

    for (var i = 0; i < 4; i++) {
        matches_table.rows[i].cells[0].innerHTML = '-';
    }

    is_buzzing = false;
    buzzed = false;
    timer_set = false;
    var m = {
        type: MSG_TYPE_NEW,
        qid: msg.qid,
        player_name: player_name,
        player_uid: player_uid,
        disable_machine_buzz: (machine_buzz_checkbox.checked === false)
    };
    sockt.send(JSON.stringify(m));
}

function update_question(msg) {
    if (typeof msg.buzzed != 'undefined') {
        buzz_button.disabled = msg.buzzed;
    } else if (buzzed === false) { 
        buzz_button.disabled = false;
    }
    
    update_interpretation(msg);
    position = msg.position;
    var m = {
        qid: msg.qid,
        position: position,
    };
    if (is_buzzing === false) {
        m.type = MSG_TYPE_RESUME,
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
    if (is_buzzing == false) {
        return;
    }
    
    var answer = answer_area.value;
    if (answer == "" && curr_answer != "") {
        answer = curr_answer;
    }
    var m = {
        type: MSG_TYPE_BUZZING_ANSWER,
        qid: qid,
        position: position,
        text: answer,
        helps: get_helps()
    };
    sockt.send(JSON.stringify(m));
    answer_group.style.display = "none";
    is_buzzing = false;
    clearTimeout(timer_timeout);
    timer_set = false;
}

function handle_result(msg) {
    clearTimeout(timer_timeout);
    timer_set = false;
    // var text = msg.guess + ' ';
    // if (msg.result === true) {
    //     text += '<span class="badge badge-success">Correct</span><br />';
    // } else {
    //     text += '<span class="badge badge-warning">Wrong</span><br />';
    // }
    // info_text += text;
    update_question_display();
    answer_area.value = "";
    answer_group.style.display = "none";

    if (msg.type === MSG_TYPE_RESULT_MINE) {
        score += msg.score;
        // score_area.innerHTML = 'Your score: ' + score;
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
    if (highlight_checkbox.checked) {
        content += question_text_color + '<br />' + info_text + '</div></div>';
    } else {
        content += question_text + '<br />' + info_text + '</div></div>';
    }

    history_div.innerHTML = header + content + history_div.innerHTML;
}


function set_guess(guess) {
    answer_area.value = guess;
    curr_answer = guess;
    answer_area.focus();
}

function update_interpretation(msg) {
    // update text and colored text
    if (typeof msg.text_highlighted != 'undefined') {
        question_text_color = msg.text_highlighted;
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

    // update the list of guesses
    if (typeof msg.guesses !== 'undefined') {
        var guesses = msg.guesses;
        for (var i = 0; i < Math.min(5, guesses.length); i++) {
            var guess = guesses[i][0];
            var guess_score = guesses[i][1].toFixed(4);
            // var button_text = '<a id="guesses_' + i + '"';
            // button_text += 'onclick=set_guess("' + guess + '")';
            // button_text += '>' + guess.substr(0, 20) + '</a>';
            var button_text = guess.substr(0, 20);
            guesses_table.rows[i + 1].cells[1].innerHTML = button_text;
            guesses_table.rows[i + 1].cells[2].innerHTML = guess_score;

            var createClickHandler = function(guess) {
                return function() { 
                    answer_area.value = guess;
                    curr_answer = guess;
                    answer_area.focus();
                };
            };

            guesses_table.rows[i + 1].onclick = createClickHandler(guess);
        }
        if (guesses.length > 0) {
            curr_answer = guesses[0][0];
            guess_matches_area.innerHTML = guesses[0][0];
        } else {
            guess_matches_area.innerHTML = '-';
        }
    }

    //update the matches
    if (typeof msg.matches !== 'undefined') {
        for (var i = 0; i < Math.min(4, msg.matches.length); i++) {
            matches_table.rows[i].cells[0].innerHTML = msg.matches[i];
        }
    }
}

function end_of_question(msg) {
    var real_answer = 'Question';
    if (typeof msg.answer !== 'undefined') {
        // info_text += "<br />Correct answer: " + msg.answer;
        // update_question_display();
        real_answer = msg.answer;
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
    if (msg.type === MSG_TYPE_BUZZING_GREEN) {
        answer_group.style.display = "initial";
        answer_area.focus();
        $('#answer_area').typeahead('val', curr_answer);
        answer_area.value = "";
        is_buzzing = true;
        buzzed = true;
    }
    buzz_button.disabled = true;
    clearTimeout(timer_timeout);
    progress(7, 7, true);
    question_text += bell_str;
    question_text_color += bell_str;
    update_question_display();
}


function start() {
    sockt = new WebSocket(socket_addr);
    sockt.onmessage = function(event) {
        var msg = JSON.parse(event.data);
        if (typeof msg.player_name != 'undefined') {
            if (player_name == "") {
                player_name = msg.player_name;
                console.log(player_name);
                setCookie("player_name", player_name);
            }
        }
        if (typeof msg.player_uid != 'undefined') {
            if (player_uid == "") {
                player_uid = msg.player_uid;
                console.log(player_uid);
                setCookie("player_uid", player_uid);
            }
        }
        if (typeof msg.player_list !== 'undefined') {
            var player_list = msg.player_list;
            for (var i = 0; i < 5; i++) {
                if (i >= player_list.length) {
                    players_table.rows[i + 1].cells[1].innerHTML = '-';
                    players_table.rows[i + 1].cells[2].innerHTML = '-';
                    players_table.rows[i + 1].className = "";
                    continue;
                }
                var name = player_list[i][0];
                if (name == player_name) {
                    players_table.rows[i + 1].className = "table-info";
                } else {
                    players_table.rows[i + 1].className = "";
                }
                players_table.rows[i + 1].cells[1].innerHTML = name;
                players_table.rows[i + 1].cells[2].innerHTML = player_list[i][1];
            }
        }
        if (typeof msg.info_text != 'undefined') {
            info_text = msg.info_text;
            update_question_display();
        }
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
}

$("#exampleModalLong").on("hidden.bs.modal", function () {
    var chosen_name = $("#choose_user_name").val();
    if (chosen_name != "") {
        console.log("use chosen name", chosen_name);
        player_name = chosen_name;
    }
    start();
});
