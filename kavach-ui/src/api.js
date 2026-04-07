// Same origin — frontend is served by FastAPI, so no cross-origin needed
const BASE = '';

export async function getChallenge() {
  const res = await fetch(`${BASE}/challenge`);
  if (!res.ok) throw new Error('Failed to get challenge');
  return res.json();
}

export async function verifyKYC({ videoBlob, idImageB64, nonce, deviceId }) {
  const form = new FormData();
  form.append('video', videoBlob, 'recording.webm');
  form.append('id_image', idImageB64);
  form.append('nonce', nonce);
  if (deviceId) form.append('device_id', deviceId);

  const res = await fetch(`${BASE}/verify`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('Verification failed');
  return res.json();
}

export async function runDemoScenario(scenario) {
  const res = await fetch(`${BASE}/demo/${scenario}`, { method: 'POST' });
  if (!res.ok) throw new Error('Demo failed');
  return res.json();
}
