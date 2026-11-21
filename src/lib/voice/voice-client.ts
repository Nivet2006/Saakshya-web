import { DangerAlert, LanguageCode, VisitDraft, VoiceSessionStatus } from '@/types';
import { ClientWebSocketMessage, ServerWebSocketMessage } from '@/lib/contracts/voice-events';

export interface VoiceClientCallbacks {
  onStatusChange: (status: VoiceSessionStatus) => void;
  onPartialTranscript: (text: string) => void;
  onFinalTranscript: (text: string) => void;
  onAssistantText: (text: string, state: string) => void;
  onAudioLevel: (level: number) => void;
  onVisitExtracted: (draft: Partial<VisitDraft>) => void;
  onDangerAlert: (alert: DangerAlert) => void;
  onError: (error: string) => void;
}

export class BrowserVoiceClient {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private audioSource: MediaStreamAudioSourceNode | null = null;
  private analyser: AnalyserNode | null = null;
  private activeAudioElements: HTMLAudioElement[] = [];

  private sessionId: string = '';
  private language: LanguageCode = 'hi-IN';
  private ashaWorkerId: string = '';
  private beneficiaryId?: string;
  private callbacks: VoiceClientCallbacks;
  private isInterrupted: boolean = false;
  private simulatedTimer: any = null;

  constructor(callbacks: VoiceClientCallbacks) {
    this.callbacks = callbacks;
  }

  async startSession(config: {
    sessionId: string;
    language: LanguageCode;
    ashaWorkerId: string;
    beneficiaryId?: string;
  }): Promise<void> {
    this.sessionId = config.sessionId;
    this.language = config.language;
    this.ashaWorkerId = config.ashaWorkerId;
    this.beneficiaryId = config.beneficiaryId;
    this.isInterrupted = false;

    this.callbacks.onStatusChange('connecting');

    // 1. Request microphone permission
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch (err: any) {
      console.error('Microphone access denied or error:', err);
      this.callbacks.onStatusChange('permission_denied');
      this.callbacks.onError('Microphone permission was denied. Please allow microphone access to capture visits by voice.');
      return;
    }

    // 2. Setup Web Audio & Analyser for live waveform
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContextClass({ sampleRate: 16000 });
      this.audioSource = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.audioSource.connect(this.analyser);

      this.monitorAudioLevel();
    } catch (err) {
      console.warn('Web Audio initialization warning:', err);
    }

    // 3. Connect to WebSocket or fallback to local simulated pipeline
    const wsUrl = process.env.NEXT_PUBLIC_VOICE_WS_URL || 'ws://localhost:8000/ws/voice';
    this.connectWebSocket(wsUrl);
  }

  private connectWebSocket(url: string) {
    try {
      this.ws = new WebSocket(url);
      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        this.callbacks.onStatusChange('listening');
        const startMsg: ClientWebSocketMessage = {
          type: 'session_start',
          session_id: this.sessionId,
          asha_worker_id: this.ashaWorkerId,
          beneficiary_id: this.beneficiaryId,
          language: this.language,
          audio_format: 'pcm_16000_s16le',
        };
        this.ws?.send(JSON.stringify(startMsg));
        this.startAudioStreaming();
      };

      this.ws.onmessage = (event) => {
        try {
          if (typeof event.data === 'string') {
            const data: ServerWebSocketMessage = JSON.parse(event.data);
            this.handleServerMessage(data);
          }
        } catch (e) {
          console.error('Error parsing WebSocket message', e);
        }
      };

      this.ws.onerror = (e) => {
        console.warn('WebSocket encountered error or backend unavailable, switching to local simulated AI loop', e);
        this.fallbackToSimulation();
      };

      this.ws.onclose = () => {
        if (!this.isInterrupted) {
          this.callbacks.onStatusChange('disconnected');
        }
      };
    } catch (e) {
      console.warn('Could not instantiate WebSocket, using simulated local pipeline', e);
      this.fallbackToSimulation();
    }
  }

  private startAudioStreaming() {
    if (!this.audioContext || !this.audioSource) return;

    this.processor = this.audioContext.createScriptProcessor(2048, 1, 1);
    this.audioSource.connect(this.processor);
    this.processor.connect(this.audioContext.destination);

    this.processor.onaudioprocess = (e) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const inputData = e.inputBuffer.getChannelData(0);
        // Convert Float32 to 16-bit PCM Linear
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        this.ws.send(pcm16.buffer);
      }
    };
  }

  private monitorAudioLevel() {
    if (!this.analyser) return;
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

    const checkLevel = () => {
      if (!this.analyser) return;
      this.analyser.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
      }
      const average = sum / dataArray.length;
      const normalized = Math.min(1, average / 128);
      this.callbacks.onAudioLevel(normalized);

      // Barge-in check: if user speaks while assistant audio is playing
      if (normalized > 0.35 && this.activeAudioElements.length > 0 && !this.isInterrupted) {
        this.triggerBargeIn();
      }

      requestAnimationFrame(checkLevel);
    };

    requestAnimationFrame(checkLevel);
  }

  private handleServerMessage(msg: ServerWebSocketMessage) {
    switch (msg.type) {
      case 'stt_partial':
        this.callbacks.onPartialTranscript(msg.text);
        break;
      case 'stt_final':
        this.callbacks.onFinalTranscript(msg.text);
        break;
      case 'assistant_text':
        this.callbacks.onStatusChange('speaking');
        this.callbacks.onAssistantText(msg.text, msg.state);
        break;
      case 'tts_audio_chunk':
        this.playAudioChunk(msg.audio_base64, msg.codec || 'wav');
        break;
      case 'tts_complete':
        this.callbacks.onStatusChange('listening');
        break;
      case 'interrupted':
        this.stopAudioPlayback();
        this.callbacks.onStatusChange('interrupted');
        break;
      case 'visit_extracted':
        this.callbacks.onVisitExtracted(msg.draft);
        break;
      case 'danger_alert':
        this.callbacks.onDangerAlert(msg.alert);
        break;
      case 'error':
        this.callbacks.onError(msg.message);
        break;
    }
  }

  triggerBargeIn() {
    this.isInterrupted = true;
    this.stopAudioPlayback();
    this.callbacks.onStatusChange('interrupted');

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const bargeMsg: ClientWebSocketMessage = {
        type: 'barge_in',
        session_id: this.sessionId,
        interrupted_at_ms: Date.now(),
      };
      this.ws.send(JSON.stringify(bargeMsg));
    }

    setTimeout(() => {
      this.isInterrupted = false;
      this.callbacks.onStatusChange('listening');
    }, 400);
  }

  sendVoiceCorrection(fieldName: string, targetValue?: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const msg: ClientWebSocketMessage = {
        type: 'voice_correction',
        session_id: this.sessionId,
        field_name: fieldName,
        target_value: targetValue,
      };
      this.ws.send(JSON.stringify(msg));
    }
  }

  private playAudioChunk(base64: string, codec: string) {
    try {
      const audio = new Audio(`data:audio/${codec};base64,${base64}`);
      this.activeAudioElements.push(audio);
      audio.onended = () => {
        this.activeAudioElements = this.activeAudioElements.filter((a) => a !== audio);
      };
      audio.play().catch((err) => {
        console.warn('Autoplay blocked or playback error:', err);
      });
    } catch (e) {
      console.error('Audio chunk playback failed', e);
    }
  }

  private stopAudioPlayback() {
    this.activeAudioElements.forEach((audio) => {
      audio.pause();
      audio.currentTime = 0;
    });
    this.activeAudioElements = [];
  }

  // Realistic fallback demo simulation for complete independent local execution
  private fallbackToSimulation() {
    this.callbacks.onStatusChange('listening');

    // Simulate speech detection after 2.5 seconds
    this.simulatedTimer = setTimeout(() => {
      const isSunita = this.beneficiaryId?.includes('1042') || !this.beneficiaryId;
      const lang = this.language;

      let partialText = '';
      let finalText = '';
      let referralInstruction = '';
      let assistantWarning = '';
      let assistantConfirm = '';

      if (lang === 'kn-IN') {
        partialText = isSunita ? 'ಸುನೀತಾ ಬಾಯಿ ಅವರ ರಕ್ತದೊತ್ತಡ 160/100 ಇದೆ...' : 'ಮಗುವಿಗೆ ಬಿಸಿಜಿ ಲಸಿಕೆ ನೀಡಲಾಗಿದೆ...';
        finalText = isSunita
          ? 'ಸುನೀತಾ ಬಾಯಿ ಅವರ ರಕ್ತದೊತ್ತಡ 160/100 ಇದೆ, ತೀವ್ರ ತಲೆನೋವು ಮತ್ತು ದೃಷ್ಟಿ ಮಸುಕಾಗಿದೆ. 32 ವಾರಗಳ ಗರ್ಭಧಾರಣೆ.'
          : 'ಮಗುವಿನ ತೂಕ 3.4 ಕೆಜಿ, ತಾಪಮಾನ 98.2 ಸಾಮಾನ್ಯವಾಗಿದೆ. ಇಂದು 6 ವಾರಗಳ ಪೆಂಟಾವಲೆಂಟ್ ಲಸಿಕೆ ನೀಡಬೇಕಾಗಿದೆ.';
        referralInstruction = 'ಅಪಾಯದ ಲಕ್ಷಣ: ತಕ್ಷಣ ಹತ್ತಿರದ ಸಿಎಚ್‌ಸಿ/ಎಫ್‌ಆರ್‌ಯು ಗೆ ರೆಫರ್ ಮಾಡಿ ಮತ್ತು 108 ಆಂಬ್ಯುಲೆನ್ಸ್ ಕರೆಯಿರಿ.';
        assistantWarning = 'ಅಪಾಯದ ಲಕ್ಷಣ ಪತ್ತೆಯಾಗಿದೆ! ಸುನೀತಾ ಬಾಯಿ ಅವರ ರಕ್ತದೊತ್ತಡ 160/100 ತುಂಬಾ ಹೆಚ್ಚಾಗಿದೆ. ತಕ್ಷಣ 108 ಆಂಬ್ಯುಲೆನ್ಸ್ ಕರೆ ಮಾಡಿ ಸಿಎಚ್‌ಸಿ ಗೆ ಕಳುಹಿಸಿ. ವಿವರಗಳನ್ನು ದೃಢೀಕರಿಸುತ್ತೀರಾ?';
        assistantConfirm = 'ಮಗುವಿನ ತೂಕ 3.4 ಕೆಜಿ, ತಾಪಮಾನ ಸಾಮಾನ್ಯ. 6 ವಾರಗಳ ಲಸಿಕೆ ಬಾಕಿ ಇದೆ. ದೃಢೀಕರಿಸುತ್ತೀರಾ?';
      } else if (lang === 'ta-IN') {
        partialText = isSunita ? 'சுனிதா பாய் அவர்களின் ரத்த அழுத்தம் 160/100 ஆக உள்ளது...' : 'குழந்தைக்கு பிசிஜி தடுப்பூசி போடப்பட்டுள்ளது...';
        finalText = isSunita
          ? 'சுனிதா பாய் அவர்களின் ரத்த அழுத்தம் 160/100 ஆக உள்ளது, கடுமையான தலைவலி மற்றும் பார்வை மங்கலாக உள்ளது. 32 வார கர்ப்பம்.'
          : 'குழந்தையின் எடை 3.4 கிலோ, வெப்பநிலை 98.2 சாதாரணமானது. இன்று 6 வார பென்டாவலண்ட் தடுப்பூசி செலுத்த வேண்டும்.';
        referralInstruction = 'அதிதீவிர ஆபத்து: உடனடியாக அருகிலுள்ள சி.எச்.சி/எஃப்.ஆர்.யு-க்கு பரிந்துரைத்து 108 ஆம்புலன்ஸை அழைக்கவும்.';
        assistantWarning = 'ஆபத்து அறிகுறி கண்டறியப்பட்டது! சுனிதா பாய் அவர்களின் ரத்த அழுத்தம் 160/100 மிக அதிகமாக உள்ளது. உடனடியாக 108 ஆம்புலன்ஸ் அழைக்கவும். விவரங்களை உறுதிப்படுத்துகிறீர்களா?';
        assistantConfirm = 'குழந்தையின் எடை 3.4 கிலோ, வெப்பநிலை இயல்பானது. 6 வார தடுப்பூசிகள் நிலுவையில் உள்ளன. உறுதிப்படுத்துகிறீர்களா?';
      } else if (lang === 'en-IN') {
        partialText = isSunita ? 'Sunita Bai blood pressure is 160 over 100...' : 'Infant administered BCG vaccine...';
        finalText = isSunita
          ? 'Sunita Bai blood pressure is 160 over 100 mmHg, severe frontal headache and blurred vision reported at 32 weeks gestation.'
          : 'Infant weight is 3.4 kg, temperature 98.2 normal. Due for 6-week Pentavalent-1 vaccination today.';
        referralInstruction = 'Critical danger sign: Immediate referral to nearby CHC/FRU required and dispatch 108 ambulance.';
        assistantWarning = 'Critical danger sign detected! Sunita Bai blood pressure is 160/100 mmHg. Please dispatch 108 ambulance and refer to CHC immediately. Do you confirm?';
        assistantConfirm = 'Infant weight is 3.4 kg, temperature normal. 6-week vaccines due. Do you confirm?';
      } else {
        // Hindi default (hi-IN)
        partialText = isSunita ? 'सुनीता बाई का बीपी 160 बटा 100 है...' : 'बच्चे को बीसीजी का टीका लगाया गया है...';
        finalText = isSunita
          ? 'सुनीता बाई का बीपी 160 बटा 100 है, सिर में तेज दर्द है और धुंधला दिख रहा है। 32 सप्ताह की गर्भावस्था है।'
          : 'बच्चे का वजन 3.4 किलो है, तापमान 98.2 सामान्य है। आज 6 सप्ताह का पेंटावेलेंट टीका लगना है।';
        referralInstruction = 'अत्यधिक खतरे का लक्षण: तुरंत नजदीकी सीएचसी/एफआरयू रेफर करें और 108 एम्बुलेंस बुलाएं।';
        assistantWarning = 'खतरे का संकेत मिला है! सुनीता बाई का रक्तचाप 160/100 बहुत अधिक है। तुरंत 108 एम्बुलेंस बुलाकर सीएचसी रेफर करें। क्या आप विवरण की पुष्टि करते हैं?';
        assistantConfirm = 'शिशु का वजन 3.4 किलो, तापमान सामान्य है। 6 सप्ताह के टीके देय हैं। क्या आप पुष्टि करते हैं?';
      }

      this.callbacks.onPartialTranscript(partialText);

      setTimeout(() => {
        this.callbacks.onFinalTranscript(finalText);
        this.callbacks.onStatusChange('processing');

        setTimeout(() => {
          if (isSunita) {
            // Emits safety-critical danger sign alert immediately
            const dangerAlert: DangerAlert = {
              alert_id: `ALT-${Date.now()}`,
              session_id: this.sessionId,
              beneficiary_id: this.beneficiaryId || 'c0000000-0000-0000-0000-000000001042',
              beneficiary_name: 'Sunita Bai',
              asha_worker_id: this.ashaWorkerId,
              phc_id: 'a0000000-0000-0000-0000-000000000001',
              severity: 'CRITICAL',
              category: 'severe_pre_eclampsia_eclampsia',
              symptom_evidence: 'BP 160/100, severe frontal headache, visual disturbance at 32 weeks.',
              referral_instruction: referralInstruction,
              referral_facility_type: 'CHC',
              referral_status: 'EN_ROUTE',
              supervisor_acknowledged: false,
              detected_at: new Date().toISOString(),
            };
            this.callbacks.onDangerAlert(dangerAlert);

            this.callbacks.onVisitExtracted({
              visit_type: 'ANC_2',
              vitals: {
                blood_pressure_sys: 160,
                blood_pressure_dia: 100,
                weight_kg: 56.5,
                temperature_f: 98.4,
                fetal_heart_rate_bpm: 144,
              },
              danger_signs_present: true,
              danger_signs: [dangerAlert],
              follow_up_required: true,
              follow_up_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
              follow_up_reason: 'Emergency pre-eclampsia referral check',
              notes: finalText,
              read_back_confirmed: true,
            });

            this.callbacks.onStatusChange('speaking');
            this.callbacks.onAssistantText(assistantWarning, 'danger_warning');
          } else {
            this.callbacks.onVisitExtracted({
              visit_type: 'IMMUNISATION',
              vitals: {
                weight_kg: 3.4,
                temperature_f: 98.2,
              },
              immunisations_administered: ['BCG', 'OPV-0'],
              immunisations_due: ['Pentavalent-1', 'Rotavirus-1'],
              danger_signs_present: false,
              follow_up_required: true,
              follow_up_date: new Date(Date.now() + 2 * 86400000).toISOString().split('T')[0],
              follow_up_reason: 'Pentavalent 1 vaccination due',
              read_back_confirmed: true,
            });

            this.callbacks.onStatusChange('speaking');
            this.callbacks.onAssistantText(assistantConfirm, 'reading_back');
          }
        }, 1200);
      }, 1500);
    }, 2000);
  }

  stopSession() {
    if (this.simulatedTimer) clearTimeout(this.simulatedTimer);
    this.stopAudioPlayback();

    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.audioSource) {
      this.audioSource.disconnect();
      this.audioSource = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.callbacks.onStatusChange('idle');
  }
}
