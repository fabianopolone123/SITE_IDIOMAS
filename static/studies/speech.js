(function () {
    const synth = window.speechSynthesis;
    const statusEl = document.querySelector('[data-voice-status]');
    const buttons = document.querySelectorAll('[data-speak-text]');
    let voiceLoadAttempts = 0;

    function setStatus(message) {
        if (statusEl) {
            statusEl.textContent = message;
        }
    }

    if (!synth || buttons.length === 0) {
        setStatus('Seu navegador nao oferece leitura em voz alta nesta tela.');
        buttons.forEach((button) => {
            button.disabled = true;
        });
        return;
    }

    function voices() {
        return synth ? synth.getVoices() : [];
    }

    function italianVoice() {
        const availableVoices = voices();
        return availableVoices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith('it')) || null;
    }

    function bestAvailableVoice() {
        const voices = synth.getVoices();
        return (
            voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith('it')) ||
            voices[0]
        );
    }

    function retryVoiceStatus() {
        if (voiceLoadAttempts >= 8 || voices().length > 0) {
            updateVoiceStatus();
            return;
        }

        voiceLoadAttempts += 1;
        window.setTimeout(retryVoiceStatus, 250);
    }

    function updateVoiceStatus() {
        const voice = bestAvailableVoice();
        if (!voice) {
            setStatus('Clique em play. O navegador ainda esta carregando as vozes.');
            return;
        }

        if (voice.lang && voice.lang.toLowerCase().startsWith('it')) {
            setStatus(`Voz selecionada: ${voice.name} (${voice.lang}).`);
        } else {
            setStatus('Nenhuma voz italiana foi encontrada; vou pedir ao navegador para falar em it-IT.');
        }
    }

    function speak(text, lang, button) {
        if (!text) {
            return;
        }

        synth.cancel();
        synth.resume();

        const utterance = new SpeechSynthesisUtterance(text);
        const voice = italianVoice();
        utterance.lang = lang || 'it-IT';
        utterance.rate = 0.82;
        utterance.pitch = 1;

        if (voice) {
            utterance.voice = voice;
            utterance.lang = voice.lang || lang || 'it-IT';
        }

        button.classList.add('is-playing');
        button.setAttribute('aria-busy', 'true');

        utterance.onend = function () {
            button.classList.remove('is-playing');
            button.removeAttribute('aria-busy');
        };

        utterance.onerror = function () {
            button.classList.remove('is-playing');
            button.removeAttribute('aria-busy');
            setStatus('Nao foi possivel tocar o audio agora. Tente novamente.');
        };

        synth.speak(utterance);
        window.setTimeout(() => synth.resume(), 120);
    }

    buttons.forEach((button) => {
        button.addEventListener('click', () => {
            speak(button.dataset.speakText, button.dataset.speakLang, button);
        });
    });

    retryVoiceStatus();
    if (typeof synth.onvoiceschanged !== 'undefined') {
        synth.onvoiceschanged = updateVoiceStatus;
    }
})();
