// Empty JS for your own code to be here
var sockt = new WebSocket("ws://127.0.0.1:9000");
var question_text = ""
var question_area = document.getElementById('question_area');
var answer_area = document.getElementById('answer_area');
var score_area = document.getElementById('score_area');
var answer_button = document.getElementById("answer_button");
var buzz_button = document.getElementById("buzz_button");
var is_buzzing = false;
var position = 0;
var qid = 0;
var score = 0;

buzz_button.onclick = function() { buzzing(); }
answer_button.onclick = function() { send_answer(); }

sockt.onopen = function (event) {
  console.log("websocket open");
  question_area.textContent = "Hello";
};

function new_question (msg) {
  console.log("new question", msg.qid);
  qid = msg.qid;
  position = 0;
  question_text = "";
  question_area.textContent = question_text;
  answer_area.value = "";
  buzz_button.disabled = false;
  answer_button.disabled = true;
  is_buzzing = false;
  var m = {type: 0, qid: msg.qid};
  console.log("Sending ready message");
  sockt.send(JSON.stringify(m));
}

function update_question (msg) {
  question_text = question_text + " " + msg.text
  question_area.textContent = question_text;
  if (is_buzzing === false) { 
    var m = {type: 1, qid: msg.qid, position: position};
    sockt.send(JSON.stringify(m));
  } else {
    var m = {type: 3, qid: msg.qid, position: position};
    sockt.send(JSON.stringify(m));
    is_buzzing = false
  }
}

function buzzing () {
  is_buzzing = true;
  buzz_button.disabled = true;
}

function send_answer () {
  var answer = answer_area.value;
  var m = {type: 4, qid: qid, position: position, text: answer};
  sockt.send(JSON.stringify(m));
  answer_button.disabled = true;
  answer_area.value = "";
}

function handle_result (msg) {
  answer_button.disabled = true;
  if (msg.text === false) {
    score -= 5;
  } else {
    score += 10;
  }
  console.log("score", score)
  score_area.innerHTML = 'Your score:' + score;
}

sockt.onmessage = function (event) {
  var msg = JSON.parse(event.data);
  
  if (msg.type === 0) {
    new_question(msg);
  } else if (msg.type == 1) {
    update_question(msg);
  } else if (msg.type == 4) {
    handle_result(msg);
  } else if (msg.type == 5) {
    answer_button.disabled = false;
  } else if (msg.type == 6) {
    answer_button.disabled = true;
  }
};
