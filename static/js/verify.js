const stripe     = Stripe(stripePublishableKey);
const btn        = document.getElementById('verify-btn');
const statusMsg  = document.getElementById('status-msg');

btn.addEventListener('click', async () => {
  btn.disabled = true;
  btn.textContent = 'Зареждане...';
  statusMsg.textContent = '';

  try {
    const res = await fetch('/verify/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_type: userType, user_id: parseInt(userId) })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Грешка при стартиране на верификацията.');
    }

    const { error } = await stripe.verifyIdentity(data.client_secret);

    if (error) {
      statusMsg.style.color = '#9B1C35';
      statusMsg.textContent = 'Верификацията беше отменена или неуспешна.';
      btn.disabled = false;
      btn.textContent = 'Опитай отново';
    } else {
      statusMsg.style.color = '#2e7d32';
      statusMsg.textContent = 'Верификацията се обработва...';

      // Poll until Stripe marks the session as verified (max ~30s)
      let attempts = 0;
      const maxAttempts = 15;
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await fetch(
            `/verify/status?user_type=${userType}&user_id=${userId}`
          );
          const statusData = await statusRes.json();
          console.log(`[verify poll #${attempts}]`, statusData);
          if (statusData.verified) {
            clearInterval(pollInterval);
            statusMsg.textContent = 'Верификацията е успешна! Пренасочване...';
            setTimeout(() => { window.location.href = redirectAfterVerify; }, 1000);
          } else if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            statusMsg.textContent = 'Верификацията се обработва. Ще бъдеш пренасочен...';
            setTimeout(() => { window.location.href = redirectAfterVerify; }, 1500);
          }
        } catch (e) {
          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            window.location.href = redirectAfterVerify;
          }
        }
      }, 2000);
    }

  } catch (err) {
    statusMsg.style.color = '#9B1C35';
    statusMsg.textContent = err.message;
    btn.disabled = false;
    btn.textContent = 'Опитай отново';
  }
});
