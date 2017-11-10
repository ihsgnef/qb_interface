// Empty JS for your own code to be here
var sockt = new WebSocket("ws://127.0.0.1:9000");

var question_area = document.getElementById('question_area');
var answer_area = document.getElementById('answer_area');
var score_area = document.getElementById('score_area');
var guesses_area = document.getElementById('guesses_area');
var evidence_tabs = document.getElementById("tabs");

var answer_button = document.getElementById("answer_button");
var buzz_button = document.getElementById("buzz_button");
var show_hide_button = document.getElementById("show_hide_button");

var question_text = "";
var is_buzzing = false;
var position = 0;
var qid = 0;
var score = 0;

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
show_hide_button.onclick = function () { show_hide(); };

sockt.onopen = function () {
    question_area.innerHTML = "Hello";
};

function new_question(msg) {
    qid = msg.qid;
    position = 0;
    question_text = "";
    question_area.innerHTML = question_text;
    answer_area.value = "";
    buzz_button.disabled = false;
    answer_button.disabled = true;
    is_buzzing = false;
    var m = {type: MSG_TYPE_NEW, qid: msg.qid};
    sockt.send(JSON.stringify(m));
}

function update_question(msg) {
    question_text += " " + msg.text;
    question_area.innerHTML = question_text;
    var m = {type: MSG_TYPE_RESUME, qid: msg.qid, position: position};
    if (is_buzzing === false) {
        sockt.send(JSON.stringify(m));
    } else {
        m.type = MSG_TYPE_BUZZING_REQUEST;
        sockt.send(JSON.stringify(m));
        is_buzzing = false;
    }
}

function buzzing() {
    is_buzzing = true;
    buzz_button.disabled = true;
}

function send_answer() {
    var answer = answer_area.value;
    var m = {type: MSG_TYPE_BUZZING_ANSWER, qid: qid, position: position, text: answer};
    sockt.send(JSON.stringify(m));
    answer_button.disabled = true;
    answer_area.value = "";
}

function handle_result_mine(msg) {
    answer_button.disabled = true;
    if (typeof msg.evidence !== 'undefined') {
        question_text += "<br /><br />Your answer: " + msg.evidence.guess;
        if (msg.text === false) {
            question_text  = question_text + " (Wrong)<br /><br />";
        } else {
            question_text  = question_text + " (Correct)<br /><br />";
        }
        question_area.innerHTML = question_text;
    }

    if (msg.text === false) {
        score -= 5;
    } else {
        score += 10;
    }
    score_area.innerHTML = 'Your score:' + score;
}

function handle_result_others(msg) {
    answer_button.disabled = true;
    if (typeof msg.evidence !== 'undefined') {
        question_text += "<br /><br />Player" + msg.evidence.uid;
        question_text += " answer: " + msg.evidence.guess;
        if (msg.text === false) {
            question_text += " (Wrong)<br /><br />";
        } else {
            question_text += " (Correct)<br /><br />";
        }
        question_area.innerHTML = question_text;
    }
}

function show_hide() {
    if (evidence_tabs.style.display === "none") {
        evidence_tabs.style.display = "block";
    } else {
        evidence_tabs.style.display = "none";
    }
}

function update_evidence(msg) {
    var evidence = msg.evidence;
    if (typeof evidence === 'undefined') { return; }
    if (typeof evidence.answer !== 'undefined') {
        question_text += "<br /><br />Correct answer: " + evidence.answer;
        question_area.innerHTML = question_text;
    }
    if (typeof evidence.guesses !== 'undefined') {
        var guesses_text = "<br />".concat(evidence.guesses);
        guesses_area.innerHTML = guesses_text;
    }
}

function add_bell() {
    question_text += bell_str;
    question_area.innerHTML = question_text;
}

sockt.onmessage = function (event) {
    var msg = JSON.parse(event.data);
    if (msg.type === MSG_TYPE_NEW) {
        new_question(msg);
    } else if (msg.type === MSG_TYPE_RESUME) {
        update_question(msg);
        update_evidence(msg);
    } else if (msg.type === MSG_TYPE_END) {
        update_evidence(msg);
    } else if (msg.type === MSG_TYPE_BUZZING_GREEN) {
        answer_button.disabled = false;
        add_bell();
    } else if (msg.type === MSG_TYPE_BUZZING_RED) {
        answer_button.disabled = true;
        add_bell();
    } else if (msg.type === MSG_TYPE_RESULT_MINE) {
        handle_result_mine(msg);
    } else if (msg.type === MSG_TYPE_RESULT_OTHER) {
        handle_result_others(msg);
    }
};