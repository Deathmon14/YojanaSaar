import React, { useState, useEffect, useRef } from "react";

const VoiceAssistant = ({ onVoiceInput, aiResponse }) => {
  const [listening, setListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState(null); // <-- NEW: State for the best voice
  const recognitionRef = useRef(null);

  // --- NEW: Find and set the best available voice when the component loads ---
  useEffect(() => {
    const loadVoices = () => {
      const voices = speechSynthesis.getVoices();
      if (voices.length > 0) {
        // Prefer a non-local, English (India) voice if available
        let bestVoice = voices.find(v => v.lang === 'en-IN' && !v.localService);
        // Fallback to any other non-local English voice
        if (!bestVoice) {
          bestVoice = voices.find(v => v.lang.startsWith('en-') && !v.localService);
        }
        // Fallback to the first available English voice
        if (!bestVoice) {
          bestVoice = voices.find(v => v.lang.startsWith('en-'));
        }
        setSelectedVoice(bestVoice || voices[0]);
      }
    };

    // The 'voiceschanged' event is fired when the list of voices is ready
    speechSynthesis.onvoiceschanged = loadVoices;
    loadVoices(); // Initial attempt

    return () => {
      speechSynthesis.cancel();
      speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  useEffect(() => {
    // ... (The SpeechRecognition setup remains the same) ...
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      alert("Sorry, your browser doesn't support speech recognition.");
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onresult = (event) => onVoiceInput(event.results[0][0].transcript);
    recognition.onerror = (event) => console.error("Speech recognition error:", event.error);
    recognitionRef.current = recognition;
  }, [onVoiceInput]);

  const toggleListening = () => {
    if (listening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

  const toggleSpeech = () => {
    if (isSpeaking) {
      speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      if (!aiResponse || typeof aiResponse !== 'string') return;
      
      const utterance = new SpeechSynthesisUtterance(aiResponse);
      
      // --- NEW: Apply the selected voice and tune its properties ---
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }
      utterance.pitch = 1.1; // Make it sound slightly more expressive
      utterance.rate = 1.0;  // A natural speaking rate
      // -------------------------------------------------------------

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      
      speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="voice-assistant">
      <button onClick={toggleListening} disabled={isSpeaking}>
        🎙️ {listening ? "Listening..." : "Ask with Voice"}
      </button>

      <button onClick={toggleSpeech} disabled={!aiResponse}>
        🔊 {isSpeaking ? "Stop Reading" : "Read Response"}
      </button>
    </div>
  );
};

export default VoiceAssistant;