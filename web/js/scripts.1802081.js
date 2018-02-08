var sockt;
// var socket_addr = "ws://127.0.0.1:9000";
var socket_addr = "ws://34.209.31.242:9000";
// var answer_json_dir = "http://localhost/answers.json";
var answer_json_dir = "http://qbinterface.club/answers.json";
$("#consent_form").load("consent_form.html"); 


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
var username_area      = document.getElementById("choose_user_name");
var question_area      = document.getElementById("question_area");
var answer_area        = document.getElementById("answer_area");
// var score_area         = document.getElementById('score_area');
var guesses_card       = document.getElementById("guesses_card");
var guesses_table      = document.getElementById("guesses_table");
var players_table      = document.getElementById("players_table");
var players_tbody      = document.getElementById("players_tbody");
var players_n_active   = document.getElementById("n_active");
var matches_card       = document.getElementById("matches_card");
var matches_table      = document.getElementById("matches_table");
var guess_matches_area = document.getElementById("guess_of_matches");
var buzz_button        = document.getElementById("buzz_button");
var guesses_checkbox   = document.getElementById("guesses_checkbox");
var highlight_checkbox = document.getElementById("highlight_checkbox");
var matches_checkbox   = document.getElementById("matches_checkbox");
var voice_checkbox     = document.getElementById("voice_checkbox");
var answer_group       = document.getElementById("answer_area_row");
var history_div        = document.getElementById('history');
var logout_button      = document.getElementById("logout_button");


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

logout_button.onclick = function(event) {
    deleteAllCookies();
    window.location.reload(false);
    console.log(getCookie("player_name"));
    console.log(getCookie("player_uid"));
};


//////// Starting process ////////

var player_name = getCookie("player_name");
var player_uid = getCookie("player_uid");
var consent_accepted = getCookie("consent_accepted");

introJs.fn.oncomplete(function() {console.log('complete'); start();});
introJs.fn.onexit(function() {console.log('complete'); start();});

// var consent_accepted = "";
if (consent_accepted == "N_O_T_S_E_T") {
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
        setCookie("player_uid", "N_O_T_S_E_T");
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
window.addEventListener('beforeunload', function(){
    window.speechSynthesis.cancel();});

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
    answer_area.value = "";
    buzzing_on_guess = false;
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
    clearTimeout(timer_timeout);
    timer_set = false;
    var m = {
        type: MSG_TYPE_NEW,
        qid: msg.qid,
        player_name: player_name,
        player_uid: player_uid,
    };
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
        // enabled_tools: get_enabled_tools()
    };
    if (is_buzzing === false) {
        m.type = MSG_TYPE_RESUME,
        sockt.send(JSON.stringify(m));
    } else {
        m.type = MSG_TYPE_BUZZING_REQUEST;
        sockt.send(JSON.stringify(m));
    }
}

function get_enabled_tools() {
    return {
        guesses: guesses_checkbox.checked,
        highlight: highlight_checkbox.checked,
        matches: matches_checkbox.checked
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
        text: answer,
        // enabled_tools: get_enabled_tools()
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
            guesses_table.rows[i + 1].cells[1].innerHTML = guess_text;
            guesses_table.rows[i + 1].cells[2].innerHTML = guess_score;

            var createClickHandler = function(guess) {
                return function() { 
                    buzzing_on_guess = true;
                    answer_area.value = guess;
                    curr_answer = guess;
                    if (is_buzzing == false && buzz_button.disabled == false) {
                        buzz_button.click();
                    }
                };
            };

            // guesses_table.rows[i + 1].onclick = createClickHandler(guess);
        }
        if (guesses.length > 0) {
            if (is_buzzing == false) {
                curr_answer = guesses[0][0];
            }
            guess_matches_area.innerHTML = guesses[0][0];
        } else {
            guess_matches_area.innerHTML = '-';
        }
    }

    //update the matches
    if (typeof msg.matches !== 'undefined') {
        var matches = msg.matches;
        if (highlight_checkbox.checked) {
            matches = msg.matches_highlighted;
        }
        for (var i = 0; i < Math.min(4, matches.length); i++) {
            matches_table.rows[i].cells[0].innerHTML = matches[i];
        }
    }
}

function end_of_question(msg) {
    // 
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
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
    }

    if (msg.type === MSG_TYPE_BUZZING_GREEN) {
        answer_group.style.display = "initial";
        if (guesses_checkbox.checked) {
            $('#answer_area').typeahead('val', curr_answer);
        }
        if (buzzing_on_guess == false) {
            answer_area.value = "";
        }
        answer_area.focus();
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
            if (player_name == "N_O_T_S_E_T") {
                player_name = msg.player_name;
                console.log('set player name', player_name);
                setCookie("player_name", player_name);
            }
        }
        if (typeof msg.player_uid != 'undefined') {
            if (player_uid == "N_O_T_S_E_T") {
                player_uid = msg.player_uid;
                console.log('set player uid', player_uid);
                setCookie("player_uid", player_uid);
            }
        }
        if (typeof msg.length != 'undefined') {
            if (timer_set === false) {
                var timetotal = msg.length / 2;
                var timeleft = (msg.length - msg.position) / 2;
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
                td.appendChild(document.createTextNode(ply.name));
                tr.appendChild(td);

                var stat = ply.questions_correct.length + '/'
                           + ply.questions_answered.length + '/'
                           + ply.questions_seen.length;

                var td = document.createElement('td');
                td.appendChild(document.createTextNode(stat));
                tr.appendChild(td);

                new_tbody.appendChild(tr);

                if (ply.uid == player_uid) {
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
        if (typeof msg.enabled_tools != 'undefined') {
            var tools = msg.enabled_tools;
            if (tools.guesses) {
                guesses_card.style.display = "block";
                guesses_checkbox.checked = true;
            } else {
                guesses_card.style.display = "none";
                guesses_checkbox.checked = false;
            }
            if (tools.matches) {
                matches_card.style.display = "block";
                matches_checkbox.checked = true;
            } else {
                matches_card.style.display = "none";
                matches_checkbox.checked = false;
            }
            highlight_checkbox = tools.highlight;

        }
        if (msg.type === MSG_TYPE_NEW) {
            new_question(msg);
        } else if (msg.type === MSG_TYPE_RESUME) {
            update_question(msg);
        } else if (msg.type === MSG_TYPE_END) {
            update_interpretation(msg);
            clearTimeout(timer_timeout);
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

// $("#consent_modal").on("hidden.bs.modal", function () {
//     var chosen_name = $("#choose_user_name").val();
//     if (chosen_name != "") {
//         console.log("use chosen name", chosen_name);
//         player_name = chosen_name;
//         setCookie("player_name", player_name);
//     }
//     start();
// });
