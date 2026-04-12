const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function initVoiceInput(buttonId, targetInputId) {
  if (!SpeechRecognition) {
    const btn = document.getElementById(buttonId);
    if (btn) btn.style.display = "none";
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.lang = "en-US";
  recognition.interimResults = false;

  const startBtn = document.getElementById(buttonId);
  const targetInput = document.getElementById(targetInputId);

  if (!startBtn || !targetInput) return;

  startBtn.onclick = () => {
    if (startBtn.classList.contains("listening")) {
      recognition.stop();
      return;
    }
    recognition.start();
    startBtn.classList.add("listening");
    startBtn.textContent = "🔴 Listening...";
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    targetInput.value = transcript;
    startBtn.classList.remove("listening");
    startBtn.textContent = "🎤 Voice Input";
  };

  recognition.onerror = (event) => {
    console.error("Voice error:", event.error);
    startBtn.classList.remove("listening");
    startBtn.textContent = "🎤 Voice Input";
  };

  recognition.onend = () => {
    startBtn.classList.remove("listening");
    startBtn.textContent = "🎤 Voice Input";
  };
}

// Speech Synthesis — Read AI response aloud
function speakText(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 0.95;
  utterance.pitch = 1.0;
  // Prefer a female voice if available
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v => v.name.includes("Female") || v.name.includes("Samantha"));
  if (preferred) utterance.voice = preferred;
  window.speechSynthesis.speak(utterance);
}