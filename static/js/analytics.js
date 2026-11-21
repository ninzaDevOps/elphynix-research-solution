(async function renderTrafficChart() {
  const totalElement = document.getElementById('aTotal');
  const completeElement = document.getElementById('aComplete');
  const dropElement = document.getElementById('aDrop');
  const canvas = document.getElementById('traffic');
  const context = canvas.getContext('2d');

  try {
    const metricsResponse = await api('/api/analytics/metrics');
    if (!metricsResponse.ok) throw new Error('Could not load analytics metrics');
    const metrics = await metricsResponse.json();
    totalElement.textContent = metrics.totalTraffics.value;
    completeElement.textContent = `${metrics.completePercent.value}%`;
    dropElement.textContent = `${metrics.totalDropPercent.value}%`;

    const chartResponse = await api('/api/analytics/traffic-chart');
    if (!chartResponse.ok) throw new Error('Could not load traffic chart');
    const chart = await chartResponse.json();

    const width = Math.max(canvas.clientWidth, 320);
    const height = 260;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.width = '100%';
    canvas.style.height = `${height}px`;
    context.scale(ratio, ratio);
    context.clearRect(0, 0, width, height);

    const values = chart.data || [];
    const max = Math.max(1, ...values);
    const left = 38, right = width - 12, top = 18, bottom = height - 38;
    context.font = '12px sans-serif';
    context.strokeStyle = '#d7dee8';
    context.fillStyle = '#526174';
    context.lineWidth = 1;
    for (let tick = 0; tick <= 4; tick += 1) {
      const y = bottom - (bottom - top) * tick / 4;
      context.beginPath(); context.moveTo(left, y); context.lineTo(right, y); context.stroke();
      context.fillText(String(Math.round(max * tick / 4)), 4, y + 4);
    }
    if (!values.length) {
      context.fillText('No survey traffic recorded yet', left + 8, (top + bottom) / 2);
      return;
    }
    const xAt = (index) => values.length === 1 ? (left + right) / 2 : left + (right - left) * index / (values.length - 1);
    const yAt = (value) => bottom - (bottom - top) * value / max;
    context.strokeStyle = '#2563eb'; context.lineWidth = 2.5; context.beginPath();
    values.forEach((value, index) => index ? context.lineTo(xAt(index), yAt(value)) : context.moveTo(xAt(index), yAt(value)));
    context.stroke();
    context.fillStyle = '#2563eb';
    values.forEach((value, index) => { context.beginPath(); context.arc(xAt(index), yAt(value), 3, 0, Math.PI * 2); context.fill(); });
    context.fillStyle = '#526174';
    const labels = chart.labels || [];
    const stride = Math.max(1, Math.ceil(labels.length / 6));
    labels.forEach((label, index) => { if (index % stride === 0 || index === labels.length - 1) context.fillText(label, Math.min(xAt(index), right - 42), height - 12); });
  } catch (error) {
    console.error(error);
    context.fillText('Analytics are temporarily unavailable', 12, 24);
  }
})();
