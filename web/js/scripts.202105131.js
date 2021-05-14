var sockt;
var socket_addr = "ws://localhost:9000";
// var socket_addr = "ws://play.qanta.org:9000";
var answer_json_dir = "http://localhost:8000/answers.0515.json";
// var answer_json_dir = "http://play.qanta.org/answers.0212.json";
// $("#consent_form").load("consent_form.html"); 


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
var MSG_TYPE_COMPLETE = 9; // answered all questions
var MSG_TYPE_NEW_ROUND = 10; // start_new_round


///////// CONFIGS ///////// 
var SECOND_PER_WORD = 0.3;


///////// HTML Elements ///////// 
var accept_button      = document.getElementById("accept_button");
var username_area      = document.getElementById("choose_user_name");
var question_area      = document.getElementById("question_area");
var question_title     = document.getElementById("question_title");
var answer_area        = document.getElementById("answer_area");
var alternatives_card  = document.getElementById("alternatives_card");
var alternatives_table = document.getElementById("alternatives_table");
var players_table      = document.getElementById("players_table");
var players_tbody      = document.getElementById("players_tbody");
var players_n_active   = document.getElementById("n_active");
var evidence_card      = document.getElementById("evidence_card");
var evidence_table     = document.getElementById("evidence_table");
var prediction_area    = document.getElementById("prediction_area");
var prediction_area_autopilot    = document.getElementById("prediction_area_autopilot");
var voice_checkbox     = document.getElementById("voice_checkbox");
var answer_group       = document.getElementById("answer_area_row");
var history_div        = document.getElementById('history');
var buzz_button        = document.getElementById("buzz_button");
// var logout_button      = document.getElementById("logout_button");
var pause_button       = document.getElementById("pause_button");
var resume_button      = document.getElementById("resume_button");
var evidence_checkbox  = document.getElementById("evidence_checkbox");
var autopilot_checkbox = document.getElementById("autopilot_checkbox");
var prediction_card    = document.getElementById("prediction_card");
var prediction_card_autopilot  = document.getElementById("prediction_card_autopilot");
var alternatives_checkbox       = document.getElementById("alternatives_checkbox");
var highlight_question_checkbox = document.getElementById("highlight_question_checkbox");
var highlight_evidence_checkbox = document.getElementById("highlight_evidence_checkbox");


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
var timer_set           = false;
var timer_timeout;
var buzzing_on_guess    = false; // buzzing by clicking on guess or not
var bell_str = ' <span class="fa fa-bell" aria-hidden="true"></span> ';
var speech_text = '';
var speech_starting_position = 0;
var PAUSE_COUNTDOWN = 5;
var pause_countdown = PAUSE_COUNTDOWN;
var task_completed = false;
var start_new_round = false;  // when this is true, send a start new round signal to server on register


///////// Constants ///////// 
var HISTORY_LENGTH = 30;
var highlight_color = '#ecff6d';
var highlight_prefix = '<span style="background-color: ' + highlight_color + '">';
var highlight_suffix = '</span>';


///////// Cookies ///////// 
function setCookie(cname, cvalue, exdays=10) {
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
    return "N_O_T_S_E_T";
}

function deleteAllCookies() {
    var cookies = document.cookie.split(";");

    for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i];
        var eqPos = cookie.indexOf("=");
        var name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT";
    }
}

// logout_button.onclick = function(event) {
//     deleteAllCookies();
//     window.location.reload(false);
//     console.log(getCookie("player_name"));
//     console.log(getCookie("player_id"));
// };

pause_button.onclick = function(event) {
    $('#pause_modal').modal('show');
    if (task_completed) {
        $('#pause_modal_content').text('Round finished. Please wait for the next round to begin.');
    }
    clearTimeout(timer_timeout);
    timer_set = false;
    // sockt.onclose = function() {};
    // sockt.onmessage = function() {};
    // sockt.close();
};

resume_button.onclick = function(event) {
    clearTimeout(timer_timeout);
    timer_set = false;
    start_new_round = true;
    start();
};

//////// Starting process ////////

var player_name = getCookie("player_name");
var player_id = getCookie("player_id");
var consent_accepted = getCookie("consent_accepted");

introJs.fn.oncomplete(function() {start();});
introJs.fn.onexit(function() {start();});

// var consent_accepted = "";
if (consent_accepted == "N_O_T_S_E_T") {
// if (true) {
    ///////// Consent Form ///////// 
    $('#consent_modal').modal('show');
    accept_button.onclick = function(event) {
        var uname = username_area.value;
        if (uname.length > 0) {
            setCookie("player_name", uname);
            player_name = uname;
        } else {
            setCookie("player_name", "N_O_T_S_E_T");
        }
        setCookie("player_id", "N_O_T_S_E_T");
        setCookie("consent_accepted", "True");
        $('#consent_modal').modal('hide');
        introJs().start();
    };
} else {
    start();
}

///////// Keyboard operations  ///////// 

window.onkeydown = function(e) {
    if (e.keyCode == 32 && e.target != answer_area) {
        // Use space bar for buzzing & avoid scrolling
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


///////// Button operations  ///////// 
buzz_button.onclick = function() {
    is_buzzing = true;
    buzz_button.disabled = true;
    pause_countdown = PAUSE_COUNTDOWN;
};
// show hide alternatives panel
alternatives_checkbox.onclick = function() {
    if (alternatives_checkbox.checked) {
        alternatives_card.style.display = "block";
    } else {
        alternatives_card.style.display = "none";
    }
};
// show hide autopilot panel
autopilot_checkbox.onclick = function() {
    if (autopilot_checkbox.checked) {
        prediction_card_autopilot.style.display = "block";
        prediction_card.style.display = "none";
    } else {
        prediction_card_autopilot.style.display = "none";
        prediction_card.style.display = "block";
    }
};
// show hide evidence panel
evidence_checkbox.onclick = function() {
    if (evidence_checkbox.checked) {
        evidence_card.style.display = "block";
    } else {
        evidence_card.style.display = "none";
    }
};
// stop speech synthesis
voice_checkbox.onclick = function() {
    if (!voice_checkbox.checked && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    } else {
        var st = speech_text.split(' ');
        st = st.slice(position - speech_starting_position - 1, st.length);
        st = st.join(' ');
        window.speechSynthesis.cancel();
        var utter = new SpeechSynthesisUtterance(st);
        utter.rate = 0.78;
        window.speechSynthesis.speak(utter);
    }
};
// show hide question highlights
highlight_question_checkbox.onclick = function() {
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
window.addEventListener('beforeunload', function(){
    window.speechSynthesis.cancel();});

function update_question_display() {
    if (highlight_question_checkbox.checked) {
        question_area.innerHTML = question_text_color + '<br />' + info_text;
    } else {
        question_area.innerHTML = question_text + '<br />' + info_text;
    }

    if (autopilot_checkbox.checked) {
        prediction_card_autopilot.style.display = "block";
        prediction_card.style.display = "none";
    } else {
        prediction_card_autopilot.style.display = "none";
        prediction_card.style.display = "block";
    }
}

function new_question(msg) {
    qid = msg.qid;
    position = 0;
    curr_answer = ""
    question_text = '';
    question_text_color = '';
    info_text = '';
    answer_area.value = "";
    buzzing_on_guess = false;
    question_title.innerHTML = qid;
    update_question_display();
    prediction_area.innerHTML = '';
    buzz_button.disabled = false;
    answer_group.style.display = "none";

    for (var i = 0; i < 5; i++) {
        alternatives_table.rows[i + 1].cells[1].innerHTML = '-';
        alternatives_table.rows[i + 1].cells[2].innerHTML = '-';
    }

    for (var i = 0; i < 4; i++) {
        evidence_table.rows[i].cells[0].innerHTML = '-';
    }

    is_buzzing = false;
    buzzed = false;
    clearTimeout(timer_timeout);
    timer_set = false;

    if (typeof msg.task_completed != 'undefined') {
        task_completed = msg.task_completed;
        console.log('setting completed to ' + task_completed);
        if (task_completed) {
            pause_button.click();
            if (player_name == 'ihsgnef') {
                console.log('showing resume button to admin');
                resume_button.style.display = "block";
            }
        }
    }

    console.log('new question ' + msg.qid);

    if (start_new_round == true) {
        var m = {
            type: MSG_TYPE_NEW,
            qid: msg.qid,
            player_name: player_name,
            player_id: player_id,
            start_new_round: true,
        };
        start_new_round = false;
    } else {
        var m = {
            type: MSG_TYPE_NEW,
            qid: msg.qid,
            player_name: player_name,
            player_id: player_id,
        };
    }

    sockt.send(JSON.stringify(m));
}


function update_question(msg) {
    if (window.speechSynthesis.paused && voice_checkbox.checked) {
        window.speechSynthesis.resume();
    }

    if (typeof msg.can_buzz != 'undefined') {
        buzz_button.disabled = !msg.can_buzz;
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
        sockt.send(JSON.stringify(m));
    }
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
        text: answer
    };
    sockt.send(JSON.stringify(m));
    answer_group.style.display = "none";
    is_buzzing = false;
    buzzing_on_guess = false;
    clearTimeout(timer_timeout);
    timer_set = false;
}

function handle_result(msg) {
    update_question_display();
    answer_area.value = "";
    buzzing_on_guess = false;
    answer_group.style.display = "none";
    clearTimeout(timer_timeout);
    timer_set = false;
}

function toggle_history_visability(history_id) {
    var hist_div = document.getElementById('history_' + history_id);
    if (hist_div.style.display == 'none') {
        hist_div.style.display = 'block';
    } else {
        hist_div.style.display = 'none';
    }
}

function update_history_entries(history_entries) {
    var elem_id = '';
    var head_id = '';
    var header = '';
    history_div.innerHTML = '';
    var ll = history_entries.length;
    for (var i = Math.max(0, ll - HISTORY_LENGTH); i < ll; i++) {
        elem_id = 'history_' + i;
        head_id = 'heading_' + elem_id;
        header = '<div class="card-header" role="tab" id="' + head_id + '">';
        header += '<a data-toggle="collapse" href="#' + elem_id + '" aria-expanded="false" aria-controls="' + elem_id + '">';
        header += history_entries[i].header + '</a></div>';
        var content = '<div id="' + elem_id + '" class="collapse" role="tabpanel" aria-labelledby="' + head_id + '">';
        content += '<div class="card-body mx-2 my-2">';
        content += history_entries[i].question_text + '<br />';
        content += history_entries[i].info_text + '</div>';
        content += '<table class="table"> <tbody>';
        var guesses = history_entries[i].guesses;
        for (var j = 0; j < Math.min(5, guesses.length); j++) {
            var guess_score = guesses[j][1].toFixed(4);
            var guess_text = guesses[j][0].substr(0, 20);
            content += '<tr><td>' + (j+1).toString() +'</td>';
            content += '<td>' + guess_text + '</td>';
            content += '<td>' + guess_score + '</td></tr>';
        }
        content += '</tbody></table>';
        content += '<table class="table"><tbody>';
        var matches = history_entries[i].matches;
        for (var j = 0; j < Math.min(4, matches.length); j++) {
            content += '<tr><td>' + matches[j] +'</td></tr>';
        }
        content += '</tbody></table>';
        content += '</div>';
        history_div.innerHTML = header + content + history_div.innerHTML;
    }
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

    // update the list of guesses
    if (typeof msg.guesses !== 'undefined') {
        var guesses = msg.guesses;
        var score_sum = 0;
        for (var i = 0; i < guesses.length; i++) {
            score_sum += guesses[i][1];
        }
        for (var i = 0; i < Math.min(5, guesses.length); i++) {
            var guess = guesses[i][0];
            var guess_score = (guesses[i][1]/score_sum).toFixed(4);
            var guess_text = guess.substr(0, 20);
            alternatives_table.rows[i + 1].cells[1].innerHTML = guess_text;
            alternatives_table.rows[i + 1].cells[2].innerHTML = guess_score;

            var createClickHandler = function(guess) {
                return function() { 
                    buzzing_on_guess = true;
                    answer_area.value = guess;
                    curr_answer = guess;
                    if (is_buzzing == false && buzz_button.disabled == false) {
                        answer_area.focus();
                        buzz_button.click();
                        answer_area.focus();
                    }
                };
            };
            alternatives_table.rows[i + 1].onclick = createClickHandler(guess);
        }

        if (guesses.length > 0 && is_buzzing == false) {
            // to make sure the auto-complete is pre-filled by machine prediction
            curr_answer = guesses[0][0];
        }

        if (guesses.length > 0) {
            prediction_area_autopilot.innerHTML = guesses[0][0]
            confidence_area_autopilot.innerHTML = guesses[0][1]
            prediction_area.innerHTML = guesses[0][0]
            confidence_area.innerHTML = guesses[0][1]
            if (msg.autopilot_prediction == true) {
                prediction_area_autopilot.innerHTML = '<span style="color:red;">' + guesses[0][0] + '</span>';
            } else {
                prediction_area_autopilot.innerHTML = '<span style="color:gray;">' + guesses[0][0] + '</span>';
            }
        }
    }

    //update the evidence 
    if (typeof msg.matches !== 'undefined') {
        var matches = msg.matches;
        if (highlight_evidence_checkbox.checked) {
            matches = msg.matches_highlighted;
        }
        for (var i = 0; i < Math.min(4, matches.length); i++) {
            evidence_table.rows[i].cells[0].innerHTML = matches[i];
        }
    }
}

function end_of_question(msg) {
    if (buzzed == false) {
        pause_countdown -= 1;
    }
    if (pause_countdown == 0) {
        // pause_button.click();
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
    // document.getElementById("bar").innerHTML = Math.floor(timeleft / 60) + ":" + Math.floor(timeleft % 60);
    document.getElementById("bar").innerHTML = Math.floor(timeleft);
    if (timeleft > 0) {
        timer_timeout = setTimeout(function() {
            progress(timeleft - 1, timetotal, is_red);
        }, 1000);
    }
}

function handle_buzzing(msg) {
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
    }

    if (msg.type === MSG_TYPE_BUZZING_GREEN) {
        answer_group.style.display = "initial";
        $('#answer_area').typeahead('val', curr_answer);
        // if (alternatives_checkbox.checked) {
        //     $('#answer_area').typeahead('val', curr_answer);
        // }
        if (buzzing_on_guess == false) {
            answer_area.value = "";
        }
        answer_area.focus();
        is_buzzing = true;
        buzzed = true;
    }
    clearTimeout(timer_timeout);
    progress(7, 7, true);
    timer_set = true;
    buzz_button.disabled = true;
    question_text += bell_str;
    question_text_color += bell_str;
    update_question_display();
}


function start() {
    pause_countdown = PAUSE_COUNTDOWN;
    sockt = new WebSocket(socket_addr);
    sockt.onmessage = function(event) {
        var msg = JSON.parse(event.data);
        if (typeof msg.player_name != 'undefined') {
            if (player_name == "N_O_T_S_E_T") {
                player_name = msg.player_name;
                console.log('set player name', player_name);
                setCookie("player_name", player_name);
            }
        }
        if (typeof msg.player_id != 'undefined') {
            if (player_id == "N_O_T_S_E_T") {
                player_id = msg.player_id;
                console.log('set player id', player_id);
                setCookie("player_id", player_id);
            }
        }
        if (msg.type === MSG_TYPE_NEW) {
            new_question(msg);
            timer_set = false;
        } else if (msg.type === MSG_TYPE_RESUME) {
            update_question(msg);
        } else if (msg.type === MSG_TYPE_END) {
            update_interpretation(msg);
            clearTimeout(timer_timeout);
            timer_set = false;
            end_of_question(msg);
        } else if (msg.type === MSG_TYPE_BUZZING_GREEN) {
            handle_buzzing(msg);
        } else if (msg.type === MSG_TYPE_BUZZING_RED) {
            handle_buzzing(msg);
        } else if (msg.type === MSG_TYPE_RESULT_MINE) {
            handle_result(msg);
        } else if (msg.type === MSG_TYPE_RESULT_OTHER) {
            handle_result(msg);
        } else if (msg.type === MSG_TYPE_COMPLETE) {
            // alert("Congrats! You have answered all the questions.");
            task_completed = true;
            pause_button.click();
            if (player_name == 'ihsgnef') {
                console.log('showing resume button to admin');
                resume_button.style.display = "block";
            }
        } else if (msg.type === MSG_TYPE_NEW_ROUND) {
            console.log('******* new round ******');
            resume_button.click();
        }
        if (typeof msg.length != 'undefined') {
            if (timer_set === false) {
                var timetotal = msg.length * SECOND_PER_WORD;
                var timeleft = (msg.length - msg.position) * SECOND_PER_WORD;
                progress(timeleft, timetotal, false);
                timer_set = true;
            }
        }
        if (typeof msg.player_list !== 'undefined') {
            var new_tbody = document.createElement('tbody');
            var player_list = msg.player_list;
            var n_active = 0;
            for (var i = 0; i < player_list.length; i++) {
                var ply = player_list[i];

                var tr = document.createElement('tr');

                var td = document.createElement('td');
                td.appendChild(document.createTextNode(i+1));
                tr.appendChild(td);

                var td = document.createElement('td');
                td.appendChild(document.createTextNode(ply.score));
                tr.appendChild(td);

                var td = document.createElement('td');
                td.appendChild(document.createTextNode(ply.player_name));
                tr.appendChild(td);

                var neg = ply.questions_answered - ply.questions_correct;
                var stat = ply.questions_correct + '/' + neg;

                var td = document.createElement('td');
                td.appendChild(document.createTextNode(stat));
                tr.appendChild(td);

                new_tbody.appendChild(tr);

                if (ply.player_id == player_id) {
                    tr.className = "table-success";
                }
                if (!ply.active) {
                    tr.style.color = "#c1c1c1";
                } else {
                    n_active += 1;
                }
            }
            players_tbody.parentNode.replaceChild(new_tbody, players_tbody);
            players_tbody = new_tbody;
            players_n_active.innerHTML = '<span style="font-weight:bold">' + n_active + '</span>' + " active";
        }
        if (typeof msg.history_entries !== 'undefined') {
            update_history_entries(msg.history_entries);
        }
        if (typeof msg.info_text != 'undefined') {
            info_text = msg.info_text;
            update_question_display();
        }
        if (typeof msg.speech_text != 'undefined') {
            speech_text = msg.speech_text;
            speech_starting_position = msg.position;
            if (voice_checkbox.checked) {
                window.speechSynthesis.cancel();
                var utter = new SpeechSynthesisUtterance(speech_text);
                utter.rate = 0.78;
                window.speechSynthesis.speak(utter);
            }
        }
        if (typeof msg.explanation_config != 'undefined') {
            var cfg = msg.explanation_config;

            if (cfg.allow_player_choice) {
                autopilot_checkbox.disabled = false;
                alternatives_checkbox.disabled = false;
                evidence_checkbox.disabled = false;
                highlight_question_checkbox.disabled = false;
                highlight_evidence_checkbox.disabled = false;
                return
            } else {
                autopilot_checkbox.disabled = true;
                alternatives_checkbox.disabled = true;
                evidence_checkbox.disabled = true;
                highlight_question_checkbox.disabled = true;
                highlight_evidence_checkbox.disabled = true;
            }

            if (cfg.Alternatives) {
                alternatives_card.style.display = "block";
                alternatives_checkbox.checked = true;
            } else {
                alternatives_card.style.display = "none";
                alternatives_checkbox.checked = false;
            }

            if (cfg.Evidence) {
                evidence_card.style.display = "block";
                evidence_checkbox.checked = true;
            } else {
                evidence_card.style.display = "none";
                evidence_checkbox.checked = false;
            }

            highlight_question_checkbox.checked = cfg.Highlights_Question;
            highlight_evidence_checkbox.checked = cfg.Highlights_Evidence;
            autopilot_checkbox.checked = cfg.Autopilot
        }
    };
}

// $("#consent_modal").on("hidden.bs.modal", function () {
//     var chosen_name = $("#choose_user_name").val();
//     if (chosen_name != "") {
//         console.log("use chosen name", chosen_name);
//         player_name = chosen_name;
//         setCookie("player_name", player_name);
//     }
//     start();
// });
