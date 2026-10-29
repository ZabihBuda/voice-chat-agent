// Speech layer: Azure Speech in the browser. To switch speech providers,
// replace listen() and speak() and keep the same signatures.
// Requires the Azure Speech SDK bundle (global `SpeechSDK`) loaded first.

let cachedToken = null; // { token, region, voice, language, fetchedAt }

async function getSpeechToken() {
  // Azure tokens last 10 minutes; refresh after 9 to be safe.
  if (cachedToken && Date.now() - cachedToken.fetchedAt < 9 * 60 * 1000) {
    return cachedToken;
  }
  const resp = await fetch("/api/speech-token");
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "Could not get a speech token.");
  cachedToken = { ...data, fetchedAt: Date.now() };
  return cachedToken;
}

async function speechConfig() {
  const { token, region, voice, language } = await getSpeechToken();
  const config = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
  config.speechRecognitionLanguage = language;
  config.speechSynthesisVoiceName = voice;
  return config;
}

// Listens to the microphone for one utterance and resolves with the text.
export async function listen() {
  const config = await speechConfig();
  const audio = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
  const recognizer = new SpeechSDK.SpeechRecognizer(config, audio);
  return new Promise((resolve, reject) => {
    recognizer.recognizeOnceAsync(
      (result) => {
        recognizer.close();
        if (result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
          resolve(result.text);
        } else if (result.reason === SpeechSDK.ResultReason.NoMatch) {
          resolve("");
        } else {
          const details = SpeechSDK.CancellationDetails.fromResult(result);
          reject(new Error(details.errorDetails || "Speech recognition was cancelled."));
        }
      },
      (err) => {
        recognizer.close();
        reject(new Error(err));
      }
    );
  });
}

let player = null;

// Reads the text aloud. Resolves when playback has been queued.
export async function speak(text) {
  stopSpeaking();
  const config = await speechConfig();
  player = new SpeechSDK.SpeakerAudioDestination();
  const audio = SpeechSDK.AudioConfig.fromSpeakerOutput(player);
  const synthesizer = new SpeechSDK.SpeechSynthesizer(config, audio);
  return new Promise((resolve, reject) => {
    synthesizer.speakTextAsync(
      text,
      (result) => {
        synthesizer.close();
        if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
          resolve();
        } else {
          reject(new Error(result.errorDetails || "Speech synthesis failed."));
        }
      },
      (err) => {
        synthesizer.close();
        reject(new Error(err));
      }
    );
  });
}

export function stopSpeaking() {
  if (player) {
    player.pause();
    player = null;
  }
}
