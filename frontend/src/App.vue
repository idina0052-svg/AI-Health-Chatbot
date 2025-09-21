<template>
  <div class="chat-app">
    <!-- Header -->
    <header class="chat-header">
      <h2>{{ t('title') }}</h2>
      <div class="controls">
        <!-- Language Selector -->
        <select v-model="lang" @change="saveLang">
          <option value="en">English</option>
          <option value="ti">ትግርኛ</option>
        </select>
        <!-- Refresh Button -->
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
        <!-- If it's a followup, show yes/no buttons -->
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

console.log("🔎 API_BASE_URL:", API_BASE_URL);  
export default {
  data() {
    return {
      text: "",
      messages: [],
      sessionId: localStorage.getItem("session_id") || null,
      canNext: false,
      lang: localStorage.getItem("lang") || "en",

      // ✅ translations map
      translations: {
        en: {
          title: "AI Health Assistant",
          placeholder: "Describe the situation...",
          next: "Next ⏭",
          yes: "Yes",
          no: "No",
        },
       
        ti: {
          title: "ኤአይ ሓጋዚ ጥእና",
          placeholder: "ኹነታት ግለጽ...",
          next: "ቀጽል ⏭",
          yes: "እወ",
          no: "ኣይ",
        },
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

      const payload = {
        message: this.text,
        lang: this.lang,
        session_id: this.sessionId,
      };
      this.text = "";

      const res = await this.callBackend(payload);
      this.handleResponse(res);
    },
    async sendQuick(answer) {
      this.messages.push({ sender: "user", text: this.t(answer) });

      const payload = { message: answer, lang: this.lang, session_id: this.sessionId };
      const res = await this.callBackend(payload);
      this.handleResponse(res);
    },
    async sendNext() {
      const payload = {
        action: "next",
        lang: this.lang,
        session_id: this.sessionId,
        message: "",
      };
      const res = await this.callBackend(payload);
      this.handleResponse(res);
    },
    async callBackend(payload) {
      try {
        
        const r = await axios.post(`${API_BASE_URL}/chat`, payload);
       
        return r.data;
      } catch (e) {
        
        this.messages.push({
          sender: "assistant",
          text: "⚠️ Sorry, server error.",
        });
        console.error(e);
        return null;
      }
    },
    handleResponse(res) {
      if (!res) return;

      if (res.session_id) {
        this.sessionId = res.session_id;
        localStorage.setItem("session_id", this.sessionId);
      }

      if (res.text) {
        this.messages.push({ sender: "assistant", text: res.text });
      }

      if (res.escalation) {
        this.messages.push({
          sender: "assistant",
          text: "⚠️ " + res.escalation,
        });
      }

      if (res.followup_question) {
        this.messages.push({
          sender: "assistant",
          text: res.followup_question,
          followup: true, // ✅ mark as followup so buttons show
        });
      }

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
