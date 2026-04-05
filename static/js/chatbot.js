(function () {
  const btn = document.getElementById('chatbot-btn');
  const win = document.getElementById('chatbot-window');
  const closeBtn = document.getElementById('chatbot-close');
  const messages = document.getElementById('chatbot-messages');
  const form = document.getElementById('chatbot-form');
  const input = document.getElementById('chatbot-input');
  const send = document.getElementById('chatbot-send');

  let history = [];
  let open = false;

  btn.addEventListener('click', () => {
    open = !open;
    win.style.display = open ? 'flex' : 'none';
    if (open && history.length === 0) addBotMsg('Здравей! Аз съм GoodHost Асистент. Как мога да ти помогна?');
    if (open) input.focus();
  });

  closeBtn.addEventListener('click', () => {
    open = false;
    win.style.display = 'none';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    send.disabled = true;

    addUserMsg(text);
    history.push({ role: 'user', content: text });

    const typing = addBotMsg('...', true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history }),
      });
      const data = await res.json();
      typing.remove();
      if (data.reply) {
        addBotMsg(data.reply);
        history.push({ role: 'assistant', content: data.reply });
      } else {
        addBotMsg('Съжалявам, нещо се обърка. Опитай отново.');
      }
    } catch {
      typing.remove();
      addBotMsg('Няма връзка. Провери интернет и опитай отново.');
    }

    send.disabled = false;
    input.focus();
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  function addUserMsg(text) {
    const el = document.createElement('div');
    el.className = 'chat-msg user';
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  function addBotMsg(text, isTyping = false) {
    const el = document.createElement('div');
    el.className = 'chat-msg bot' + (isTyping ? ' typing' : '');
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }
})();
