const stateEls = {
  danceType: document.getElementById('danceType'),
  cameraSelect: document.getElementById('cameraSelect'),
  vmcHost: document.getElementById('vmcHost'),
  vmcPort: document.getElementById('vmcPort'),
  startBtn: document.getElementById('startBtn'),
  stopBtn: document.getElementById('stopBtn'),
  refreshVideoBtn: document.getElementById('refreshVideoBtn'),
  sidebarToggle: document.getElementById('sidebarToggle'),
  appShell: document.querySelector('.app-shell'),
  timerValue: document.getElementById('timerValue'),
  sessionState: document.getElementById('sessionState'),
  modelStatus: document.getElementById('modelStatus'),
  videoStatus: document.getElementById('videoStatus'),
  videoHint: document.getElementById('videoHint'),
  rankPill: document.getElementById('rankPill'),
  scoreValue: document.getElementById('scoreValue'),
  scoreBar: document.getElementById('scoreBar'),
  danceValue: document.getElementById('danceValue'),
  bestCombo: document.getElementById('bestCombo'),
  feedbackValue: document.getElementById('feedbackValue'),
  weakestJointValue: document.getElementById('weakestJointValue'),
  userValue: document.getElementById('userValue'),
  vmcValue: document.getElementById('vmcValue'),
  recordValue: document.getElementById('recordValue'),
  lastImportValue: document.getElementById('lastImportValue'),
  scoreFocusValue: document.getElementById('scoreFocusValue'),
  scoreFocusBar: document.getElementById('scoreFocusBar'),
  scoreFocusRank: document.getElementById('scoreFocusRank'),
  scoreFocusFeedback: document.getElementById('scoreFocusFeedback'),
  scoreFocusCombo: document.getElementById('scoreFocusCombo'),
  scoreFocusWeakest: document.getElementById('scoreFocusWeakest'),
  chartMeta: document.getElementById('chartMeta'),
  scoreChartGrid: document.getElementById('scoreChartGrid'),
  scoreChartLine: document.getElementById('scoreChartLine'),
  scoreChartArea: document.getElementById('scoreChartArea'),
  scoreChartPeak: document.getElementById('scoreChartPeak'),
  scoreChartPeakText: document.getElementById('scoreChartPeakText'),
  feedListWide: document.getElementById('feedListWide'),
  historyListWide: document.getElementById('historyListWide'),
  historyDetail: document.getElementById('historyDetail'),
  historyDanceFilter: document.getElementById('historyDanceFilter'),
  historyGradeFilter: document.getElementById('historyGradeFilter'),
  historyKeyword: document.getElementById('historyKeyword'),
  historyFilterBtn: document.getElementById('historyFilterBtn'),
  importForm: document.getElementById('importForm'),
  importDanceType: document.getElementById('importDanceType'),
  importFile: document.getElementById('importFile'),
  importResult: document.getElementById('importResult'),
  importList: document.getElementById('importList'),
  modelList: document.getElementById('modelList'),
  deviceList: document.getElementById('deviceList'),
  permissionValue: document.getElementById('permissionValue'),
  activeCameraValue: document.getElementById('activeCameraValue'),
  cameraCountValue: document.getElementById('cameraCountValue'),
  vmcFpsValue: document.getElementById('vmcFpsValue'),
  vmcBoneCountValue: document.getElementById('vmcBoneCountValue'),
  vmcPacketCountValue: document.getElementById('vmcPacketCountValue'),
  serverDeviceSummary: document.getElementById('serverDeviceSummary'),
  accountState: document.getElementById('accountState'),
  loginUsername: document.getElementById('loginUsername'),
  loginPassword: document.getElementById('loginPassword'),
  loginBtn: document.getElementById('loginBtn'),
  logoutBtn: document.getElementById('logoutBtn'),
  registerUsername: document.getElementById('registerUsername'),
  registerPassword: document.getElementById('registerPassword'),
  registerRole: document.getElementById('registerRole'),
  registerBtn: document.getElementById('registerBtn'),
  resetPasswordBtn: document.getElementById('resetPasswordBtn'),
  userList: document.getElementById('userList'),
  perfectFx: document.getElementById('perfectFx'),
  judgeFx: document.getElementById('judgeFx'),
  comboFx: document.getElementById('comboFx'),
  video: document.getElementById('video'),
};

const navItems = [...document.querySelectorAll('.nav-item')];
const panels = [...document.querySelectorAll('.panel')];
let stream = null;
let eventSource = null;
let lastPerfectAt = 0;
let cameraDevices = [];
let scoreSeries = [];
let activeHistoryId = null;
let cachedHistory = [];
let lastStateToken = "";
let lastFeedToken = "";
let lastHistoryToken = "";
let lastImportsToken = "";
let reconnectTimer = null;
function setStatus(el, text, level = 'neutral') {
  el.textContent = text;
  el.className = `pill status-${level}`;
}

function toast(message) {
  console.log(message);
  const target = stateEls.importResult?.querySelector('strong');
  if (target) target.textContent = message;
}

function switchPanel(name) {
  navItems.forEach((btn) => btn.classList.toggle('active', btn.dataset.panel === name));
  panels.forEach((panel) => panel.classList.toggle('active', panel.id === `panel-${name}`));
}

function hasHistoryFilter() {
  return Boolean(stateEls.historyDanceFilter.value || stateEls.historyGradeFilter.value || stateEls.historyKeyword.value.trim());
}

async function detectPermission() {
  try {
    if (!navigator.permissions) return '浏览器未提供权限查询';
    const result = await navigator.permissions.query({ name: 'camera' });
    return result.state === 'granted' ? '已授予' : result.state === 'denied' ? '已拒绝' : '待确认';
  } catch {
    return '浏览器未提供权限查询';
  }
}

function mmss(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, '0');
  const s = String(sec % 60).padStart(2, '0');
  return `${m}:${s}`;
}

function scoreColor(score) {
  if (score < 70) return 'linear-gradient(90deg, #ff8a7a, #ff5f57)';
  if (score < 85) return 'linear-gradient(90deg, #ffd76a, #ffb340)';
  if (score < 92) return 'linear-gradient(90deg, #71e0af, #32c27d)';
  return 'linear-gradient(90deg, #8b5cff, #1fc8ff)';
}

function pushScorePoint(score) {
  scoreSeries.push(Number(score || 0));
  while (scoreSeries.length > 24) scoreSeries.shift();
  renderChart();
}

function renderChart() {
  const values = scoreSeries.length ? scoreSeries : [0];
  stateEls.chartMeta.textContent = `最近 ${values.length} 次采样`;
  const width = 640, height = 220, padX = 18, padY = 18;
  const usableW = width - padX * 2, usableH = height - padY * 2;
  const step = values.length > 1 ? usableW / (values.length - 1) : 0;
  const gridYs = [0, 25, 50, 75, 100].map((v) => height - padY - (v / 100) * usableH);
  stateEls.scoreChartGrid.innerHTML = gridYs.map((y) => `<line x1="${padX}" y1="${y.toFixed(1)}" x2="${width - padX}" y2="${y.toFixed(1)}"></line>`).join('');
  const pts = values.map((v, i) => [padX + i * step, height - padY - (Math.max(0, Math.min(100, v)) / 100) * usableH, v]);
  const lineD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
  const areaD = `${lineD} L ${pts[pts.length - 1][0].toFixed(1)} ${(height - padY).toFixed(1)} L ${pts[0][0].toFixed(1)} ${(height - padY).toFixed(1)} Z`;
  stateEls.scoreChartLine.setAttribute('d', lineD);
  stateEls.scoreChartArea.setAttribute('d', areaD);
  const peak = pts.reduce((best, cur) => (cur[2] >= best[2] ? cur : best), pts[0]);
  stateEls.scoreChartPeak.setAttribute('cx', peak[0].toFixed(1));
  stateEls.scoreChartPeak.setAttribute('cy', peak[1].toFixed(1));
  stateEls.scoreChartPeak.setAttribute('r', values.length ? '7' : '0');
  stateEls.scoreChartPeakText.setAttribute('x', (peak[0] + 10).toFixed(1));
  stateEls.scoreChartPeakText.setAttribute('y', (peak[1] - 10).toFixed(1));
  stateEls.scoreChartPeakText.textContent = `峰值 ${Math.round(peak[2])}`;
}

function renderFeed(feed) {
  const token = JSON.stringify(feed || []);
  if (token === lastFeedToken) return;
  lastFeedToken = token;
  stateEls.feedListWide.innerHTML = (feed || []).map((item) => {
    const cls = `rank-${String(item.rank || 'system').toLowerCase()}`;
    return `<article class="feed-item ${cls}"><header><strong>${item.title}</strong><small>${item.time}</small></header><p>${item.detail}</p></article>`;
  }).join('');
}

async function loadHistoryDetail(id) {
  const resp = await fetch(`/api/history/get?id=${id}`);
  const data = await resp.json();
  renderHistoryDetail(data.item || null);
}

function renderHistory(items) {
  const token = JSON.stringify(items || []);
  if (token === lastHistoryToken) {
    cachedHistory = items;
    return;
  }
  lastHistoryToken = token;
  cachedHistory = items;
  stateEls.historyListWide.innerHTML = items.map((item) => {
    const active = item.id === activeHistoryId ? 'active' : '';
    return `<article class="history-item ${active}" data-history-id="${item.id}"><header><strong>${item.dance_type} / ${item.grade}</strong><small>${item.created_at}</small></header><p>平均分 ${Number(item.avg_score || 0).toFixed(1)}，最高连击 ${item.best_combo || 0}，时长 ${mmss(item.duration_sec || 0)}</p></article>`;
  }).join('') || '<article class="history-item"><p>暂无历史记录</p></article>';
  stateEls.historyListWide.querySelectorAll('[data-history-id]').forEach((node) => {
    node.addEventListener('click', async () => {
      activeHistoryId = Number(node.dataset.historyId);
      renderHistory(cachedHistory);
      await loadHistoryDetail(activeHistoryId);
    });
  });
  if (!activeHistoryId && items.length) activeHistoryId = items[0].id;
  if (!items.length) renderHistoryDetail(null);
}

function renderHistoryDetail(item) {
  if (!item) {
    stateEls.historyDetail.className = 'history-detail empty';
    stateEls.historyDetail.innerHTML = '<div class="section-eyebrow">Record Detail</div><h3>选择一条历史记录</h3><p>展开后可查看平均分、时长、关节级分析和原始文件。</p><div class="history-preview">暂无截图预览</div>';
    return;
  }
  const preview = item.summary_image_url ? `<div class="history-preview has-image"><img src="${item.summary_image_url}" alt="历史截图"></div>` : '<div class="history-preview">暂无截图预览</div>';
  const joints = (item.analysis?.joint_scores || []).map((x) => `<div class="analysis-row"><span>${x.joint}</span><div class="analysis-bar"><i style="width:${Math.max(6, x.score)}%"></i></div><em>${x.score}</em></div>`).join('');
  const segments = (item.analysis?.segments || []).map((x) => `<div class="analysis-row"><span>片段 ${x.index}</span><div class="analysis-bar energy"><i style="width:${Math.max(6, Math.min(100, x.energy * 2000 + 8))}%"></i></div><em>${x.start_sec}-${x.end_sec}s</em></div>`).join('');
  stateEls.historyDetail.className = 'history-detail';
  stateEls.historyDetail.innerHTML = `
    <div class="section-eyebrow">Record Detail</div>
    <h3>${item.dance_type} / ${item.grade}</h3>
    <p>${item.created_at}</p>
    ${preview}
    <div class="history-detail-grid">
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 4v16"></path><path d="M7 9h10"></path><path d="M9 15h6"></path></svg></span>平均分</span><strong>${Number(item.avg_score || 0).toFixed(1)}</strong></div>
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M13 3 6 13h5l-1 8 8-11h-5l0-7z"></path></svg></span>最高连击</span><strong>${item.best_combo || 0}</strong></div>
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 5v7l4 2"></path><circle cx="12" cy="12" r="8"></circle></svg></span>舞蹈时长</span><strong>${mmss(item.duration_sec || 0)}</strong></div>
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"></circle><path d="M12 9v3l2 2"></path></svg></span>最弱关节</span><strong>${item.analysis?.worst_joint || '未知'}</strong></div>
    </div>
    <div class="mini-card report-card" style="margin-top:12px;"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 8h14"></path><path d="M5 12h10"></path><path d="M5 16h8"></path></svg></span>评估报告</span><strong>${item.summary_report || item.record_text || '暂无说明'}</strong></div>
    <div class="section-eyebrow" style="margin-top:16px;">关节级分析</div>
    <div class="analysis-grid">${joints || '<div class="mini-card"><span>暂无</span><strong>无可用分析</strong></div>'}</div>
    <div class="section-eyebrow" style="margin-top:16px;">时间片段</div>
    <div class="analysis-grid">${segments || '<div class="mini-card"><span>暂无</span><strong>无可用分析</strong></div>'}</div>
    <div class="action-row">
      <button id="replayHistoryBtn" class="btn secondary"><span class="btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 0 1-13.7 5.7"></path><path d="M4 12A8 8 0 0 1 17.7 6.3"></path><path d="M6 17H3v-3"></path></svg></span><span class="btn-label">重新评估</span></button>
      <button id="deleteHistoryBtn" class="btn secondary"><span class="btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 7h8"></path><path d="M6 7h12"></path><path d="M9 7V5h6v2"></path><path d="m8 10 1 8"></path><path d="m16 10-1 8"></path></svg></span><span class="btn-label">删除记录</span></button>
      <a class="btn secondary link-btn ${item.npy_url ? '' : 'disabled'}" ${item.npy_url ? `href="${item.npy_url}" target="_blank"` : ''}><span class="btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 8h14"></path><path d="M5 12h10"></path><path d="M5 16h8"></path></svg></span><span class="btn-label">打开 NPY</span></a>
      <a class="btn secondary link-btn ${item.bvh_url ? '' : 'disabled'}" ${item.bvh_url ? `href="${item.bvh_url}" target="_blank"` : ''}><span class="btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="5" y="6" width="14" height="12" rx="3"></rect><path d="M10 10h4"></path><path d="M10 14h4"></path></svg></span><span class="btn-label">打开 BVH</span></a>
      <a class="btn secondary link-btn ${item.source_url ? '' : 'disabled'}" ${item.source_url ? `href="${item.source_url}" target="_blank"` : ''}><span class="btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 4v10"></path><path d="m8 10 4 4 4-4"></path><path d="M5 18h14"></path></svg></span><span class="btn-label">打开源文件</span></a>
      <button id="exportHistoryBtn" class="btn secondary"><span class="btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 4v10"></path><path d="m8 10 4 4 4-4"></path><path d="M5 18h14"></path></svg></span><span class="btn-label">导出摘要</span></button>
    </div>`;
  document.getElementById('replayHistoryBtn').onclick = async () => toast((await postJson('/api/history/replay', { id: item.id })).message || '已提交重评');
  document.getElementById('deleteHistoryBtn').onclick = async () => { toast((await postJson('/api/history/delete', { id: item.id })).message || '已删除'); activeHistoryId = null; };
  document.getElementById('exportHistoryBtn').onclick = () => {
    const text = [
      `舞种: ${item.dance_type}`,
      `等级: ${item.grade}`,
      `平均分: ${Number(item.avg_score || 0).toFixed(1)}`,
      `最弱关节: ${item.analysis?.worst_joint || '未知'}`,
      `报告: ${item.summary_report || item.record_text || '暂无说明'}`,
    ].join('\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `history_${item.id}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  };
}

function renderImports(items) {
  const token = JSON.stringify(items || []);
  if (token === lastImportsToken) return;
  lastImportsToken = token;
  stateEls.importList.innerHTML = (items || []).map((item) => `<article class="history-item"><header><strong>${item.file_type || '未知类型'} / ${item.eval_grade || '--'}</strong><small>${item.created_at}</small></header><p>${item.stored_path}</p><p>状态：${item.eval_status || '已导入'}${item.eval_score != null ? `，分数 ${Number(item.eval_score).toFixed(1)}` : ''}</p></article>`).join('') || '<article class="history-item"><p>暂无导入记录</p></article>';
}

function renderModels(items) {
  stateEls.modelList.innerHTML = items.map((item) => `<article class="mini-card model-card ${item.exists ? 'ok' : 'warn'}"><div class="model-head"><span class="model-badge ${item.exists ? 'ok' : 'warn'}"></span><span class="model-code">${item.code}</span></div><strong>${item.name}</strong><p>${item.desc}</p><p class="model-path"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="5" y="6" width="14" height="12" rx="3"></rect><path d="M10 10h4"></path><path d="M10 14h4"></path></svg></span><span>权重：${item.weight}</span></p><em class="model-state ${item.exists ? 'ok' : 'warn'}">${item.exists ? '权重已就绪' : '缺少权重文件'}</em></article>`).join('');
}

function renderUsers(items, state) {
  stateEls.accountState.textContent = `${state.current_user || '游客'} / ${state.current_role || '学生'}`;
  stateEls.userList.innerHTML = items.map((item) => `<article class="device-item"><header><strong>${item.username}</strong><small>${item.role}</small></header><p>创建时间：${item.created_at}，最近登录：${item.last_login || '从未登录'}</p></article>`).join('');
}

function flashJudge(rank, combo, score) {
  stateEls.rankPill.textContent = rank;
  stateEls.judgeFx.textContent = rank;
  stateEls.judgeFx.classList.remove('hidden');
  stateEls.judgeFx.classList.add('show');
  stateEls.comboFx.textContent = `COMBO x${combo}`;
  stateEls.comboFx.classList.toggle('hidden', combo <= 0);
  stateEls.comboFx.classList.toggle('show', combo > 0);
  if (score >= 90 && Date.now() - lastPerfectAt > 3000) {
    lastPerfectAt = Date.now();
    stateEls.perfectFx.classList.remove('hidden');
    stateEls.perfectFx.classList.add('show');
    setTimeout(() => { stateEls.perfectFx.classList.remove('show'); stateEls.perfectFx.classList.add('hidden'); }, 1000);
  }
  setTimeout(() => { stateEls.judgeFx.classList.remove('show'); stateEls.judgeFx.classList.add('hidden'); }, 900);
}

function applyState(snapshot) {
  const state = snapshot.state || {};
  const record = snapshot.record || {};
  const stateToken = JSON.stringify({
    active: !!state.active,
    score: state.score || 0,
    feedback: state.feedback || '',
    rank: state.rank || 'IDLE',
    combo: state.combo || 0,
    best_combo: state.best_combo || 0,
    elapsed_sec: state.elapsed_sec || 0,
    weakest_joint: state.weakest_joint || '--',
    stats: state.stats || {},
    model_status: state.model_status || '未加载',
    last_update: state.last_update || 0,
    record_bvh: record.bvh || '',
    record_npy: record.npy || ''
  });
  if (stateToken === lastStateToken) return;

  const prevJudge = window.__lastJudgeState || {};
  const judgeChanged = (
    (state.rank || 'IDLE') !== (prevJudge.rank || 'IDLE') ||
    (state.combo || 0) !== (prevJudge.combo || 0) ||
    (state.score || 0) !== (prevJudge.score || 0) ||
    (state.last_update || 0) !== (prevJudge.last_update || 0) ||
    (!!state.active) !== (!!prevJudge.active)
  );

  lastStateToken = stateToken;
  stateEls.timerValue.textContent = mmss(state.elapsed_sec || 0);
  setStatus(stateEls.sessionState, state.active ? '实时评估中' : '待机', state.active ? 'ok' : 'neutral');
  setStatus(stateEls.modelStatus, state.model_status || '未加载', state.model_status === '真实模型' ? 'ok' : 'neutral');
  const score = state.score || 0;
  stateEls.scoreValue.textContent = score;
  stateEls.scoreFocusValue.textContent = score;
  const bg = scoreColor(score);
  stateEls.scoreBar.style.width = `${score}%`;
  stateEls.scoreBar.style.background = bg;
  stateEls.scoreFocusBar.style.width = `${score}%`;
  stateEls.scoreFocusBar.style.background = bg;
  stateEls.danceValue.textContent = state.dance_type || '未启动';
  stateEls.bestCombo.textContent = state.best_combo || 0;
  stateEls.feedbackValue.textContent = state.feedback || '等待开始';
  stateEls.weakestJointValue.textContent = state.weakest_joint || '--';
  stateEls.scoreFocusRank.textContent = state.rank || 'IDLE';
  stateEls.scoreFocusFeedback.textContent = state.feedback || '等待开始';
  stateEls.scoreFocusCombo.textContent = state.combo || 0;
  stateEls.scoreFocusWeakest.textContent = state.weakest_joint || '--';
  stateEls.userValue.textContent = `${state.current_user || '游客'} / ${state.current_role || '学生'}`;
  stateEls.vmcValue.textContent = `${state.host || '0.0.0.0'}:${state.port || 39539}`;
  stateEls.recordValue.textContent = record.bvh || record.npy || '尚未生成';
  stateEls.lastImportValue.textContent = state.last_import_path || '尚未导入';
  stateEls.startBtn.disabled = !!state.active;
  stateEls.stopBtn.disabled = !state.active;

  ['perfect', 'great', 'good', 'warn'].forEach((k) => {
    const key = k.toUpperCase();
    const value = state.stats?.[key] || 0;
    const total = Object.values(state.stats || {}).reduce((a, b) => a + b, 0) || 1;
    document.getElementById(`count-${k}`).textContent = value;
    document.getElementById(`stat-${k}`).style.width = `${(value * 100) / total}%`;
  });

  renderFeed(snapshot.feed || []);
  if (!scoreSeries.length || scoreSeries[scoreSeries.length - 1] !== Number(score)) {
    pushScorePoint(score);
  }
  if (judgeChanged && state.rank && state.rank !== 'IDLE' && state.active) {
    flashJudge(state.rank, state.combo || 0, score);
  }
  window.__lastJudgeState = {
    rank: state.rank || 'IDLE',
    combo: state.combo || 0,
    score: state.score || 0,
    last_update: state.last_update || 0,
    active: !!state.active,
  };

  const vmc = state.vmc_metrics || {};
  stateEls.vmcFpsValue.textContent = `${Number(vmc.fps || 0).toFixed(2)} fps`;
  stateEls.vmcBoneCountValue.textContent = String(vmc.bone_count || 0);
  stateEls.vmcPacketCountValue.textContent = String(vmc.packet_count || 0);
  stateEls.serverDeviceSummary.textContent = vmc.connected ? `VMC 已连接，最近 ${Number(vmc.fps || 0).toFixed(2)} fps，骨骼数 ${vmc.bone_count || 0}，已接收 ${vmc.packet_count || 0} 个 UDP 包。` : 'VMC 当前未连通。请检查 Rebocap 是否已经开始向当前 Host/Port 推流。';
}
function connectStream() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (eventSource) eventSource.close();
  eventSource = new EventSource('/api/stream');
  eventSource.addEventListener('state', (ev) => applyState(JSON.parse(ev.data)));
  eventSource.addEventListener('history', async (ev) => {
    if (hasHistoryFilter()) return;
    const items = JSON.parse(ev.data);
    const before = lastHistoryToken;
    renderHistory(items || []);
    if (activeHistoryId && before !== lastHistoryToken) await loadHistoryDetail(activeHistoryId);
  });
  eventSource.addEventListener('imports', (ev) => renderImports(JSON.parse(ev.data) || []));
  eventSource.onerror = () => {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectStream();
      }, 1500);
    }
  };
}

async function listVideoDevices() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  cameraDevices = devices.filter((d) => d.kind === 'videoinput');
  stateEls.cameraSelect.innerHTML = '';
  cameraDevices.forEach((cam, index) => {
    const opt = document.createElement('option');
    opt.value = cam.deviceId;
    opt.textContent = cam.label || `摄像头 ${index + 1}`;
    stateEls.cameraSelect.appendChild(opt);
  });
  const preferred = cameraDevices.find((cam) => /obs|virtual/i.test(cam.label || ''));
  if (preferred) {
    stateEls.cameraSelect.value = preferred.deviceId;
    setStatus(stateEls.videoStatus, `已识别到 ${preferred.label}`, 'ok');
  } else if (cameraDevices.length) {
    setStatus(stateEls.videoStatus, `找到 ${cameraDevices.length} 个视频设备`, 'neutral');
  } else {
    setStatus(stateEls.videoStatus, '未检测到视频设备', 'warn');
  }
  stateEls.cameraCountValue.textContent = String(cameraDevices.length);
  stateEls.activeCameraValue.textContent = stateEls.cameraSelect.options[stateEls.cameraSelect.selectedIndex]?.textContent || '未选择';
  stateEls.deviceList.innerHTML = cameraDevices.map((cam, index) => `<article class="device-item ${/obs|virtual/i.test(cam.label || '') ? 'device-obs' : 'device-normal'}"><header><strong>${cam.label || `摄像头 ${index + 1}`}</strong><small><span class="device-badge ${/obs|virtual/i.test(cam.label || '') ? 'obs' : 'normal'}">${/obs|virtual/i.test(cam.label || '') ? 'OBS' : 'CAM'}</span>${/obs|virtual/i.test(cam.label || '') ? '候选 OBS 虚拟摄像头' : '普通视频设备'}</small></header><p>deviceId: ${cam.deviceId || '无'}</p></article>`).join('');
}

async function startPreview() {
  try {
    if (stream) stream.getTracks().forEach((t) => t.stop());
    const deviceId = stateEls.cameraSelect.value;
    if (!deviceId) return false;
    stream = await navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    stateEls.video.srcObject = stream;
    setStatus(stateEls.videoStatus, `视频已连接：${stateEls.cameraSelect.options[stateEls.cameraSelect.selectedIndex]?.textContent || '当前设备'}`, 'ok');
    stateEls.videoHint.textContent = '如果画面仍不正确，请确认 OBS 已启动虚拟摄像头，再手动切换设备。';
    return true;
  } catch (err) {
    setStatus(stateEls.videoStatus, '视频连接失败', 'error');
    stateEls.videoHint.textContent = `视频打开失败：${err?.message || '未知错误'}。如果是 OBS，请先启动虚拟摄像头后再刷新设备。`;
    return false;
  }
}

async function postJson(url, payload) {
  const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload || {}) });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.message || '请求失败');
  return data;
}

async function refreshModels() { renderModels((await (await fetch('/api/models')).json()).items || []); }
async function refreshUser() { const data = await (await fetch('/api/user')).json(); renderUsers(data.users || [], data.state || {}); }

navItems.forEach((btn) => btn.addEventListener('click', () => switchPanel(btn.dataset.panel)));
stateEls.sidebarToggle?.addEventListener('click', () => stateEls.appShell.classList.toggle('sidebar-collapsed'));
stateEls.cameraSelect.addEventListener('change', startPreview);
stateEls.refreshVideoBtn.addEventListener('click', async () => { await listVideoDevices(); if (stateEls.cameraSelect.options.length) await startPreview(); });
stateEls.startBtn.addEventListener('click', async () => { if (!(await startPreview())) return; toast((await postJson('/api/start', { dance_type: stateEls.danceType.value, host: stateEls.vmcHost.value, port: Number(stateEls.vmcPort.value || 39539) })).message || '已启动'); scoreSeries = []; renderChart(); });
stateEls.stopBtn.addEventListener('click', async () => toast((await postJson('/api/stop', {})).message || '已停止'));
stateEls.historyFilterBtn.addEventListener('click', async () => {
  const params = new URLSearchParams();
  if (stateEls.historyDanceFilter.value) params.set('dance_type', stateEls.historyDanceFilter.value);
  if (stateEls.historyGradeFilter.value) params.set('grade', stateEls.historyGradeFilter.value);
  if (stateEls.historyKeyword.value.trim()) params.set('keyword', stateEls.historyKeyword.value.trim());
  const data = await (await fetch(`/api/history?${params.toString()}`)).json();
  activeHistoryId = null;
  renderHistory(data.items || []);
});
stateEls.importForm.addEventListener('submit', async (e) => { e.preventDefault(); const file = stateEls.importFile.files?.[0]; if (!file) return toast('请先选择文件'); const form = new FormData(); form.append('file', file); form.append('dance_type', stateEls.importDanceType.value); stateEls.importResult.querySelector('strong').textContent = '上传中...'; const resp = await fetch('/api/import/upload', { method: 'POST', body: form }); const data = await resp.json(); stateEls.importResult.innerHTML = `<span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 8h14"></path><path d="M5 12h10"></path><path d="M5 16h8"></path></svg></span>导入结果</span><strong>${data.message || '处理完成'}</strong>`; });
stateEls.loginBtn.addEventListener('click', async () => { toast((await postJson('/api/auth/login', { username: stateEls.loginUsername.value.trim(), password: stateEls.loginPassword.value })).message || '已登录'); await refreshUser(); });
stateEls.logoutBtn.addEventListener('click', async () => { toast((await postJson('/api/auth/logout', {})).message || '已退出'); await refreshUser(); });
stateEls.registerBtn.addEventListener('click', async () => { toast((await postJson('/api/auth/register', { username: stateEls.registerUsername.value.trim(), password: stateEls.registerPassword.value, role: stateEls.registerRole.value })).message || '注册成功'); await refreshUser(); });
stateEls.resetPasswordBtn.addEventListener('click', async () => toast((await postJson('/api/auth/reset_password', { username: stateEls.registerUsername.value.trim(), password: stateEls.registerPassword.value })).message || '密码已重置'));
navigator.mediaDevices.addEventListener('devicechange', listVideoDevices);

(async function boot() {
  stateEls.permissionValue.textContent = await detectPermission();
  try { await navigator.mediaDevices.getUserMedia({ video: true, audio: false }); stateEls.permissionValue.textContent = '已授予'; } catch { stateEls.permissionValue.textContent = '未授予'; }
  await listVideoDevices();
  if (stateEls.cameraSelect.options.length) await startPreview();
  renderChart();
  renderHistoryDetail(null);
  await refreshModels();
  await refreshUser();
  connectStream();
})();










