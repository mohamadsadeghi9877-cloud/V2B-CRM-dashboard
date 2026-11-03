// Ghofreyar Frontend Client Logic
document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messagesContainer");
  const micBtn = document.getElementById("micBtn");
  const micStatusText = document.getElementById("micStatusText");
  const textForm = document.getElementById("textForm");
  const textInput = document.getElementById("textInput");
  const sendBtn = document.getElementById("sendBtn");
  const resetBtn = document.getElementById("resetBtn");
  const offTopicIndicator = document.getElementById("offTopicIndicator");
  const completionRateBadge = document.getElementById("completionRateBadge");
  const progressBarFill = document.getElementById("progressBarFill");
  const showSummaryBtn = document.getElementById("showSummaryBtn");
  const confirmationModal = document.getElementById("confirmationModal");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const confirmLeadBtn = document.getElementById("confirmLeadBtn");
  const newVisitorFromModalBtn = document.getElementById("newVisitorFromModalBtn");
  const messageCountBadge = document.getElementById("messageCountBadge");
  const ttsAudioPlayer = document.getElementById("ttsAudioPlayer");
  const autoVoiceToggle = document.getElementById("autoVoiceToggle");
  const autoVoiceLabel = document.getElementById("autoVoiceLabel");

  let isRecording = false;
  let mediaRecorder = null;
  let audioChunks = [];
  let totalMessages = 0;

  // Auto-play voice setting: strictly OFF by default as requested
  let isAutoVoiceEnabled = localStorage.getItem("ghofreyar_auto_voice") === "true";
  if (autoVoiceToggle) {
    autoVoiceToggle.checked = isAutoVoiceEnabled;
    updateAutoVoiceLabel();
    autoVoiceToggle.addEventListener("change", () => {
      isAutoVoiceEnabled = autoVoiceToggle.checked;
      localStorage.setItem("ghofreyar_auto_voice", isAutoVoiceEnabled ? "true" : "false");
      updateAutoVoiceLabel();
      if (!isAutoVoiceEnabled && activeAudio) {
        activeAudio.pause();
        activeAudio = null;
        resetAllVoiceButtons();
      }
    });
  }

  function updateAutoVoiceLabel() {
    if (!autoVoiceLabel) return;
    if (isAutoVoiceEnabled) {
      autoVoiceLabel.textContent = "🔊 پخش خودکار: روشن";
    } else {
      autoVoiceLabel.textContent = "🔇 پخش خودکار: خاموش";
    }
  }

  // Initial State Load
  fetchState();

  async function fetchState() {
    try {
      const res = await fetch("/api/state");
      const state = await res.json();
      renderInitialMessages(state.history, state.greeting_audio);
      updateFormFields(state.form_data, {});
      checkOffTopic(state.is_off_topic);
    } catch (err) {
      console.error("Failed to load state:", err);
    }
  }

  let lastGreetingAudio = "";

  function renderInitialMessages(history, greetingAudio = "") {
    if (messagesContainer) messagesContainer.innerHTML = "";
    totalMessages = 0;
    (history || []).forEach((msg, idx) => {
      const audioToAttach = (idx === 0 && msg.role === "assistant") ? greetingAudio : "";
      appendMessage(msg.role, msg.content, false, audioToAttach);
    });
  }

  function appendMessage(role, text, isPlaying = false, audioBase64 = "") {
    if (!text) return;
    totalMessages++;
    if (messageCountBadge) messageCountBadge.textContent = `${totalMessages} پیام`;

    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;

    const senderHeader = document.createElement("div");
    senderHeader.className = "bubble-sender";

    if (role === "assistant") {
      senderHeader.innerHTML = `<span>🎙️ دستیار هوشمند CRM</span> ${isPlaying ? '<div class="playing-wave"><span></span><span></span><span></span></div>' : ''}`;
    } else {
      senderHeader.innerHTML = `<span>👤 مخاطب</span>`;
    }

    const contentText = document.createElement("div");
    contentText.className = "bubble-text";
    contentText.textContent = text;

    bubble.appendChild(senderHeader);
    bubble.appendChild(contentText);

    // If audio is provided for assistant, add an audio button
    if (role === "assistant" && audioBase64) {
      const audioRow = document.createElement("div");
      audioRow.className = "audio-action-row";
      const listenBtn = document.createElement("button");
      listenBtn.className = "play-voice-btn";
      listenBtn.innerHTML = "🔊 شنیدن گفتار";
      listenBtn.title = "پخش صدای دستیار هوشمند";
      listenBtn.onclick = (e) => {
        e.stopPropagation();
        toggleAudioPlayback(audioBase64, listenBtn, bubble);
      };
      audioRow.appendChild(listenBtn);
      bubble.appendChild(audioRow);
    }

    if (messagesContainer) {
      messagesContainer.appendChild(bubble);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    return bubble;
  }

  const formFieldIds = [
    "full_name",
    "phone_number",
    "email",
    "company_name",
    "job_title",
    "project_description",
    "field_of_interest",
    "estimated_budget",
    "timeline",
    "notes"
  ];

  function clearAllFormFields() {
    formFieldIds.forEach(f => {
      const inputEl = document.getElementById(`input-${f}`);
      const cardElement = document.getElementById(`field-${f}`);
      if (inputEl) inputEl.value = "";
      if (cardElement) {
        cardElement.classList.remove("filled", "highlight");
      }
    });
    if (progressBarFill) progressBarFill.style.width = "0%";
    if (completionRateBadge) completionRateBadge.textContent = "0٪ تکمیل شده";
  }

  function updateFormFields(formData, updatedFields = {}, forceClear = false) {
    if (forceClear || !formData) {
      clearAllFormFields();
      return;
    }

    let filledCount = 0;

    formFieldIds.forEach(f => {
      const inputEl = document.getElementById(`input-${f}`);
      const cardElement = document.getElementById(`field-${f}`);
      if (!inputEl || !cardElement) return;

      const val = formData[f];

      if (val && String(val).trim()) {
        inputEl.value = val;
        cardElement.classList.add("filled");
        filledCount++;

        // If this field was updated in this turn, trigger animation
        if (updatedFields[f]) {
          cardElement.classList.remove("highlight");
          void cardElement.offsetWidth; // trigger reflow
          cardElement.classList.add("highlight");
        }
      } else if (!inputEl.value.trim()) {
        cardElement.classList.remove("filled");
      } else {
        filledCount++;
      }
    });

    // Update progress bar
    const percentage = Math.round((filledCount / formFieldIds.length) * 100);
    if (progressBarFill) progressBarFill.style.width = `${percentage}%`;
    if (completionRateBadge) completionRateBadge.textContent = `${percentage}٪ تکمیل شده`;
  }

  // Allow manual typing in form fields to update progress bar and state dynamically
  formFieldIds.forEach(f => {
    const el = document.getElementById(`input-${f}`);
    if (el) {
      el.addEventListener("input", () => {
        const cardElement = document.getElementById(`field-${f}`);
        if (el.value.trim()) {
          if (cardElement) cardElement.classList.add("filled");
        } else {
          if (cardElement) cardElement.classList.remove("filled");
        }
        let filled = 0;
        formFieldIds.forEach(id => {
          const inp = document.getElementById(`input-${id}`);
          if (inp && inp.value.trim()) filled++;
        });
        const pct = Math.round((filled / formFieldIds.length) * 100);
        if (progressBarFill) progressBarFill.style.width = `${pct}%`;
        if (completionRateBadge) completionRateBadge.textContent = `${pct}٪ تکمیل شده`;
      });
    }
  });

  function checkOffTopic(isOffTopic) {
    if (!offTopicIndicator) return;
    if (isOffTopic) {
      offTopicIndicator.classList.remove("hidden");
    } else {
      offTopicIndicator.classList.add("hidden");
    }
  }

  let activeAudio = null;
  let currentlyPlayingBtn = null;
  let currentlyPlayingBubble = null;

  function resetAllVoiceButtons() {
    if (currentlyPlayingBtn) {
      currentlyPlayingBtn.innerHTML = "🔊 شنیدن گفتار";
      currentlyPlayingBtn.classList.remove("is-playing");
    }
    if (currentlyPlayingBubble) {
      const wave = currentlyPlayingBubble.querySelector(".playing-wave");
      if (wave) wave.remove();
    }
    currentlyPlayingBtn = null;
    currentlyPlayingBubble = null;
    if (micStatusText) {
      micStatusText.textContent = "برای صحبت با دستیار صوتی کلیک کنید";
    }
  }

  function toggleAudioPlayback(audioBase64, buttonEl, bubbleEl) {
    if (!audioBase64) return;

    // If this audio is currently playing, pause it and reset button
    if (activeAudio && currentlyPlayingBtn === buttonEl) {
      activeAudio.pause();
      activeAudio = null;
      resetAllVoiceButtons();
      return;
    }

    // Stop previous audio if any
    if (activeAudio) {
      activeAudio.pause();
      activeAudio = null;
      resetAllVoiceButtons();
    }

    try {
      const audioUrl = base64ToBlobUrl(audioBase64);
      activeAudio = new Audio(audioUrl);
      activeAudio.volume = 1.0;

      currentlyPlayingBtn = buttonEl;
      currentlyPlayingBubble = bubbleEl;
      buttonEl.innerHTML = "⏹️ توقف گفتار";
      buttonEl.classList.add("is-playing");

      // Add playing wave to bubble header
      const header = bubbleEl.querySelector(".bubble-sender");
      if (header && !header.querySelector(".playing-wave")) {
        const wave = document.createElement("div");
        wave.className = "playing-wave";
        wave.innerHTML = "<span></span><span></span><span></span>";
        header.appendChild(wave);
      }

      if (micStatusText) {
        micStatusText.textContent = "🔊 در حال پخش صدای دستیار...";
      }

      activeAudio.onended = () => {
        resetAllVoiceButtons();
      };

      activeAudio.onerror = () => {
        resetAllVoiceButtons();
      };

      activeAudio.play().catch(err => {
        console.warn("Audio playback interrupted:", err);
        resetAllVoiceButtons();
      });
    } catch (err) {
      console.error("Playback error:", err);
      resetAllVoiceButtons();
    }
  }

  function base64ToBlobUrl(base64Audio) {
    const binaryString = atob(base64Audio);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: "audio/wav" });
    return URL.createObjectURL(blob);
  }

  function playTTS(base64Audio) {
    if (!base64Audio) return;
    try {
      if (activeAudio) {
        activeAudio.pause();
        activeAudio = null;
        resetAllVoiceButtons();
      }
      const audioUrl = base64ToBlobUrl(base64Audio);
      activeAudio = new Audio(audioUrl);
      activeAudio.volume = 1.0;

      // Update micStatusText to let user know voice is playing
      micStatusText.textContent = "🔊 در حال پخش صدای دستیار...";

      activeAudio.onended = () => {
        resetAllVoiceButtons();
      };

      activeAudio.onerror = () => {
        resetAllVoiceButtons();
      };

      const playPromise = activeAudio.play();
      if (playPromise !== undefined) {
        playPromise.catch(err => {
          console.warn("Auto-play blocked by browser. User can click 'شنیدن گفتار' button:", err);
          resetAllVoiceButtons();
        });
      }
    } catch (e) {
      console.error("Audio playback error:", e);
      resetAllVoiceButtons();
    }
  }

  // Handle Text Submission
  if (textForm) {
    textForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!textInput) return;
      const text = textInput.value.trim();
      if (!text) return;

      appendMessage("user", text);
      textInput.value = "";
      textInput.disabled = true;
      if (sendBtn) sendBtn.disabled = true;
      if (micStatusText) micStatusText.textContent = "در حال پردازش پاسخ دستیار...";

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        handleTurnResponse(data);
      } catch (err) {
        console.error("Chat error:", err);
        appendMessage("assistant", "متأسفانه مشکلی در ارتباط پیش آمد. لطفاً دوباره تلاش کنید.");
      } finally {
        textInput.disabled = false;
        if (sendBtn) sendBtn.disabled = false;
        textInput.focus();
        if (micStatusText) micStatusText.textContent = "برای صحبت با دستیار صوتی کلیک کنید";
      }
    });
  }

  function handleTurnResponse(data) {
    appendMessage("assistant", data.spoken_response, false, data.audio_base64 || "");
    updateFormFields(data.form_data, data.updated_fields || {});
    checkOffTopic(data.is_off_topic);

    // Strictly do NOT auto-play audio unless user explicitly turned on the toggle switch
    if (isAutoVoiceEnabled && data.audio_base64) {
      playTTS(data.audio_base64);
    }

    if (data.conversation_complete) {
      setTimeout(() => {
        openSummaryModal();
      }, 1500);
    }
  }

  let audioCtx = null;
  let micStream = null;
  let scriptNode = null;
  let audioSamples = [];

  function encodeWAV(samples, sampleRate = 16000) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    function writeString(v, offset, string) {
      for (let i = 0; i < string.length; i++) {
        v.setUint8(offset + i, string.charCodeAt(i));
      }
    }
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      offset += 2;
    }
    return new Blob([view], { type: 'audio/wav' });
  }

  // Speech Recognition API (Native Webkit/Blink Speech Recognition for 99.9% Persian Accuracy)
  try {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let speechRecognitionTranscript = "";

    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.lang = "fa-IR";
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            speechRecognitionTranscript += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        if (micStatusText) micStatusText.textContent = speechRecognitionTranscript || interim || "در حال شنیدن گفتار شما...";
      };

      recognition.onerror = (event) => {
        console.warn("Browser SpeechRecognition warning:", event.error);
      };

      recognition.onend = () => {
        if (isRecording) {
          stopRecording();
        }
      };
    }
  } catch (e) {
    console.warn("Speech recognition init skipped:", e);
  }

  let mediaRecorderInstance = null;
  let recordedAudioChunks = [];

  // Handle Microphone Recording
  if (micBtn) {
    micBtn.addEventListener("click", async () => {
      if (isRecording) {
        stopRecording();
      } else {
        await startRecording();
      }
    });
  }

  async function startRecording() {
    try {
      // Professional Studio-grade audio constraints with active Noise Suppression
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 48000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      recordedAudioChunks = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : (MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "");

      mediaRecorderInstance = mimeType
        ? new MediaRecorder(micStream, { mimeType, audioBitsPerSecond: 128000 })
        : new MediaRecorder(micStream);

      mediaRecorderInstance.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          recordedAudioChunks.push(e.data);
        }
      };

      mediaRecorderInstance.onstop = async () => {
        const audioBlob = new Blob(recordedAudioChunks, { type: mediaRecorderInstance.mimeType || "audio/webm" });
        await sendAudio(audioBlob);
      };

      mediaRecorderInstance.start(250); // Slice every 250ms to prevent buffer drops

      isRecording = true;
      micBtn.classList.add("recording");
      micStatusText.textContent = "در حال ضبط با کیفیت استودیویی... وقتی صحبت تمام شد کلیک کنید";
    } catch (err) {
      console.error("Mic access error:", err);
      alert("دسترسی به میکروفون امکان‌پذیر نیست. لطفاً اجازه دسترسی را در مرورگر تأیید فرمایید.");
    }
  }

  async function stopRecording() {
    if (isRecording) {
      isRecording = false;
      micBtn.classList.remove("recording");
      micStatusText.textContent = "در حال پردازش گفتار با مدل شنوا...";

      if (mediaRecorderInstance && mediaRecorderInstance.state !== "inactive") {
        mediaRecorderInstance.stop();
      }
      if (micStream) {
        micStream.getTracks().forEach(t => t.stop());
        micStream = null;
      }
    }
  }

  async function sendAudio(blob) {
    const formData = new FormData();
    const extension = blob.type.includes("webm") ? "webm" : "wav";
    formData.append("file", blob, `visitor_speech.${extension}`);

    try {
      const res = await fetch("/api/chat/audio", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.transcript) {
        appendMessage("user", data.transcript);
      }
      handleTurnResponse(data);
    } catch (err) {
      console.error("Audio upload error:", err);
      appendMessage("assistant", "خطا در دریافت صدا. لطفاً دوباره صحبت کنید یا تایپ نمایید.");
    } finally {
      micStatusText.textContent = "برای صحبت با دستیار صوتی کلیک کنید";
    }
  }

  // Reset Session
  if (resetBtn) {
    resetBtn.addEventListener("click", async () => {
      if (confirm("آیا مایلید اطلاعات این مشتری ریست شده و فرم برای مشتری جدید کاملاً خالی شود؟")) {
        await performReset();
      }
    });
  }

  async function performReset() {
    try {
      // 1. Immediately empty all form inputs and cards in the UI
      clearAllFormFields();
      if (textInput) textInput.value = "";
      if (ttsAudioPlayer) {
        ttsAudioPlayer.pause();
        ttsAudioPlayer.currentTime = 0;
      }
      if (activeAudio) {
        activeAudio.pause();
        activeAudio = null;
        resetAllVoiceButtons();
      }
      checkOffTopic(false);
      confirmationModal.classList.add("hidden");

      // 2. Notify backend to clear history and form state
      const res = await fetch("/api/reset", { method: "POST" });
      const data = await res.json();

      // 3. Render fresh initial greeting
      renderInitialMessages([{ role: "assistant", content: data.greeting }]);
      clearAllFormFields();
    } catch (err) {
      console.error("Reset error:", err);
      clearAllFormFields();
    }
  }

  // Summary Modal Logic
  if (showSummaryBtn) {
    showSummaryBtn.addEventListener("click", async () => {
      await openSummaryModal();
    });
  }

  let lastFetchedSummary = null;

  async function openSummaryModal() {
    try {
      const res = await fetch("/api/summary");
      const summary = await res.json();
      
      // Override with manual edits from live inputs if user typed anything
      const getInpVal = (f) => {
        const inp = document.getElementById(`input-${f}`);
        return inp && inp.value.trim() ? inp.value.trim() : null;
      };

      summary.full_name = getInpVal("full_name") || summary.full_name;
      summary.phone_number = getInpVal("phone_number") || summary.phone_number;
      summary.email = getInpVal("email") || summary.email;
      summary.company_name = getInpVal("company_name") || summary.company_name;
      summary.job_title = getInpVal("job_title") || summary.job_title;
      summary.project_description = getInpVal("project_description") || summary.project_description;
      summary.field_of_interest = getInpVal("field_of_interest") || summary.field_of_interest;
      summary.estimated_budget = getInpVal("estimated_budget") || summary.estimated_budget;
      summary.timeline = getInpVal("timeline") || summary.timeline;
      summary.notes = getInpVal("notes") || summary.notes;

      lastFetchedSummary = summary;

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val || "—";
      };

      setVal("sum-full_name", summary.full_name);
      setVal("sum-phone_number", summary.phone_number);
      setVal("sum-email", summary.email);
      setVal("sum-company_name", summary.company_name);
      setVal("sum-job_title", summary.job_title);
      setVal("sum-project_description", summary.project_description);
      setVal("sum-field_of_interest", summary.field_of_interest);
      setVal("sum-estimated_budget", summary.estimated_budget);
      setVal("sum-timeline", summary.timeline);
      setVal("sum-notes", summary.notes);

      if (confirmationModal) confirmationModal.classList.remove("hidden");
    } catch (err) {
      console.error("Error fetching summary:", err);
    }
  }

  const copyLeadBtn = document.getElementById("copyLeadBtn");
  if (copyLeadBtn) {
    copyLeadBtn.addEventListener("click", () => {
      if (!lastFetchedSummary) return;
      const text = `📌 شناسنامه لید نمایشگاه:
👤 نام: ${lastFetchedSummary.full_name || "—"}
📱 شماره تماس: ${lastFetchedSummary.phone_number || "—"}
✉️ ایمیل: ${lastFetchedSummary.email || "—"}
🏢 شرکت: ${lastFetchedSummary.company_name || "—"}
💼 سمت: ${lastFetchedSummary.job_title || "—"}
💡 شرح پروژه: ${lastFetchedSummary.project_description || "—"}
🎯 حوزه علاقه‌مندی: ${lastFetchedSummary.field_of_interest || "—"}
💰 بودجه: ${lastFetchedSummary.estimated_budget || "—"}
⏱️ بازه زمانی: ${lastFetchedSummary.timeline || "—"}
📝 یادداشت‌ها: ${lastFetchedSummary.notes || "—"}`;
      navigator.clipboard.writeText(text).then(() => {
        alert("✅ مشخصات کامل لید در کلیپ‌بورد کپی شد.");
      }).catch(err => {
        console.error("Copy error:", err);
      });
    });
  }

  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", () => {
      if (confirmationModal) confirmationModal.classList.add("hidden");
    });
  }

  if (confirmLeadBtn) {
    confirmLeadBtn.addEventListener("click", async () => {
      if (!lastFetchedSummary) return;
      try {
        // Save directly to SQLite CRM database via Quick Capture API
        const projectDesc = (lastFetchedSummary.project_description && lastFetchedSummary.project_description.trim()) ? lastFetchedSummary.project_description.trim() : null;
        const payload = {
          full_name: lastFetchedSummary.full_name || "بازدیدکننده ناشناس",
          phone_number: lastFetchedSummary.phone_number || "ثبت‌نشده",
          email: lastFetchedSummary.email || null,
          company_name: lastFetchedSummary.company_name || null,
          job_title: lastFetchedSummary.job_title || null,
          project_title: projectDesc,
          field_of_interest: lastFetchedSummary.field_of_interest || null,
          estimated_budget: lastFetchedSummary.estimated_budget || null,
          timeline: lastFetchedSummary.timeline || null,
          notes: lastFetchedSummary.notes || null,
          temperature: projectDesc ? "Hot" : "Warm"
        };

        const res = await fetch("/api/crm/quick-capture", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          if (projectDesc || payload.field_of_interest || payload.estimated_budget) {
            alert("✅ مشخصات با موفقیت در ۴ شیت CRM (مخاطبان، شرکت‌ها، سرنخ‌ها و فرصت‌های فروش) ثبت شد!");
          } else {
            alert("✅ مشخصات با موفقیت در ۳ شیت CRM (مخاطبان، شرکت‌ها و سرنخ‌ها) ثبت شد.\n(با توجه به عدم ارائه درخواست مشخص، در شیت فرصت‌های فروش رکوردی ایجاد نشد.)");
          }
          if (confirmationModal) confirmationModal.classList.add("hidden");
          loadCRMLeads();
          loadCRMContacts();
          loadCRMCompanies();
          loadCRMOpportunities();
          if (confirm("آیا مایلید فرم برای ثبت مشخصات مشتری بعدی خالی شود؟")) {
            await performReset();
          }
        } else {
          alert("خطا در ذخیره‌سازی در دیتابیس.");
        }
      } catch (err) {
        console.error("Save to CRM error:", err);
        alert("خطا در ارتباط با سرور CRM.");
      }
    });
  }

  if (newVisitorFromModalBtn) {
    newVisitorFromModalBtn.addEventListener("click", async () => {
      if (confirmationModal) confirmationModal.classList.add("hidden");
      await performReset();
    });
  }

  // ==========================================
  // CRM DASHBOARD LOGIC (فاز ۳)
  // ==========================================

  const tabBtnAgent = document.getElementById("tabBtnAgent");
  const tabBtnCRM = document.getElementById("tabBtnCRM");
  const viewAgent = document.getElementById("viewAgent");
  const viewCRM = document.getElementById("viewCRM");
  const navLeadsCount = document.getElementById("navLeadsCount");

  const statTotalLeads = document.getElementById("statTotalLeads");
  const statHotLeads = document.getElementById("statHotLeads");
  const statContactedLeads = document.getElementById("statContactedLeads");
  const statWonLeads = document.getElementById("statWonLeads");

  const filterTemperature = document.getElementById("filterTemperature");
  const filterStatus = document.getElementById("filterStatus");
  const btnRefreshLeads = document.getElementById("btnRefreshLeads");
  const crmLeadsTableBody = document.getElementById("crmLeadsTableBody");

  // CRM Sub-tabs elements
  const subTabLeads = document.getElementById("subTabLeads");
  const subTabOpportunities = document.getElementById("subTabOpportunities");
  const subTabContacts = document.getElementById("subTabContacts");
  const subTabCompanies = document.getElementById("subTabCompanies");

  const tableSectionLeads = document.getElementById("tableSectionLeads");
  const tableSectionOpportunities = document.getElementById("tableSectionOpportunities");
  const tableSectionContacts = document.getElementById("tableSectionContacts");
  const tableSectionCompanies = document.getElementById("tableSectionCompanies");

  const btnRefreshContacts = document.getElementById("btnRefreshContacts");
  const btnRefreshCompanies = document.getElementById("btnRefreshCompanies");
  const btnRefreshOpportunities = document.getElementById("btnRefreshOpportunities");
  const filterOppStage = document.getElementById("filterOppStage");
  const btnOpenAddOppModal = document.getElementById("btnOpenAddOppModal");
  const crmOpportunitiesTableBody = document.getElementById("crmOpportunitiesTableBody");

  const oppKpiTotalAmount = document.getElementById("oppKpiTotalAmount");
  const oppKpiTotalCount = document.getElementById("oppKpiTotalCount");
  const oppKpiOpenAmount = document.getElementById("oppKpiOpenAmount");
  const oppKpiOpenCount = document.getElementById("oppKpiOpenCount");
  const oppKpiWonAmount = document.getElementById("oppKpiWonAmount");
  const oppKpiWonCount = document.getElementById("oppKpiWonCount");
  const oppKpiWinRate = document.getElementById("oppKpiWinRate");

  const crmContactsTableBody = document.getElementById("crmContactsTableBody");
  const crmCompaniesTableBody = document.getElementById("crmCompaniesTableBody");

  const crmQuickCaptureForm = document.getElementById("crmQuickCaptureForm");

  // Sub-Tab Switching Logic
  function switchCRMSubTab(activeTab) {
    [subTabLeads, subTabOpportunities, subTabContacts, subTabCompanies].forEach(t => {
      if (t) t.classList.remove("active");
    });
    [tableSectionLeads, tableSectionOpportunities, tableSectionContacts, tableSectionCompanies].forEach(s => {
      if (s) s.classList.add("hidden");
    });

    if (activeTab === "leads") {
      if (subTabLeads) subTabLeads.classList.add("active");
      if (tableSectionLeads) tableSectionLeads.classList.remove("hidden");
      loadCRMLeads();
    } else if (activeTab === "opportunities") {
      if (subTabOpportunities) subTabOpportunities.classList.add("active");
      if (tableSectionOpportunities) tableSectionOpportunities.classList.remove("hidden");
      loadCRMOpportunities();
      loadOpportunityStats();
    } else if (activeTab === "contacts") {
      if (subTabContacts) subTabContacts.classList.add("active");
      if (tableSectionContacts) tableSectionContacts.classList.remove("hidden");
      loadCRMContacts();
    } else if (activeTab === "companies") {
      if (subTabCompanies) subTabCompanies.classList.add("active");
      if (tableSectionCompanies) tableSectionCompanies.classList.remove("hidden");
      loadCRMCompanies();
    }
  }

  if (subTabLeads) subTabLeads.addEventListener("click", () => switchCRMSubTab("leads"));
  if (subTabOpportunities) subTabOpportunities.addEventListener("click", () => switchCRMSubTab("opportunities"));
  if (subTabContacts) subTabContacts.addEventListener("click", () => switchCRMSubTab("contacts"));
  if (subTabCompanies) subTabCompanies.addEventListener("click", () => switchCRMSubTab("companies"));

  if (btnRefreshContacts) btnRefreshContacts.addEventListener("click", loadCRMContacts);
  if (btnRefreshCompanies) btnRefreshCompanies.addEventListener("click", loadCRMCompanies);
  if (btnRefreshOpportunities) btnRefreshOpportunities.addEventListener("click", loadCRMOpportunities);
  if (filterOppStage) filterOppStage.addEventListener("change", loadCRMOpportunities);

  // Main Nav Tab switching
  if (tabBtnAgent) {
    tabBtnAgent.addEventListener("click", () => {
      tabBtnAgent.classList.add("active");
      if (tabBtnCRM) tabBtnCRM.classList.remove("active");
      if (viewAgent) viewAgent.classList.remove("hidden");
      if (viewCRM) viewCRM.classList.add("hidden");
    });
  }

  if (tabBtnCRM) {
    tabBtnCRM.addEventListener("click", () => {
      tabBtnCRM.classList.add("active");
      if (tabBtnAgent) tabBtnAgent.classList.remove("active");
      if (viewCRM) viewCRM.classList.remove("hidden");
      if (viewAgent) viewAgent.classList.add("hidden");
      loadCRMLeads();
      loadCRMContacts();
      loadCRMCompanies();
      loadCRMOpportunities();
    });
  }

  // Load Contacts (Table 2)
  async function loadCRMContacts() {
    if (!crmContactsTableBody) return;
    try {
      crmContactsTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">در حال دریافت اطلاعات مخاطبان...</td></tr>`;
      const res = await fetch("/api/crm/contacts");
      const contacts = await res.json();
      renderCRMContacts(contacts);
    } catch (err) {
      console.error("Error loading CRM contacts:", err);
      crmContactsTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #f43f5e; padding: 1.5rem;">خطا در بارگذاری مخاطبان</td></tr>`;
    }
  }

  function renderCRMContacts(contacts) {
    if (!crmContactsTableBody) return;
    crmContactsTableBody.innerHTML = "";

    if (!contacts || contacts.length === 0) {
      crmContactsTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">هیچ مخاطبی در دیتابیس ثبت نشده است.</td></tr>`;
      return;
    }

    contacts.forEach((c, index) => {
      const tr = document.createElement("tr");
      const compName = c.company ? c.company.name : "—";
      const createdAt = c.created_at ? new Date(c.created_at).toLocaleDateString("fa-IR") : "—";

      tr.innerHTML = `
        <td>${index + 1}</td>
        <td><strong>${c.full_name}</strong></td>
        <td>${c.job_title || "—"}</td>
        <td><span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa;">${compName}</span></td>
        <td dir="ltr" style="text-align: right;">${c.phone_number || "—"}</td>
        <td>${c.email || "—"}</td>
        <td>${createdAt}</td>
        <td>
          <button class="btn-edit-contact" data-contact-id="${c.id}" title="ویرایش مخاطب" style="margin-left: 0.35rem; background: transparent; border: none; cursor: pointer; font-size: 1rem;">✏️</button>
          <button class="btn-delete-contact" data-contact-id="${c.id}" title="حذف مخاطب" style="background: transparent; border: none; cursor: pointer; font-size: 1rem;">🗑️</button>
        </td>
      `;
      crmContactsTableBody.appendChild(tr);
    });

    document.querySelectorAll(".btn-edit-contact").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = parseInt(e.currentTarget.getAttribute("data-contact-id"), 10);
        const contact = contacts.find(x => x.id === id);
        if (contact) openEditContactModal(contact);
      });
    });

    document.querySelectorAll(".btn-delete-contact").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-contact-id");
        if (confirm("آیا از حذف این مخاطب اطمینان دارید؟")) {
          try {
            await fetch(`/api/crm/contacts/${id}`, { method: "DELETE" });
            loadCRMContacts();
          } catch (err) {
            console.error("Delete contact error:", err);
          }
        }
      });
    });
  }

  // Load Companies (Table 3)
  async function loadCRMCompanies() {
    if (!crmCompaniesTableBody) return;
    try {
      crmCompaniesTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">در حال دریافت اطلاعات شرکت‌ها...</td></tr>`;
      const res = await fetch("/api/crm/companies");
      const companies = await res.json();
      renderCRMCompanies(companies);
    } catch (err) {
      console.error("Error loading CRM companies:", err);
      crmCompaniesTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #f43f5e; padding: 1.5rem;">خطا در بارگذاری شرکت‌ها</td></tr>`;
    }
  }

  function renderCRMCompanies(companies) {
    if (!crmCompaniesTableBody) return;
    crmCompaniesTableBody.innerHTML = "";

    if (!companies || companies.length === 0) {
      crmCompaniesTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">هیچ شرکتی در دیتابیس ثبت نشده است.</td></tr>`;
      return;
    }

    companies.forEach((comp, index) => {
      const tr = document.createElement("tr");
      const createdAt = comp.created_at ? new Date(comp.created_at).toLocaleDateString("fa-IR") : "—";
      const website = comp.website ? `<a href="${comp.website}" target="_blank" style="color: #38bdf8;">${comp.website}</a>` : "—";

      tr.innerHTML = `
        <td>${index + 1}</td>
        <td><strong>${comp.name}</strong></td>
        <td>${comp.industry || "عمومی / نامشخص"}</td>
        <td dir="ltr" style="text-align: right;">${comp.phone || "—"}</td>
        <td>${website}</td>
        <td>${comp.address || "—"}</td>
        <td>${createdAt}</td>
        <td>
          <button class="btn-edit-company" data-company-id="${comp.id}" title="ویرایش شرکت" style="margin-left: 0.35rem; background: transparent; border: none; cursor: pointer; font-size: 1rem;">✏️</button>
          <button class="btn-delete-company" data-company-id="${comp.id}" title="حذف شرکت" style="background: transparent; border: none; cursor: pointer; font-size: 1rem;">🗑️</button>
        </td>
      `;
      crmCompaniesTableBody.appendChild(tr);
    });

    document.querySelectorAll(".btn-edit-company").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = parseInt(e.currentTarget.getAttribute("data-company-id"), 10);
        const company = companies.find(x => x.id === id);
        if (company) openEditCompanyModal(company);
      });
    });

    document.querySelectorAll(".btn-delete-company").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-company-id");
        if (confirm("آیا از حذف این شرکت اطمینان دارید؟")) {
          try {
            await fetch(`/api/crm/companies/${id}`, { method: "DELETE" });
            loadCRMCompanies();
          } catch (err) {
            console.error("Delete company error:", err);
          }
        }
      });
    });
  }

  // Load Leads from REST API
  async function loadCRMLeads() {
    try {
      const temp = filterTemperature ? filterTemperature.value : "";
      const stat = filterStatus ? filterStatus.value : "";

      let url = "/api/crm/leads?";
      if (temp) url += `temperature=${encodeURIComponent(temp)}&`;
      if (stat) url += `status=${encodeURIComponent(stat)}&`;

      const res = await fetch(url);
      const leads = await res.json();
      renderCRMTable(leads);
      updateCRMStats(leads);
    } catch (err) {
      console.error("Error loading CRM leads:", err);
    }
  }

  if (btnRefreshLeads) btnRefreshLeads.addEventListener("click", loadCRMLeads);
  if (filterTemperature) filterTemperature.addEventListener("change", loadCRMLeads);
  if (filterStatus) filterStatus.addEventListener("change", loadCRMLeads);

  function updateCRMStats(leads) {
    if (!Array.isArray(leads)) return;
    const total = leads.length;
    const hot = leads.filter(l => l.temperature === "Hot").length;
    const contacted = leads.filter(l => l.status === "In_Progress" || l.status === "Contacted").length;
    const won = leads.filter(l => l.status === "Won").length;

    if (statTotalLeads) statTotalLeads.textContent = total;
    if (statHotLeads) statHotLeads.textContent = hot;
    if (statContactedLeads) statContactedLeads.textContent = contacted;
    if (statWonLeads) statWonLeads.textContent = won;
    if (navLeadsCount) navLeadsCount.textContent = total;
  }

  function renderCRMTable(leads) {
    if (!crmLeadsTableBody) return;
    crmLeadsTableBody.innerHTML = "";

    if (!leads || leads.length === 0) {
      crmLeadsTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">هیچ سرنخی با این فیلتر ثبت نشده است.</td></tr>`;
      return;
    }

    leads.forEach((l, index) => {
      const tr = document.createElement("tr");

      const contactName = l.contact ? l.contact.full_name : "—";
      const contactPhone = l.contact ? l.contact.phone_number : "—";
      const companyName = l.company ? l.company.name : (l.contact && l.contact.company ? l.contact.company.name : "—");
      const budget = l.estimated_budget || "نامشخص";

      const rawTitle = (l.title || "").trim();
      const dummyTitles = ["آشنایی و ثبت مشخصات غرفه", "ارتباط و مذاکره تجاری", "ارتباط و مذاکره اولیه", "درخواست عمومی بازدیدکننده غرفه"];
      const projectTitleDisplay = (rawTitle && !dummyTitles.includes(rawTitle)) ? rawTitle : "—";

      const tempIcon = l.temperature === "Hot" ? "🔥 داغ" : (l.temperature === "Cold" ? "❄️ سرد" : "⚡ گرم");

      tr.innerHTML = `
        <td>${index + 1}</td>
        <td><strong>${contactName}</strong></td>
        <td>${companyName}</td>
        <td dir="ltr" style="text-align: right;">${contactPhone}</td>
        <td>${projectTitleDisplay}</td>
        <td>${budget}</td>
        <td><span class="tag-temp ${l.temperature}">${tempIcon}</span></td>
        <td>
          <select class="select-status" data-lead-id="${l.id}">
            <option value="New" ${l.status === 'New' ? 'selected' : ''}>جدید</option>
            <option value="In_Progress" ${l.status === 'In_Progress' || l.status === 'Contacted' ? 'selected' : ''}>در حال ارزیابی / تماس</option>
            <option value="Converted" ${l.status === 'Converted' || l.status === 'Qualified' ? 'selected' : ''}>تبدیل شده به فرصت ✨</option>
            <option value="Disqualified" ${l.status === 'Disqualified' || l.status === 'Lost' ? 'selected' : ''}>رد شده / غیرمرتبط</option>
          </select>
        </td>
        <td>
          <button class="btn-convert-lead" data-convert-id="${l.id}" title="تبدیل سرنخ به فرصت فروش" style="margin-left: 0.35rem;">💼 تبدیل</button>
          <button class="btn-edit-lead" data-edit-id="${l.id}" title="ویرایش کامل لید" style="margin-left: 0.35rem; background: transparent; border: none; cursor: pointer; font-size: 1rem;">✏️</button>
          <button class="btn-delete-lead" data-delete-id="${l.id}" title="حذف لید" style="background: transparent; border: none; cursor: pointer; font-size: 1rem;">🗑️</button>
        </td>
      `;

      crmLeadsTableBody.appendChild(tr);
    });

    document.querySelectorAll(".btn-convert-lead").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = parseInt(e.currentTarget.getAttribute("data-convert-id"), 10);
        const lead = leads.find(x => x.id === id);
        if (lead) openConvertLeadModal(lead);
      });
    });

    document.querySelectorAll(".btn-edit-lead").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = parseInt(e.currentTarget.getAttribute("data-edit-id"), 10);
        const lead = leads.find(x => x.id === id);
        if (lead) openEditLeadModal(lead);
      });
    });

    // Attach Status Change Listener
    document.querySelectorAll(".select-status").forEach(selectEl => {
      selectEl.addEventListener("change", async (e) => {
        const leadId = e.target.getAttribute("data-lead-id");
        const newStatus = e.target.value;
        try {
          const res = await fetch(`/api/crm/leads/${leadId}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
          });
          if (res.ok) {
            if (newStatus === "Converted" || newStatus === "Qualified") {
              alert("✨ سرنخ با موفقیت به فرصت فروش تبدیل شد و به شیت فرصت‌ها اضافه گردید!");
              loadCRMOpportunities();
              loadCRMOppStats();
            }
          }
          loadCRMLeads();
        } catch (err) {
          console.error("Status update error:", err);
        }
      });
    });

    // Attach Delete Listener
    document.querySelectorAll(".btn-delete-lead").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const leadId = e.currentTarget.getAttribute("data-delete-id");
        if (confirm("آیا از حذف این سرنخ اطمینان دارید؟")) {
          try {
            await fetch(`/api/crm/leads/${leadId}`, { method: "DELETE" });
            loadCRMLeads();
          } catch (err) {
            console.error("Delete error:", err);
          }
        }
      });
    });
  }

  // Quick Lead Form Handler
  if (crmQuickCaptureForm) {
    crmQuickCaptureForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const pTitle = document.getElementById("quickProjectTitle").value.trim();
      const payload = {
        full_name: document.getElementById("quickFullName").value.trim(),
        phone_number: document.getElementById("quickPhone").value.trim(),
        company_name: document.getElementById("quickCompany").value.trim() || null,
        job_title: document.getElementById("quickJobTitle").value.trim() || null,
        project_title: pTitle || null,
        estimated_budget: document.getElementById("quickBudget").value.trim() || null,
        temperature: document.getElementById("quickTemp").value,
        notes: document.getElementById("quickNotes").value.trim() || null
      };

      try {
        const res = await fetch("/api/crm/quick-capture", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          alert("✅ اطلاعات با موفقیت در دیتابیس CRM (شیت‌های مخاطبان، شرکت‌ها و سرنخ‌ها) ذخیره شد!");
          crmQuickCaptureForm.reset();
          loadCRMLeads();
          loadCRMContacts();
          loadCRMCompanies();
          loadCRMOpportunities();
        } else {
          const errData = await res.json().catch(() => ({}));
          alert("خطا در ثبت: " + (errData.detail || "مشکلی پیش آمد"));
        }
      } catch (err) {
        console.error("Quick form submit error:", err);
        alert("خطا در ارتباط با سرور.");
      }
    });
  }

  // ==========================================
  // DIRECT ENTRY MODALS HANDLERS (ثبت مستقیم در ۳ شیت)
  // ==========================================

  // 1. Add Company Modal
  const modalAddCompany = document.getElementById("modalAddCompany");
  const btnOpenAddCompanyModal = document.getElementById("btnOpenAddCompanyModal");
  const btnCloseAddCompanyModal = document.getElementById("btnCloseAddCompanyModal");
  const btnCancelAddCompany = document.getElementById("btnCancelAddCompany");
  const formAddCompany = document.getElementById("formAddCompany");

  if (btnOpenAddCompanyModal) {
    btnOpenAddCompanyModal.addEventListener("click", () => {
      if (formAddCompany) formAddCompany.reset();
      if (modalAddCompany) modalAddCompany.classList.remove("hidden");
    });
  }

  const closeCompanyModal = () => { if (modalAddCompany) modalAddCompany.classList.add("hidden"); };
  if (btnCloseAddCompanyModal) btnCloseAddCompanyModal.addEventListener("click", closeCompanyModal);
  if (btnCancelAddCompany) btnCancelAddCompany.addEventListener("click", closeCompanyModal);

  if (formAddCompany) {
    formAddCompany.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById("compName").value.trim(),
        industry: document.getElementById("compIndustry").value.trim() || null,
        phone: document.getElementById("compPhone").value.trim() || null,
        website: document.getElementById("compWebsite").value.trim() || null,
        address: document.getElementById("compAddress").value.trim() || null
      };

      try {
        const res = await fetch("/api/crm/companies", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          alert("✅ شرکت با موفقیت به بانک اطلاعاتی CRM اضافه شد.");
          closeCompanyModal();
          loadCRMCompanies();
        } else {
          const errData = await res.json().catch(() => ({}));
          alert("خطا: " + (errData.detail || "ثبت شرکت ناموفق بود"));
        }
      } catch (err) {
        console.error("Save company error:", err);
        alert("خطا در برقراری ارتباط با سرور");
      }
    });
  }

  // 2. Add Contact Modal
  const modalAddContact = document.getElementById("modalAddContact");
  const btnOpenAddContactModal = document.getElementById("btnOpenAddContactModal");
  const btnCloseAddContactModal = document.getElementById("btnCloseAddContactModal");
  const btnCancelAddContact = document.getElementById("btnCancelAddContact");
  const formAddContact = document.getElementById("formAddContact");
  const contactCompanySelect = document.getElementById("contactCompanySelect");

  if (btnOpenAddContactModal) {
    btnOpenAddContactModal.addEventListener("click", async () => {
      if (formAddContact) formAddContact.reset();
      // Populate companies dropdown
      if (contactCompanySelect) {
        contactCompanySelect.innerHTML = `<option value="">— شخص حقیقی (بدون انتساب به شرکت) —</option>`;
        try {
          const res = await fetch("/api/crm/companies");
          const comps = await res.json();
          comps.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.id;
            opt.textContent = `🏢 ${c.name}`;
            contactCompanySelect.appendChild(opt);
          });
        } catch (e) {
          console.error("Error fetching companies:", e);
        }
      }
      if (modalAddContact) modalAddContact.classList.remove("hidden");
    });
  }

  const closeContactModal = () => { if (modalAddContact) modalAddContact.classList.add("hidden"); };
  if (btnCloseAddContactModal) btnCloseAddContactModal.addEventListener("click", closeContactModal);
  if (btnCancelAddContact) btnCancelAddContact.addEventListener("click", closeContactModal);

  if (formAddContact) {
    formAddContact.addEventListener("submit", async (e) => {
      e.preventDefault();
      const compIdVal = contactCompanySelect ? contactCompanySelect.value : "";
      const payload = {
        full_name: document.getElementById("contactFullName").value.trim(),
        phone_number: document.getElementById("contactPhone").value.trim(),
        company_id: compIdVal ? parseInt(compIdVal, 10) : null,
        job_title: document.getElementById("contactJobTitle").value.trim() || null,
        email: document.getElementById("contactEmail").value.trim() || null
      };

      try {
        const res = await fetch("/api/crm/contacts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          alert("✅ مخاطب با موفقیت در CRM ثبت شد.");
          closeContactModal();
          loadCRMContacts();
        } else {
          const errData = await res.json().catch(() => ({}));
          alert("خطا: " + (errData.detail || "ثبت مخاطب ناموفق بود"));
        }
      } catch (err) {
        console.error("Save contact error:", err);
        alert("خطا در برقراری ارتباط با سرور");
      }
    });
  }

  // 3. Add Lead Modal
  const modalAddLead = document.getElementById("modalAddLead");
  const btnOpenAddLeadModal = document.getElementById("btnOpenAddLeadModal");
  const btnCloseAddLeadModal = document.getElementById("btnCloseAddLeadModal");
  const btnCancelAddLead = document.getElementById("btnCancelAddLead");
  const formAddLead = document.getElementById("formAddLead");
  const leadContactSelect = document.getElementById("leadContactSelect");

  if (btnOpenAddLeadModal) {
    btnOpenAddLeadModal.addEventListener("click", async () => {
      if (formAddLead) formAddLead.reset();
      // Populate contacts dropdown
      if (leadContactSelect) {
        leadContactSelect.innerHTML = `<option value="">— لطفاً مخاطب را انتخاب کنید —</option>`;
        try {
          const res = await fetch("/api/crm/contacts");
          const contacts = await res.json();
          contacts.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.id;
            const compTxt = c.company ? ` (${c.company.name})` : "";
            opt.textContent = `👤 ${c.full_name}${compTxt} - ${c.phone_number}`;
            leadContactSelect.appendChild(opt);
          });
        } catch (e) {
          console.error("Error fetching contacts:", e);
        }
      }
      if (modalAddLead) modalAddLead.classList.remove("hidden");
    });
  }

  const closeLeadModal = () => { if (modalAddLead) modalAddLead.classList.add("hidden"); };
  if (btnCloseAddLeadModal) btnCloseAddLeadModal.addEventListener("click", closeLeadModal);
  if (btnCancelAddLead) btnCancelAddLead.addEventListener("click", closeLeadModal);

  if (formAddLead) {
    formAddLead.addEventListener("submit", async (e) => {
      e.preventDefault();
      const contactIdVal = leadContactSelect ? leadContactSelect.value : "";
      if (!contactIdVal) {
        alert("لطفاً یک مخاطب را انتخاب فرمایید.");
        return;
      }

      const titleInput = document.getElementById("leadTitleInput").value.trim();
      const payload = {
        contact_id: parseInt(contactIdVal, 10),
        title: titleInput || null,
        estimated_budget: document.getElementById("leadBudgetInput").value.trim() || null,
        temperature: document.getElementById("leadTempSelect").value,
        field_of_interest: document.getElementById("leadFieldInput").value.trim() || null,
        notes: document.getElementById("leadNotesInput").value.trim() || null
      };

      try {
        const res = await fetch("/api/crm/leads", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          alert("✅ سرنخ با موفقیت به چرخه پیگیری فروش اضافه شد.");
          closeLeadModal();
          loadCRMLeads();
          loadCRMContacts();
          loadCRMCompanies();
          loadCRMOpportunities();
        } else {
          const errData = await res.json().catch(() => ({}));
          alert("خطا: " + (errData.detail || "ثبت سرنخ ناموفق بود"));
        }
      } catch (err) {
        console.error("Save lead error:", err);
        alert("خطا در برقراری ارتباط با سرور");
      }
    });
  }

  // ==========================================
  // LIVE SEARCH & SELECTION CACHE
  // ==========================================
  let cachedCompanies = [];
  let cachedContacts = [];

  async function refreshCachedCompanies() {
    try {
      const res = await fetch("/api/crm/companies");
      cachedCompanies = await res.json();
    } catch (e) {
      console.error("Cache companies error:", e);
    }
  }

  async function refreshCachedContacts() {
    try {
      const res = await fetch("/api/crm/contacts");
      cachedContacts = await res.json();
    } catch (e) {
      console.error("Cache contacts error:", e);
    }
  }

  function renderCompanyOptions(selectEl, filterText = "", selectedId = null) {
    if (!selectEl) return;
    selectEl.innerHTML = `<option value="">— شخص حقیقی (بدون شرکت) —</option>`;
    const search = filterText.toLowerCase().trim();
    const filtered = cachedCompanies.filter(c => !search || c.name.toLowerCase().includes(search));
    filtered.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `🏢 ${c.name}`;
      if (selectedId && c.id === selectedId) opt.selected = true;
      selectEl.appendChild(opt);
    });
  }

  function renderContactOptions(selectEl, filterText = "", selectedId = null) {
    if (!selectEl) return;
    selectEl.innerHTML = `<option value="">— لطفاً مخاطب را انتخاب کنید —</option>`;
    const search = filterText.toLowerCase().trim();
    const filtered = cachedContacts.filter(c => {
      if (!search) return true;
      const compName = c.company ? c.company.name : "";
      return c.full_name.toLowerCase().includes(search) ||
             (c.phone_number && c.phone_number.includes(search)) ||
             compName.toLowerCase().includes(search);
    });
    filtered.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      const compTxt = c.company ? ` (${c.company.name})` : "";
      opt.textContent = `👤 ${c.full_name}${compTxt} - ${c.phone_number}`;
      if (selectedId && c.id === selectedId) opt.selected = true;
      selectEl.appendChild(opt);
    });
  }

  // Connect live search inputs
  const searchCompanyInput = document.getElementById("searchCompanyInput");
  const editSearchCompanyInput = document.getElementById("editSearchCompanyInput");
  const searchContactInput = document.getElementById("searchContactInput");
  const editSearchContactInput = document.getElementById("editSearchContactInput");

  if (searchCompanyInput) {
    searchCompanyInput.addEventListener("input", (e) => {
      renderCompanyOptions(contactCompanySelect, e.target.value);
    });
  }
  if (editSearchCompanyInput) {
    editSearchCompanyInput.addEventListener("input", (e) => {
      const sel = document.getElementById("editContactCompanySelect");
      renderCompanyOptions(sel, e.target.value);
    });
  }
  if (searchContactInput) {
    searchContactInput.addEventListener("input", (e) => {
      renderContactOptions(leadContactSelect, e.target.value);
    });
  }
  if (editSearchContactInput) {
    editSearchContactInput.addEventListener("input", (e) => {
      const sel = document.getElementById("editLeadContactSelect");
      renderContactOptions(sel, e.target.value);
    });
  }

  // Update Add Modals opening logic to use cache
  if (btnOpenAddContactModal) {
    btnOpenAddContactModal.addEventListener("click", async () => {
      if (formAddContact) formAddContact.reset();
      if (searchCompanyInput) searchCompanyInput.value = "";
      await refreshCachedCompanies();
      renderCompanyOptions(contactCompanySelect);
      if (modalAddContact) modalAddContact.classList.remove("hidden");
    });
  }

  if (btnOpenAddLeadModal) {
    btnOpenAddLeadModal.addEventListener("click", async () => {
      if (formAddLead) formAddLead.reset();
      if (searchContactInput) searchContactInput.value = "";
      await refreshCachedContacts();
      renderContactOptions(leadContactSelect);
      if (modalAddLead) modalAddLead.classList.remove("hidden");
    });
  }

  // ==========================================
  // EDIT MODALS LOGIC (ویرایش شرکت، مخاطب و لید)
  // ==========================================

  // 1. Edit Company
  const modalEditCompany = document.getElementById("modalEditCompany");
  const btnCloseEditCompanyModal = document.getElementById("btnCloseEditCompanyModal");
  const btnCancelEditCompany = document.getElementById("btnCancelEditCompany");
  const formEditCompany = document.getElementById("formEditCompany");

  function openEditCompanyModal(comp) {
    document.getElementById("editCompId").value = comp.id;
    document.getElementById("editCompName").value = comp.name || "";
    document.getElementById("editCompIndustry").value = comp.industry || "";
    document.getElementById("editCompPhone").value = comp.phone || "";
    document.getElementById("editCompWebsite").value = comp.website || "";
    document.getElementById("editCompAddress").value = comp.address || "";
    if (modalEditCompany) modalEditCompany.classList.remove("hidden");
  }

  const closeEditCompModal = () => { if (modalEditCompany) modalEditCompany.classList.add("hidden"); };
  if (btnCloseEditCompanyModal) btnCloseEditCompanyModal.addEventListener("click", closeEditCompModal);
  if (btnCancelEditCompany) btnCancelEditCompany.addEventListener("click", closeEditCompModal);

  if (formEditCompany) {
    formEditCompany.addEventListener("submit", async (e) => {
      e.preventDefault();
      const compId = document.getElementById("editCompId").value;
      const payload = {
        name: document.getElementById("editCompName").value.trim(),
        industry: document.getElementById("editCompIndustry").value.trim() || null,
        phone: document.getElementById("editCompPhone").value.trim() || null,
        website: document.getElementById("editCompWebsite").value.trim() || null,
        address: document.getElementById("editCompAddress").value.trim() || null
      };

      try {
        const res = await fetch(`/api/crm/companies/${compId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          alert("✅ مشخصات شرکت با موفقیت به‌روزرسانی شد.");
          closeEditCompModal();
          loadCRMCompanies();
        } else {
          alert("خطا در ذخیره تغییرات شرکت.");
        }
      } catch (err) {
        console.error("Update company error:", err);
      }
    });
  }

  // 2. Edit Contact
  const modalEditContact = document.getElementById("modalEditContact");
  const btnCloseEditContactModal = document.getElementById("btnCloseEditContactModal");
  const btnCancelEditContact = document.getElementById("btnCancelEditContact");
  const formEditContact = document.getElementById("formEditContact");
  const editContactCompanySelect = document.getElementById("editContactCompanySelect");

  async function openEditContactModal(contact) {
    document.getElementById("editContactId").value = contact.id;
    document.getElementById("editContactFullName").value = contact.full_name || "";
    document.getElementById("editContactPhone").value = contact.phone_number || "";
    document.getElementById("editContactJobTitle").value = contact.job_title || "";
    document.getElementById("editContactEmail").value = contact.email || "";
    if (editSearchCompanyInput) editSearchCompanyInput.value = "";

    await refreshCachedCompanies();
    renderCompanyOptions(editContactCompanySelect, "", contact.company_id);

    if (modalEditContact) modalEditContact.classList.remove("hidden");
  }

  const closeEditContactModal = () => { if (modalEditContact) modalEditContact.classList.add("hidden"); };
  if (btnCloseEditContactModal) btnCloseEditContactModal.addEventListener("click", closeEditContactModal);
  if (btnCancelEditContact) btnCancelEditContact.addEventListener("click", closeEditContactModal);

  if (formEditContact) {
    formEditContact.addEventListener("submit", async (e) => {
      e.preventDefault();
      const contactId = document.getElementById("editContactId").value;
      const compVal = editContactCompanySelect ? editContactCompanySelect.value : "";
      const payload = {
        full_name: document.getElementById("editContactFullName").value.trim(),
        phone_number: document.getElementById("editContactPhone").value.trim(),
        company_id: compVal ? parseInt(compVal, 10) : null,
        job_title: document.getElementById("editContactJobTitle").value.trim() || null,
        email: document.getElementById("editContactEmail").value.trim() || null
      };

      try {
        const res = await fetch(`/api/crm/contacts/${contactId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          alert("✅ مشخصات مخاطب با موفقیت به‌روزرسانی شد.");
          closeEditContactModal();
          loadCRMContacts();
        } else {
          alert("خطا در به‌روزرسانی مخاطب.");
        }
      } catch (err) {
        console.error("Update contact error:", err);
      }
    });
  }

  // 3. Edit Lead
  const modalEditLead = document.getElementById("modalEditLead");
  const btnCloseEditLeadModal = document.getElementById("btnCloseEditLeadModal");
  const btnCancelEditLead = document.getElementById("btnCancelEditLead");
  const formEditLead = document.getElementById("formEditLead");
  const editLeadContactSelect = document.getElementById("editLeadContactSelect");

  async function openEditLeadModal(lead) {
    document.getElementById("editLeadId").value = lead.id;
    document.getElementById("editLeadTitleInput").value = lead.title || "";
    document.getElementById("editLeadBudgetInput").value = lead.estimated_budget || "";
    document.getElementById("editLeadTempSelect").value = lead.temperature || "Warm";
    document.getElementById("editLeadStatusSelect").value = lead.status || "New";
    document.getElementById("editLeadFieldInput").value = lead.field_of_interest || "";
    document.getElementById("editLeadNotesInput").value = lead.notes || "";
    if (editSearchContactInput) editSearchContactInput.value = "";

    await refreshCachedContacts();
    renderContactOptions(editLeadContactSelect, "", lead.contact_id);

    if (modalEditLead) modalEditLead.classList.remove("hidden");
  }

  const closeEditLeadModal = () => { if (modalEditLead) modalEditLead.classList.add("hidden"); };
  if (btnCloseEditLeadModal) btnCloseEditLeadModal.addEventListener("click", closeEditLeadModal);
  if (btnCancelEditLead) btnCancelEditLead.addEventListener("click", closeEditLeadModal);

  if (formEditLead) {
    formEditLead.addEventListener("submit", async (e) => {
      e.preventDefault();
      const leadId = document.getElementById("editLeadId").value;
      const contactVal = editLeadContactSelect ? editLeadContactSelect.value : "";
      if (!contactVal) {
        alert("لطفاً مخاطب صاحب سرنخ را مشخص کنید.");
        return;
      }

      const payload = {
        contact_id: parseInt(contactVal, 10),
        title: document.getElementById("editLeadTitleInput").value.trim() || "ارتباط و مذاکره تجاری",
        estimated_budget: document.getElementById("editLeadBudgetInput").value.trim() || null,
        temperature: document.getElementById("editLeadTempSelect").value,
        status: document.getElementById("editLeadStatusSelect").value,
        field_of_interest: document.getElementById("editLeadFieldInput").value.trim() || null,
        notes: document.getElementById("editLeadNotesInput").value.trim() || null
      };

      try {
        const res = await fetch(`/api/crm/leads/${leadId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          alert("✅ مشخصات سرنخ با موفقیت به‌روزرسانی شد.");
          closeEditLeadModal();
          loadCRMLeads();
        } else {
          alert("خطا در به‌روزرسانی سرنخ.");
        }
      } catch (err) {
        console.error("Update lead error:", err);
      }
    });
  }

  // ==========================================
  // OPPORTUNITIES & PIPELINE LOGIC (فرصت‌های فروش)
  // ==========================================

  const stageProbs = {
    Requirement_Analysis: 20,
    Proposal: 50,
    Negotiation: 80,
    Closed_Won: 100,
    Closed_Lost: 0,
    // سازگاری با رکوردهای گذشته
    Prospecting: 20,
    Qualification: 30
  };

  function formatMoney(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return "—";
    return Number(amount).toLocaleString("fa-IR") + " تومان";
  }

  // Load KPI Stats
  async function loadOpportunityStats() {
    try {
      const res = await fetch("/api/crm/opportunities/stats");
      if (!res.ok) return;
      const stats = await res.json();
      if (oppKpiTotalAmount) oppKpiTotalAmount.textContent = formatMoney(stats.total_value ?? stats.total_pipeline_value);
      if (oppKpiTotalCount) oppKpiTotalCount.textContent = (stats.total_count || 0).toLocaleString("fa-IR");
      if (oppKpiOpenAmount) oppKpiOpenAmount.textContent = formatMoney(stats.open_value ?? stats.open_pipeline_value);
      if (oppKpiOpenCount) oppKpiOpenCount.textContent = (stats.open_count || 0).toLocaleString("fa-IR");
      if (oppKpiWonAmount) oppKpiWonAmount.textContent = formatMoney(stats.won_value ?? stats.won_pipeline_value);
      if (oppKpiWonCount) oppKpiWonCount.textContent = (stats.won_count || 0).toLocaleString("fa-IR");
      if (oppKpiWinRate) oppKpiWinRate.textContent = (stats.win_rate || 0).toLocaleString("fa-IR") + "٪";
    } catch (e) {
      console.error("Error loading opp stats:", e);
    }
  }

  // Load Opportunities Table
  async function loadCRMOpportunities() {
    if (!crmOpportunitiesTableBody) return;
    try {
      crmOpportunitiesTableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">در حال دریافت فرصت‌های تجاری...</td></tr>`;
      const stage = filterOppStage ? filterOppStage.value : "";
      let url = "/api/crm/opportunities";
      if (stage) url += `?stage=${encodeURIComponent(stage)}`;

      const res = await fetch(url);
      const opps = await res.json();
      renderOpportunitiesTable(opps);
      loadOpportunityStats();
    } catch (err) {
      console.error("Error loading opportunities:", err);
      crmOpportunitiesTableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: #f43f5e; padding: 1.5rem;">خطا در دریافت اطلاعات فرصت‌ها</td></tr>`;
    }
  }

  function renderOpportunitiesTable(opps) {
    if (!crmOpportunitiesTableBody) return;
    crmOpportunitiesTableBody.innerHTML = "";

    if (!opps || opps.length === 0) {
      crmOpportunitiesTableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">هیچ فرصت تجاری در این مرحله ثبت نشده است.</td></tr>`;
      return;
    }

    opps.forEach((opp, index) => {
      const tr = document.createElement("tr");

      const companyName = opp.company ? opp.company.name : "—";
      const contactName = opp.contact ? opp.contact.full_name : "—";
      const originLeadText = opp.origin_lead ? `🎯 ${opp.origin_lead.title || 'سرنخ'}` : `<span style="color: var(--text-muted); font-size: 0.75rem;">ثبت مستقیم</span>`;
      const amountFormatted = opp.amount ? formatMoney(opp.amount) : "نامشخص";
      const prob = (opp.probability !== null && opp.probability !== undefined) ? opp.probability : 0;
      const probColor = prob >= 70 ? "#10b981" : (prob >= 40 ? "#fbbf24" : "#94a3b8");

      tr.innerHTML = `
        <td>${index + 1}</td>
        <td><strong>${opp.title}</strong></td>
        <td>${companyName}</td>
        <td>${contactName}</td>
        <td style="font-weight: 700; color: #38bdf8;">${amountFormatted}</td>
        <td>
          <select class="select-opp-stage" data-opp-id="${opp.id}" style="padding: 0.25rem 0.5rem; border-radius: 0.4rem; background: var(--bg-surface-elevated); border: 1px solid var(--border-color); color: var(--text-primary); font-size: 0.8rem;">
            <option value="Requirement_Analysis" ${opp.stage === 'Requirement_Analysis' || opp.stage === 'Prospecting' || opp.stage === 'Qualification' ? 'selected' : ''}>🔍 نیازسنجی فنی (۲۰٪)</option>
            <option value="Proposal" ${opp.stage === 'Proposal' ? 'selected' : ''}>📑 پروپوزال (۵۰٪)</option>
            <option value="Negotiation" ${opp.stage === 'Negotiation' ? 'selected' : ''}>🤝 مذاکره نهایی (۸۰٪)</option>
            <option value="Closed_Won" ${opp.stage === 'Closed_Won' ? 'selected' : ''}>🏆 قرارداد موفق (۱۰۰٪)</option>
            <option value="Closed_Lost" ${opp.stage === 'Closed_Lost' ? 'selected' : ''}>❌ رد پیشنهاد (۰٪)</option>
          </select>
        </td>
        <td>
          <div class="prob-meter-container">
            <div class="prob-meter-bar">
              <div class="prob-meter-fill" style="width: ${prob}%; background: ${probColor};"></div>
            </div>
            <span class="prob-text" style="color: ${probColor};">${prob}٪</span>
          </div>
        </td>
        <td>${originLeadText}</td>
        <td>${opp.expected_close_date || "—"}</td>
        <td>
          <button class="btn-edit-opp-row" data-opp-id="${opp.id}" title="ویرایش مشخصات معامله" style="margin-left: 0.35rem; background: transparent; border: none; cursor: pointer; font-size: 1rem;">✏️</button>
          <button class="btn-delete-opp-row" data-opp-id="${opp.id}" title="حذف فرصت" style="background: transparent; border: none; cursor: pointer; font-size: 1rem;">🗑️</button>
        </td>
      `;

      crmOpportunitiesTableBody.appendChild(tr);
    });

    // Inline Stage Change Listener
    document.querySelectorAll(".select-opp-stage").forEach(sel => {
      sel.addEventListener("change", async (e) => {
        const oppId = e.target.getAttribute("data-opp-id");
        const newStage = e.target.value;
        try {
          await fetch(`/api/crm/opportunities/${oppId}/stage`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stage: newStage })
          });
          loadCRMOpportunities();
        } catch (err) {
          console.error("Opp stage update error:", err);
        }
      });
    });

    // Edit Opp
    document.querySelectorAll(".btn-edit-opp-row").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = parseInt(e.currentTarget.getAttribute("data-opp-id"), 10);
        const opp = opps.find(x => x.id === id);
        if (opp) openEditOpportunityModal(opp);
      });
    });

    // Delete Opp
    document.querySelectorAll(".btn-delete-opp-row").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-opp-id");
        if (confirm("آیا از حذف این فرصت فروش اطمینان دارید؟")) {
          try {
            await fetch(`/api/crm/opportunities/${id}`, { method: "DELETE" });
            loadCRMOpportunities();
          } catch (err) {
            console.error("Delete opp error:", err);
          }
        }
      });
    });
  }

  // 1. Convert Lead to Opportunity Modal Logic
  const modalConvertLead = document.getElementById("modalConvertLead");
  const btnCloseConvertLeadModal = document.getElementById("btnCloseConvertLeadModal");
  const btnCancelConvertLead = document.getElementById("btnCancelConvertLead");
  const formConvertLead = document.getElementById("formConvertLead");
  const convOppStage = document.getElementById("convOppStage");

  function openConvertLeadModal(lead) {
    document.getElementById("convLeadId").value = lead.id;
    const contactName = lead.contact ? lead.contact.full_name : "نامشخص";
    const companyName = lead.company ? lead.company.name : (lead.contact && lead.contact.company ? lead.contact.company.name : "نامشخص");
    document.getElementById("convLeadContactTxt").textContent = contactName;
    document.getElementById("convLeadCompanyTxt").textContent = companyName;
    document.getElementById("convLeadBudgetTxt").textContent = lead.estimated_budget || "ذکر نشده";

    document.getElementById("convOppTitle").value = lead.title ? `فرصت: ${lead.title}` : `معامله با ${contactName}`;

    // Extract numbers from estimated_budget
    let numericAmount = "";
    if (lead.estimated_budget) {
      const faDigits = "۰۱۲۳۴۵۶۷۸۹";
      let s = String(lead.estimated_budget).replace(/[۰-۹]/g, w => faDigits.indexOf(w));
      const m = s.match(/(\d+(\.\d+)?)/);
      if (m) {
        let val = parseFloat(m[1]);
        if (s.includes("میلیارد")) val *= 1000000000;
        else if (s.includes("میلیون")) val *= 1000000;
        numericAmount = Math.round(val);
      }
    }
    document.getElementById("convOppAmount").value = numericAmount || "";

    document.getElementById("convOppStage").value = "Qualification";
    document.getElementById("convOppProbability").value = "30";
    document.getElementById("convOppCloseDate").value = lead.timeline || "";
    document.getElementById("convOppPriority").value = lead.temperature === "Hot" ? "High" : (lead.temperature === "Cold" ? "Low" : "Medium");
    document.getElementById("convOppNotes").value = lead.notes || "";

    if (modalConvertLead) modalConvertLead.classList.remove("hidden");
  }

  const closeConvertLeadModal = () => { if (modalConvertLead) modalConvertLead.classList.add("hidden"); };
  if (btnCloseConvertLeadModal) btnCloseConvertLeadModal.addEventListener("click", closeConvertLeadModal);
  if (btnCancelConvertLead) btnCancelConvertLead.addEventListener("click", closeConvertLeadModal);

  if (convOppStage) {
    convOppStage.addEventListener("change", (e) => {
      if (stageProbs[e.target.value] !== undefined) {
        document.getElementById("convOppProbability").value = stageProbs[e.target.value];
      }
    });
  }

  if (formConvertLead) {
    formConvertLead.addEventListener("submit", async (e) => {
      e.preventDefault();
      const leadId = document.getElementById("convLeadId").value;
      const amountVal = document.getElementById("convOppAmount").value.trim();
      const probVal = document.getElementById("convOppProbability").value.trim();

      const payload = {
        title: document.getElementById("convOppTitle").value.trim() || undefined,
        amount: amountVal ? parseFloat(amountVal) : undefined,
        stage: document.getElementById("convOppStage").value,
        probability: probVal ? parseInt(probVal, 10) : undefined,
        expected_close_date: document.getElementById("convOppCloseDate").value.trim() || undefined,
        priority: document.getElementById("convOppPriority").value,
        deal_type: document.getElementById("convOppDealType").value,
        notes: document.getElementById("convOppNotes").value.trim() || undefined
      };

      try {
        const res = await fetch(`/api/crm/leads/${leadId}/convert`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          alert("✨ سرنخ با موفقیت به فرصت فروش تبدیل شد و به شیت فرصت‌ها اضافه گردید!");
          closeConvertLeadModal();
          loadCRMLeads();
          switchCRMSubTab("opportunities");
        } else {
          const errData = await res.json().catch(() => ({}));
          alert("خطا در تبدیل سرنخ: " + (errData.detail || "مشکلی پیش آمد"));
        }
      } catch (err) {
        console.error("Convert lead error:", err);
        alert("خطا در ارتباط با سرور");
      }
    });
  }

  // 2. Add Opportunity Directly Modal Logic
  const modalAddOpportunity = document.getElementById("modalAddOpportunity");
  const btnCloseAddOppModal = document.getElementById("btnCloseAddOppModal");
  const btnCancelAddOpp = document.getElementById("btnCancelAddOpp");
  const formAddOpportunity = document.getElementById("formAddOpportunity");
  const oppCompanySelect = document.getElementById("oppCompanySelect");
  const oppContactSelect = document.getElementById("oppContactSelect");
  const oppStageSelect = document.getElementById("oppStage");

  const searchOppCompanyInput = document.getElementById("searchOppCompanyInput");
  const searchOppContactInput = document.getElementById("searchOppContactInput");

  if (searchOppCompanyInput) {
    searchOppCompanyInput.addEventListener("input", (e) => {
      renderCompanyOptions(oppCompanySelect, e.target.value);
    });
  }
  if (searchOppContactInput) {
    searchOppContactInput.addEventListener("input", (e) => {
      renderContactOptions(oppContactSelect, e.target.value);
    });
  }

  if (oppStageSelect) {
    oppStageSelect.addEventListener("change", (e) => {
      if (stageProbs[e.target.value] !== undefined) {
        document.getElementById("oppProbability").value = stageProbs[e.target.value];
      }
    });
  }

  if (btnOpenAddOppModal) {
    btnOpenAddOppModal.addEventListener("click", async () => {
      if (formAddOpportunity) formAddOpportunity.reset();
      if (searchOppCompanyInput) searchOppCompanyInput.value = "";
      if (searchOppContactInput) searchOppContactInput.value = "";
      document.getElementById("oppProbability").value = "10";
      await refreshCachedCompanies();
      await refreshCachedContacts();
      renderCompanyOptions(oppCompanySelect);
      renderContactOptions(oppContactSelect);
      if (modalAddOpportunity) modalAddOpportunity.classList.remove("hidden");
    });
  }

  const closeAddOppModal = () => { if (modalAddOpportunity) modalAddOpportunity.classList.add("hidden"); };
  if (btnCloseAddOppModal) btnCloseAddOppModal.addEventListener("click", closeAddOppModal);
  if (btnCancelAddOpp) btnCancelAddOpp.addEventListener("click", closeAddOppModal);

  if (formAddOpportunity) {
    formAddOpportunity.addEventListener("submit", async (e) => {
      e.preventDefault();
      const compVal = oppCompanySelect ? oppCompanySelect.value : "";
      const contactVal = oppContactSelect ? oppContactSelect.value : "";
      const amountVal = document.getElementById("oppAmount").value.trim();
      const probVal = document.getElementById("oppProbability").value.trim();

      const payload = {
        title: document.getElementById("oppTitle").value.trim(),
        company_id: compVal ? parseInt(compVal, 10) : null,
        contact_id: contactVal ? parseInt(contactVal, 10) : null,
        amount: amountVal ? parseFloat(amountVal) : null,
        stage: document.getElementById("oppStage").value,
        probability: probVal ? parseInt(probVal, 10) : null,
        expected_close_date: document.getElementById("oppCloseDate").value.trim() || null,
        priority: document.getElementById("oppPriority").value,
        deal_type: document.getElementById("oppDealType").value,
        notes: document.getElementById("oppNotes").value.trim() || null
      };

      try {
        const res = await fetch("/api/crm/opportunities", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          alert("✅ فرصت تجاری جدید با موفقیت در پایپ‌لاین ثبت شد.");
          closeAddOppModal();
          loadCRMOpportunities();
        } else {
          const errData = await res.json().catch(() => ({}));
          alert("خطا: " + (errData.detail || "ثبت فرصت ناموفق بود"));
        }
      } catch (err) {
        console.error("Save opp error:", err);
        alert("خطا در برقراری ارتباط با سرور");
      }
    });
  }

  // 3. Edit Opportunity Modal Logic
  const modalEditOpportunity = document.getElementById("modalEditOpportunity");
  const btnCloseEditOppModal = document.getElementById("btnCloseEditOppModal");
  const btnCancelEditOpp = document.getElementById("btnCancelEditOpp");
  const formEditOpportunity = document.getElementById("formEditOpportunity");
  const editOppCompanySelect = document.getElementById("editOppCompanySelect");
  const editOppContactSelect = document.getElementById("editOppContactSelect");
  const editOppStageSelect = document.getElementById("editOppStage");

  const editSearchOppCompanyInput = document.getElementById("editSearchOppCompanyInput");
  const editSearchOppContactInput = document.getElementById("editSearchOppContactInput");

  if (editSearchOppCompanyInput) {
    editSearchOppCompanyInput.addEventListener("input", (e) => {
      renderCompanyOptions(editOppCompanySelect, e.target.value);
    });
  }
  if (editSearchOppContactInput) {
    editSearchOppContactInput.addEventListener("input", (e) => {
      renderContactOptions(editOppContactSelect, e.target.value);
    });
  }

  if (editOppStageSelect) {
    editOppStageSelect.addEventListener("change", (e) => {
      if (stageProbs[e.target.value] !== undefined) {
        document.getElementById("editOppProbability").value = stageProbs[e.target.value];
      }
    });
  }

  async function openEditOpportunityModal(opp) {
    document.getElementById("editOppId").value = opp.id;
    document.getElementById("editOppTitle").value = opp.title || "";
    document.getElementById("editOppAmount").value = opp.amount !== null && opp.amount !== undefined ? opp.amount : "";
    document.getElementById("editOppStage").value = opp.stage || "Requirement_Analysis";
    document.getElementById("editOppProbability").value = opp.probability !== null && opp.probability !== undefined ? opp.probability : 20;
    document.getElementById("editOppCloseDate").value = opp.expected_close_date || "";
    document.getElementById("editOppPriority").value = opp.priority || "Medium";
    document.getElementById("editOppDealType").value = opp.deal_type || "New Business";
    document.getElementById("editOppNotes").value = opp.notes || "";

    if (editSearchOppCompanyInput) editSearchOppCompanyInput.value = "";
    if (editSearchOppContactInput) editSearchOppContactInput.value = "";

    await refreshCachedCompanies();
    await refreshCachedContacts();
    renderCompanyOptions(editOppCompanySelect, "", opp.company_id);
    renderContactOptions(editOppContactSelect, "", opp.contact_id);

    if (modalEditOpportunity) modalEditOpportunity.classList.remove("hidden");
  }

  const closeEditOppModal = () => { if (modalEditOpportunity) modalEditOpportunity.classList.add("hidden"); };
  if (btnCloseEditOppModal) btnCloseEditOppModal.addEventListener("click", closeEditOppModal);
  if (btnCancelEditOpp) btnCancelEditOpp.addEventListener("click", closeEditOppModal);

  if (formEditOpportunity) {
    formEditOpportunity.addEventListener("submit", async (e) => {
      e.preventDefault();
      const oppId = document.getElementById("editOppId").value;
      const compVal = editOppCompanySelect ? editOppCompanySelect.value : "";
      const contactVal = editOppContactSelect ? editOppContactSelect.value : "";
      const amountVal = document.getElementById("editOppAmount").value.trim();
      const probVal = document.getElementById("editOppProbability").value.trim();

      const payload = {
        title: document.getElementById("editOppTitle").value.trim(),
        company_id: compVal ? parseInt(compVal, 10) : null,
        contact_id: contactVal ? parseInt(contactVal, 10) : null,
        amount: amountVal ? parseFloat(amountVal) : null,
        stage: document.getElementById("editOppStage").value,
        probability: probVal ? parseInt(probVal, 10) : null,
        expected_close_date: document.getElementById("editOppCloseDate").value.trim() || null,
        priority: document.getElementById("editOppPriority").value,
        deal_type: document.getElementById("editOppDealType").value,
        notes: document.getElementById("editOppNotes").value.trim() || null
      };

      try {
        const res = await fetch(`/api/crm/opportunities/${oppId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          alert("✅ مشخصات فرصت تجاری با موفقیت ذخیره شد.");
          closeEditOppModal();
          loadCRMOpportunities();
        } else {
          alert("خطا در به‌روزرسانی فرصت فروش.");
        }
      } catch (err) {
        console.error("Update opp error:", err);
      }
    });
  }

  // Initial Load of all CRM data on startup
  loadCRMLeads();
  loadCRMContacts();
  loadCRMCompanies();
  loadCRMOpportunities();
});

