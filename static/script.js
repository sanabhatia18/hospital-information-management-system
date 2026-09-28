let sessionId = null;
let currentQuestion = "";

const chatBox = document.getElementById("chatBox");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

async function startChat() {

    const response = await fetch("/start");
    const data = await response.json();

    sessionId = data.session_id;
    currentQuestion = data.question;

    addBotMessage(data.question);
}

function addBotMessage(text){

    chatBox.innerHTML += `
    <div class="bot-message">
        <div class="avatar">🤖</div>
        <div class="message">${text}</div>
    </div>
    `;

    scrollToBottom();
}

function addUserMessage(text){

    chatBox.innerHTML += `
    <div class="user-message">
        <div class="message">${text}</div>
    </div>
    `;

    scrollToBottom();
}

function scrollToBottom() {
    const chatBox = document.getElementById("chatBox");
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {

    const answer = userInput.value.trim();

    if(answer === "") return;

    addUserMessage(answer);

    userInput.value = "";

    const response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type":"application/json"
        },
        body: JSON.stringify({
            session_id: sessionId,
            answer: answer
        })
    });

    const data = await response.json();

    if(!data.success){

        addBotMessage(data.message);
        return;
    }

    if(data.completed){

        addBotMessage("Registration completed successfully.");

        document.getElementById("summaryContent").innerHTML =
            "<pre>" +
            JSON.stringify(data.summary, null, 2) +
            "</pre>";

        return;
    }

    addBotMessage(data.question);

    updateSummary(data.summary);
}

function updateSummary(summary){

    let html = "";

    for(let key in summary){

        html += `
        <div>
            <strong>${key}</strong> :
            ${summary[key]}
        </div>
        `;
    }

    document.getElementById("summaryContent").innerHTML = html;
}

sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("keypress", function(e){

    if(e.key === "Enter"){
        sendMessage();
    }

});

const observer = new MutationObserver(() => {
    chatBox.scrollTop = chatBox.scrollHeight;
});

observer.observe(chatBox, {
    childList:true
});

startChat();