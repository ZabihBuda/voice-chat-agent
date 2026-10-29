import { listen, speak, stopSpeaking } from "./speech.js";

const micBtn = document.getElementById("mic");
const statusEl = document.getElementById("status");
const chatEl = document.getElementById("chat");
const form = document.getElementById("text-form");
const input = document.getElementById("text-input");

const history = []; // [{ role, content }] sent to the backend for context
let busy = false;

function setStatus(text) {
  statusEl.textContent = text;
}

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  chatEl.appendChild(el);
  chatEl.scrollTop = chatEl.scrollHeight;
  return el;
}

async function ask(question) {
  addMessage("user", question);
  setStatus("Thinking…");
  const resp = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history: history.slice(-10) }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "The agent could not answer.");
  history.push({ role: "user", content: question }, { role: "assistant", content: data.answer });
  addMessage("agent", data.answer);
  setStatus("Speaking…");
  await speak(data.answer);
}

async function run(getQuestion) {
  if (busy) return;
  busy = true;
  micBtn.disabled = true;
  stopSpeaking();
  try {
    const question = (await getQuestion()).trim();
    if (!question) {
      setStatus("I didn't catch that. Tap the mic and try again.");
      return;
    }
    await ask(question);
    setStatus("Tap the mic to ask another question.");
  } catch (err) {
    addMessage("error", err.message);
    setStatus("Something went wrong.");
  } finally {
    busy = false;
    micBtn.disabled = false;
    micBtn.classList.remove("listening");
  }
}

micBtn.addEventListener("click", () =>
  run(async () => {
    micBtn.classList.add("listening");
    setStatus("Listening… ask your question.");
    const text = await listen();
    micBtn.classList.remove("listening");
    return text;
  })
);

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value;
  input.value = "";
  run(async () => text);
});
