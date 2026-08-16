const messagesEl = document.getElementById("messages");
const agentBadge = document.getElementById("agent-badge");
const composer = document.getElementById("composer");
const input = document.getElementById("message-input");
const templatesList = document.getElementById("templates-list");

const sessionId =
  localStorage.getItem("giva_session_id") ||
  (() => {
    const id = crypto.randomUUID();
    localStorage.setItem("giva_session_id", id);
    return id;
  })();

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(message) {
  addMessage(message, "user");
  input.value = "";
  input.disabled = true;

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    if (!res.ok) {
      addMessage(`Error: ${res.status} ${res.statusText}`, "system");
      return;
    }
    const data = await res.json();
    addMessage(data.reply, "agent");
    agentBadge.textContent = data.agent;
    await refreshTemplates();
  } catch (err) {
    addMessage(`Network error: ${err}`, "system");
  } finally {
    input.disabled = false;
    input.focus();
  }
}

function renderTemplateCard(t) {
  const card = document.createElement("div");
  card.className = "template-card";
  const channelTag = document.createElement("div");
  channelTag.className = "tc-channel";
  channelTag.textContent = t.channel;
  const title = document.createElement("div");
  title.className = "tc-title";
  title.textContent = t.name;
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(t.payload, null, 2);
  card.appendChild(channelTag);
  card.appendChild(title);
  card.appendChild(pre);
  return card;
}

async function refreshTemplates() {
  try {
    const res = await fetch("/templates");
    const templates = await res.json();
    templatesList.innerHTML = "";
    if (!templates.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "No templates saved yet.";
      templatesList.appendChild(empty);
      return;
    }
    templates
      .slice()
      .reverse()
      .forEach((t) => templatesList.appendChild(renderTemplateCard(t)));
  } catch (err) {
    // non-fatal
  }
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  sendMessage(message);
});

addMessage(
  "Hi! I can help you create a WhatsApp Business template or a push notification for Giva. What would you like to build?",
  "agent"
);
refreshTemplates();
