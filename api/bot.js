// Vercel serverless proxy: menyembunyikan BOT_API_KEY & alamat server bot dari browser
const ALLOWED = ['status', 'logs', 'start', 'stop', 'restart', 'emotes'];

module.exports = async (req, res) => {
  if (req.headers['x-panel-password'] !== process.env.PANEL_PASSWORD) {
    return res.status(401).json({ error: 'Password panel salah' });
  }
  const p = String(req.query.p || '');
  if (!ALLOWED.includes(p)) return res.status(404).json({ error: 'Endpoint tidak dikenal' });
  try {
    const r = await fetch(`${process.env.BOT_API_URL}/${p}`, {
      method: req.method,
      headers: { 'content-type': 'application/json', 'x-api-key': process.env.BOT_API_KEY },
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : JSON.stringify(req.body || {}),
    });
    res.status(r.status).setHeader('content-type', 'application/json').send(await r.text());
  } catch (e) {
    res.status(502).json({ error: 'Server bot tidak terjangkau: ' + e.message });
  }
};
