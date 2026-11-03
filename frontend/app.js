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

  let isRecording = false;
  let mediaRecorder = null;
  let audioChunks = [];
  let totalMessages = 0;

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
    messagesContainer.innerHTML = "";
    totalMessages = 0;
    (history || []).forEach((msg, idx) => {
      const audioToAttach = (idx === 0 && msg.role === "assistant") ? greetingAudio : "";
      appendMessage(msg.role, msg.content, false, audioToAttach);
    });
  }

  function appendMessage(role, text, isPlaying = false, audioBase64 = "") {
    if (!text) return;
    totalMessages++;
    messageCountBadge.textContent = `${totalMessages} پیام`;

    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;

    const senderHeader = document.createElement("div");
    senderHeader.className = "bubble-sender";

    if (role === "assistant") {
      senderHeader.innerHTML = `<span>🎙️ غرفه‌یار</span> ${isPlaying ? '<div class="playing-wave"><span></span><span></span><span></span></div>' : ''}`;
    } else {
      senderHeader.innerHTML = `<span>👤 بازدیدکننده</span>`;
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
      listenBtn.title = "پخش صدای غرفه‌یار";
      listenBtn.onclick = (e) => {
        e.stopPropagation();
        playTTS(audioBase64);
      };
      audioRow.appendChild(listenBtn);
      bubble.appendChild(audioRow);
    }

    messagesContainer.appendChild(bubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return bubble;
  }

  function updateFormFields(formData, updatedFields = {}) {
    const fields = [
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

    let filledCount = 0;

    fields.forEach(f => {
      const valElement = document.getElementById(`val-${f}`);
      const cardElement = document.getElementById(`field-${f}`);
      if (!valElement || !cardElement) return;

      const val = formData[f];

      if (val && String(val).trim()) {
        valElement.textContent = val;
        valElement.classList.remove("empty");
        filledCount++;

        // If this field was updated in this turn, trigger animation
        if (updatedFields[f]) {
          cardElement.classList.remove("highlight");
          void cardElement.offsetWidth; // trigger reflow
          cardElement.classList.add("highlight");
        }
      } else {
        if (f === "full_name" || f === "phone_number") {
          valElement.textContent = "در انتظار دریافت...";
        } else if (f === "project_description") {
          valElement.textContent = "هنوز درخواستی مطرح نشده است...";
        } else {
          valElement.textContent = "—";
        }
        valElement.classList.add("empty");
      }
    });

    // Update progress bar
    const percentage = Math.round((filledCount / fields.length) * 100);
    progressBarFill.style.width = `${percentage}%`;
    completionRateBadge.textContent = `${percentage}٪ تکمیل شده`;
  }

  function checkOffTopic(isOffTopic) {
    if (isOffTopic) {
      offTopicIndicator.classList.remove("hidden");
    } else {
      offTopicIndicator.classList.add("hidden");
    }
  }

  let activeAudio = null;

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
      }
      const audioUrl = base64ToBlobUrl(base64Audio);
      activeAudio = new Audio(audioUrl);
      activeAudio.volume = 1.0;
      const playPromise = activeAudio.play();
      if (playPromise !== undefined) {
        playPromise.catch(err => {
          console.warn("Auto-play blocked by browser. User can click 'شنیدن گفتار' button:", err);
        });
      }
    } catch (e) {
      console.error("Audio playback error:", e);
    }
  }

  // Handle Text Submission
  textForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = textInput.value.trim();
    if (!text) return;

    appendMessage("user", text);
    textInput.value = "";
    textInput.disabled = true;
    sendBtn.disabled = true;
    micStatusText.textContent = "در حال پردازش پاسخ غرفه‌یار...";

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
      sendBtn.disabled = false;
      textInput.focus();
      micStatusText.textContent = "برای صحبت با غرفه‌یار کلیک کنید";
    }
  });

  function handleTurnResponse(data) {
    appendMessage("assistant", data.spoken_response, Boolean(data.audio_base64), data.audio_base64 || "");
    updateFormFields(data.form_data, data.updated_fields || {});
    checkOffTopic(data.is_off_topic);

    if (data.audio_base64) {
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

  // Handle Microphone Recording
  micBtn.addEventListener("click", async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  });

  async function startRecording() {
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioSamples = [];
      audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      const source = audioCtx.createMediaStreamSource(micStream);
      scriptNode = audioCtx.createScriptProcessor(4096, 1, 1);

      scriptNode.onaudioprocess = (e) => {
        if (!isRecording) return;
        const inputData = e.inputBuffer.getChannelData(0);
        for (let i = 0; i < inputData.length; i++) {
          audioSamples.push(inputData[i]);
        }
      };

      source.connect(scriptNode);
      scriptNode.connect(audioCtx.destination);

      isRecording = true;
      micBtn.classList.add("recording");
      micStatusText.textContent = "در حال ضبط... وقتی صحبت تمام شد کلیک کنید";
    } catch (err) {
      console.error("Mic access error:", err);
      alert("دسترسی به میکروفون امکان‌پذیر نیست. می‌توانید از کادر تایپ متن استفاده کنید.");
    }
  }

  async function stopRecording() {
    if (isRecording) {
      isRecording = false;
      micBtn.classList.remove("recording");
      micStatusText.textContent = "در حال پردازش گفتار...";

      if (scriptNode) {
        scriptNode.disconnect();
        scriptNode = null;
      }
      if (micStream) {
        micStream.getTracks().forEach(t => t.stop());
        micStream = null;
      }
      if (audioCtx) {
        audioCtx.close();
        audioCtx = null;
      }

      const wavBlob = encodeWAV(audioSamples, 16000);
      await sendAudio(wavBlob);
    }
  }

  async function sendAudio(blob) {
    const formData = new FormData();
    formData.append("file", blob, "visitor_speech.wav");

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
      micStatusText.textContent = "برای صحبت با غرفه‌یار کلیک کنید";
    }
  }

  // Reset Session
  resetBtn.addEventListener("click", async () => {
    if (confirm("آیا مایلید گفتگو با این بازدیدکننده ریست شده و اطلاعات جدید ثبت شود؟")) {
      await performReset();
    }
  });

  async function performReset() {
    try {
      const res = await fetch("/api/reset", { method: "POST" });
      const data = await res.json();
      renderInitialMessages([{ role: "assistant", content: data.greeting }]);
      updateFormFields(data.form_data, {});
      checkOffTopic(false);
      confirmationModal.classList.add("hidden");
    } catch (err) {
      console.error("Reset error:", err);
    }
  }

  // Summary Modal Logic
  showSummaryBtn.addEventListener("click", async () => {
    await openSummaryModal();
  });

  let lastFetchedSummary = null;

  async function openSummaryModal() {
    try {
      const res = await fetch("/api/summary");
      const summary = await res.json();
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

      confirmationModal.classList.remove("hidden");
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

  closeModalBtn.addEventListener("click", () => {
    confirmationModal.classList.add("hidden");
  });

  confirmLeadBtn.addEventListener("click", () => {
    alert("✅ اطلاعات بازدیدکننده با موفقیت در بانک اطلاعاتی غرفه ذخیره شد.");
    confirmationModal.classList.add("hidden");
  });

  newVisitorFromModalBtn.addEventListener("click", async () => {
    confirmationModal.classList.add("hidden");
    await performReset();
  });
});
