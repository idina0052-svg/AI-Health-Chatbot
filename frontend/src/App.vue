<template>
  <div class="chat-app">
    <!-- Header -->
    <header class="chat-header">
      <h2>{{ t('title') }}</h2>
      <div class="controls">
        <select v-model="lang" @change="saveLang">
          <option value="en">English</option>
          <option value="ti">ትግርኛ</option>
        </select>
        <button class="refresh-btn" @click="refreshChat">⟳</button>
      </div>
    </header>

    <!-- Chat Messages -->
    <div class="messages" ref="messages">
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="message"
        :class="m.sender"
      >
        <div class="bubble">{{ m.text }}</div>
        <div v-if="m.followup" class="followup-buttons">
          <button class="yes" @click="sendQuick('yes')">{{ t('yes') }}</button>
          <button class="no" @click="sendQuick('no')">{{ t('no') }}</button>
        </div>
      </div>
    </div>

    <!-- Input Row -->
    <div class="input-row">
      <input
        v-model="text"
        @keyup.enter="send"
        :placeholder="t('placeholder')"
      />
      <button class="send-btn" @click="send">➤</button>
      <button v-if="canNext" class="next-btn" @click="sendNext">{{ t('next') }}</button>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { API_BASE_URL } from "@/config";
import enKB from "@/assets/KB/en.json";
import tiKB from "@/assets/KB/ti.json";
import stringSimilarity from "string-similarity";

let localSessions = {};

export default {
  data() {
    return {
      text: "",
      messages: [],
      sessionId: localStorage.getItem("session_id") || null,
      canNext: false,
      lang: localStorage.getItem("lang") || "en",
      translations: {
        en: { title: "AI Health Assistant", placeholder: "Describe the situation...", next: "Next ⏭", yes: "Yes", no: "No" },
        ti: { title: "ኤአይ ሓጋዚ ጥእና", placeholder: "ኹነታት ግለጽ...", next: "ቀጽል ⏭", yes: "እወ", no: "ኣይ" },
      },
    };
  },
  methods: {
    t(key) {
      return this.translations[this.lang]?.[key] || key;
    },

    async send() {
      if (!this.text.trim()) return;
      this.messages.push({ sender: "user", text: this.text });

      const payload = { message: this.text, lang: this.lang, session_id: this.sessionId };
      this.text = "";

      // ✅ Try local KB first
      const localRes = handleLocalMessage(payload);
      if (localRes.text && !localRes.text.startsWith("⚠️ I'm not sure")) {
        this.handleResponse(localRes);
      } else {
        // Fall back to backend
        const res = await this.callBackend(payload);
        this.handleResponse(res);
      }
    },

    async sendQuick(answer) {
      this.messages.push({ sender: "user", text: this.t(answer) });
      const payload = { message: answer, lang: this.lang, session_id: this.sessionId };
      const localRes = handleLocalMessage(payload);
      if (localRes.text && !localRes.text.startsWith("⚠️ I'm not sure")) {
        this.handleResponse(localRes);
      } else {
        const res = await this.callBackend(payload);
        this.handleResponse(res);
      }
    },

    async sendNext() {
      const payload = { action: "next", lang: this.lang, session_id: this.sessionId, message: "" };
      const localRes = handleLocalMessage(payload);
      if (localRes.text && !localRes.text.startsWith("⚠️ I'm not sure")) {
        this.handleResponse(localRes);
      } else {
        const res = await this.callBackend(payload);
        this.handleResponse(res);
      }
    },

    async callBackend(payload) {
      try {
        const r = await axios.post(`${API_BASE_URL}/chat`, payload);
        return r.data;
      } catch (e) {
        console.warn("⚠️ Backend unreachable → using local KB fallback");
        return handleLocalMessage(payload);
      }
    },

    handleResponse(res) {
      if (!res) return;

      if (res.session_id) {
        this.sessionId = res.session_id;
        localStorage.setItem("session_id", this.sessionId);
      }
      if (res.text) this.messages.push({ sender: "assistant", text: res.text });
      if (res.escalation) this.messages.push({ sender: "assistant", text: "⚠️ " + res.escalation });
      if (res.followup_question) this.messages.push({ sender: "assistant", text: res.followup_question, followup: true });
      this.canNext = !!res.has_next;

      this.scrollToBottom();
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.messages;
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    saveLang() {
      localStorage.setItem("lang", this.lang);
    },

    refreshChat() {
      this.messages = [];
      this.sessionId = null;
      localStorage.removeItem("session_id");
    },
  },
};

// ===== Local KB functions =====
function getKB(lang) {
  return lang === "ti" ? tiKB : enKB;
}

function startIntent(session, intent, kb) {
  const entry = kb[intent];
  if (!entry) return { text: "I don't have instructions for that.", done: true };

  session.intent = intent;
  session.steps = entry.steps || [];
  session.stepIndex = 0;
  session.awaitingFollowup = false;
  session.followup = entry.followups?.[0] || null;

  let response = { text: session.steps[0] || "" };
  if (session.followup) response.followup_question = session.followup.question;
  if (entry.escalation) response.escalation = entry.escalation;

  return response;
}

function advanceStep(session) {
  if (session.stepIndex + 1 < session.steps.length) {
    session.stepIndex++;
    return { text: session.steps[session.stepIndex], has_next: true };
  }
  return { text: "✅ End of steps. Please seek professional care if needed.", done: true };
}

function isPositive(answer, lang) {
  const a = answer.trim().replace("።", "").toLowerCase();
  const positives = { en: ["yes","y","ya","yep","sure"], ti: ["እወ","yes"], am: ["አዎ","yes"] };
  const negatives = { en: ["no","n","not","nope"], ti: ["ኣይ","ኖኖ"], am: ["አይ","ኖኖ"] };

  if (positives[lang]?.includes(a)) return true;
  if (negatives[lang]?.includes(a)) return false;
  return null;
}

// ===== Local KB functions =====
function handleLocalMessage(payload) {
  const { message, lang, session_id, action } = payload;
  const kb = lang === "ti" ? tiKB : enKB;

  let session = localSessions[session_id] || {
    intent: null,
    steps: [],
    current_step: -1,
    awaitingFollowup: false,
    followupMeta: null,
    lang
  };

  session.lang = lang;

  // 1️⃣ Handle NEXT button
  if (action === "next" && session.intent) {
    if (session.current_step + 1 < session.steps.length) {
      session.current_step++;
      localSessions[session_id] = session;
      return {
        session_id,
        text: session.steps[session.current_step],
        has_next: session.current_step + 1 < session.steps.length,
        followup_question: session.followupMeta?.question
      };
    } else {
      const escalation = kb[session.intent]?.escalation;
      localSessions[session_id] = session;
      return {
        session_id,
        text: escalation || (lang === "ti" ? "እቶም ስጉምትታት እዮም።" : "Those are the steps. If problem persists, seek professional care."),
        has_next: false
      };
    }
  }

  // 2️⃣ Handle follow-up answers (yes/no)
  if (session.awaitingFollowup && session.followupMeta) {
    const positive = isPositive(message, lang);
    if (positive === true && session.followupMeta.yes_intent) {
      const intent = session.followupMeta.yes_intent;
      return startNewIntent(session, intent, kb, session_id);
    } else if (positive === false && session.followupMeta.no_intent) {
      const intent = session.followupMeta.no_intent;
      return startNewIntent(session, intent, kb, session_id);
    } else {
      // Invalid answer, clear follow-up
      session.awaitingFollowup = false;
      session.followupMeta = null;
    }
  }

  // 3️⃣ Match new intent by exact keyword
  const userInput = message.toLowerCase();
  let matchedIntent = Object.keys(kb).find(intent =>
    kb[intent].keywords.some(kw => kw.toLowerCase() === userInput)
  );

  // 4️⃣ Fuzzy match for English
  if (!matchedIntent && lang === "en") {
    const allKeywords = [];
    const intentMap = {};
    for (let intent in kb) {
      (kb[intent].keywords || [intent]).forEach(kw => {
        allKeywords.push(kw.toLowerCase());
        intentMap[kw.toLowerCase()] = intent;
      });
    }
    const bestMatch = stringSimilarity.findBestMatch(userInput, allKeywords);
    if (bestMatch.bestMatch.rating >= 0.6) {
      matchedIntent = intentMap[bestMatch.bestMatch.target];
    }
  }

  if (matchedIntent) {
    return startNewIntent(session, matchedIntent, kb, session_id);
  }

  // 5️⃣ No match: fallback
  localSessions[session_id] = session;
  return {
    session_id,
    text: lang === "ti" ? "ኣብ ካብ መስመር ወጻኢ ፍልጠት የብለይን።" : "I don’t have specific instructions in my offline KB. Please consult a professional.",
    has_next: false
  };
}

function startNewIntent(session, intent, kb, session_id) {
  const entry = kb[intent];
  session.intent = intent;
  session.steps = entry.steps || [];
  session.current_step = 0;
  session.followupMeta = entry.followups?.[0] || null;
  session.awaitingFollowup = !!session.followupMeta;
  localSessions[session_id] = session;

  return {
    session_id,
    text: session.steps[0] || "",
    followup_question: session.followupMeta?.question,
    has_next: session.steps.length > 1
  };
}


</script>


<style scoped>
.chat-app {
  display: flex;
  flex-direction: column;
  height: 90vh;      /* fill exactly the screen */
  width: 100%;
  max-width: 420px;
  margin: auto;
  border: 1px solid #ccc;
  border-radius: 12px;
  overflow: hidden;
  font-family: sans-serif;
  background: #f9f9f9;
}
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}
/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #2d6cdf;
  color: white;
  padding: 12px;
}
.chat-header h2 {
  margin: 0;
  font-size: 18px;
}
.controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
.controls select {
  padding: 4px 6px;
  border-radius: 6px;
  border: none;
}
.refresh-btn {
  background: white;
  border: none;
  border-radius: 50%;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 16px;
}

/* Messages */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: #eef2f7;
}
.message {
  display: flex;
  flex-direction: column;
  margin: 8px 0;
}
.message.user {
  align-items: flex-end;
}
.message.assistant {
  align-items: flex-start;
}
.bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  word-wrap: break-word;
  white-space: pre-wrap;
}
.message.user .bubble {
  background: #2d6cdf;
  color: white;
  border-bottom-right-radius: 2px;
}
.message.assistant .bubble {
  background: white;
  color: #333;
  border-bottom-left-radius: 2px;
}

/* Followup buttons */
.followup-buttons {
  margin-top: 6px;
}
.followup-buttons button {
  margin: 0 4px;
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}
.followup-buttons .yes {
  background: #2ecc71;
  color: white;
}
.followup-buttons .no {
  background: #e74c3c;
  color: white;
}

/* Input */
.input-row {
  display: flex;
  padding: 8px;
  background: #fff;
  border-top: 1px solid #ddd;
}
.input-row input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 20px;
  outline: none;
}
.send-btn,
.next-btn {
  margin-left: 6px;
  padding: 10px 14px;
  border: none;
  border-radius: 50%;
  background: #2d6cdf;
  color: white;
  cursor: pointer;
}
.next-btn {
  border-radius: 16px;
}
</style>
