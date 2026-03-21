const els = {
  backendBaseUrl: document.getElementById('backendBaseUrl'),
  saveBackendBtn: document.getElementById('saveBackendBtn'),
  danceType: document.getElementById('danceType'),
  cameraSelect: document.getElementById('cameraSelect'),
  vmcHost: document.getElementById('vmcHost'),
  vmcPort: document.getElementById('vmcPort'),
  startBtn: document.getElementById('startBtn'),
  stopBtn: document.getElementById('stopBtn'),
  refreshVideoBtn: document.getElementById('refreshVideoBtn'),
  mobileSessionState: document.getElementById('mobileSessionState'),
  liveVideo: document.getElementById('liveVideo'),
  videoStage: document.getElementById('videoStage'),
  standardVideo: document.getElementById('standardVideo'),
  standardEmpty: document.getElementById('standardEmpty'),
  videoPrimaryLabel: document.getElementById('videoPrimaryLabel'),
  videoPrimarySubtag: document.getElementById('videoPrimarySubtag'),
  swapVideoBtn: document.getElementById('swapVideoBtn'),
  fullscreenBtn: document.getElementById('fullscreenBtn'),
  standardPlayBtn: document.getElementById('standardPlayBtn'),
  standardAudioBtn: document.getElementById('standardAudioBtn'),
  standardSeek: document.getElementById('standardSeek'),
  standardCurrentTime: document.getElementById('standardCurrentTime'),
  standardDuration: document.getElementById('standardDuration'),
  videoStatus: document.getElementById('videoStatus'),
  scoreValue: document.getElementById('scoreValue'),
  timerValue: document.getElementById('timerValue'),
  bestCombo: document.getElementById('bestCombo'),
  feedbackValue: document.getElementById('feedbackValue'),
  weakestJointValue: document.getElementById('weakestJointValue'),
  scoreFocusRank: document.getElementById('scoreFocusRank'),
  scoreBar: document.getElementById('scoreBar'),
  cfpiTotalBadge: document.getElementById('cfpiTotalBadge'),
  scoreCfpiAccuracy: document.getElementById('scoreCfpiAccuracy'),
  scoreCfpiRhythm: document.getElementById('scoreCfpiRhythm'),
  scoreCfpiFluency: document.getElementById('scoreCfpiFluency'),
  scoreCfpiExpression: document.getElementById('scoreCfpiExpression'),
  cfpiLiveNeck: document.getElementById('cfpiLiveNeck'),
  cfpiLiveWrist: document.getElementById('cfpiLiveWrist'),
  cfpiLiveShoulder: document.getElementById('cfpiLiveShoulder'),
  cfpiLiveHat: document.getElementById('cfpiLiveHat'),
  cfpiLiveNeckValue: document.getElementById('cfpiLiveNeckValue'),
  cfpiLiveWristValue: document.getElementById('cfpiLiveWristValue'),
  cfpiLiveShoulderValue: document.getElementById('cfpiLiveShoulderValue'),
  cfpiLiveHatValue: document.getElementById('cfpiLiveHatValue'),
  feedList: document.getElementById('feedList'),
  historyDanceFilter: document.getElementById('historyDanceFilter'),
  historyGradeFilter: document.getElementById('historyGradeFilter'),
  historyKeyword: document.getElementById('historyKeyword'),
  historyFilterBtn: document.getElementById('historyFilterBtn'),
  historyList: document.getElementById('historyList'),
  historyDetail: document.getElementById('historyDetail'),
  importForm: document.getElementById('importForm'),
  importDanceType: document.getElementById('importDanceType'),
  importFile: document.getElementById('importFile'),
  importResult: document.getElementById('importResult'),
  importList: document.getElementById('importList'),
  permissionValue: document.getElementById('permissionValue'),
  activeCameraValue: document.getElementById('activeCameraValue'),
  cameraCountValue: document.getElementById('cameraCountValue'),
  vmcFpsValue: document.getElementById('vmcFpsValue'),
  vmcBoneCountValue: document.getElementById('vmcBoneCountValue'),
  vmcPacketCountValue: document.getElementById('vmcPacketCountValue'),
  serverDeviceSummary: document.getElementById('serverDeviceSummary'),
  deviceList: document.getElementById('deviceList'),
  modelList: document.getElementById('modelList'),
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
};

const pages = [...document.querySelectorAll('.tab-page')];
const navBtns = [...document.querySelectorAll('.nav-btn')];
const BACKEND_KEY = 'danceguard:mobile-backend';
const AUDIO_KEY = 'danceguard:mobile-standard-audio';
const STANDARD_VIDEO_MAP = {
  kara: '/assets/standard/kara-jorga.mp4',
  muqam: '/assets/standard/muqam.mp4',
};

let backendBaseUrl = '';
let cameraStream = null;
let eventSource = null;
let cameraDevices = [];
let standardAudioEnabled = false;
let stageSwapped = false;

function baseOrigin() {
  return backendBaseUrl ? backendBaseUrl.replace(/\/$/, '') : window.location.origin;
}

function apiUrl(path) {
  return `${baseOrigin()}${path}`;
}

function assetUrl(path) {
  return `${baseOrigin()}${path}`;
}

function mmss(sec) {
  const total = Math.max(0, Math.floor(Number(sec || 0)));
  const m = String(Math.floor(total / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${m}:${s}`;
}

function setPill(el, text, tone = 'neutral') {
  if (!el) return;
  el.textContent = text;
  el.className = `pill ${tone}`;
}

function toast(message) {
  console.log(message);
  if (els.importResult) {
    els.importResult.textContent = message;
  }
}

function switchTab(name) {
  pages.forEach((p) => p.classList.toggle('active', p.id === `tab-${name}`));
  navBtns.forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
}

function standardVideoPath() {
  return /muqam/i.test(String(els.danceType?.value || '')) ? STANDARD_VIDEO_MAP.muqam : STANDARD_VIDEO_MAP.kara;
}

function syncStage() {
  els.videoStage?.classList.toggle('swapped', stageSwapped);
  if (els.videoPrimaryLabel) {
    els.videoPrimaryLabel.textContent = stageSwapped ? 'Standard Demo' : 'Live Capture';
  }
  if (els.videoPrimarySubtag) {
    els.videoPrimarySubtag.textContent = stageSwapped ? (els.danceType?.value || '标准参考') : 'OBS / 云景虚拟摄像头';
  }
  els.swapVideoBtn.textContent = stageSwapped ? '恢复布局' : '交换画面';
}

function applyStandardAudio() {
  if (!els.standardVideo) return;
  els.standardVideo.muted = !standardAudioEnabled;
  els.standardAudioBtn.textContent = standardAudioEnabled ? '静音' : '伴奏';
}

function colorBar(node, score) {
  if (!node) return;
  const value = Math.max(4, Math.min(100, Number(score) || 0));
  node.style.width = `${value}%`;
  node.style.background = value >= 92
    ? 'linear-gradient(90deg,#8b5cff,#1fc8ff)'
    : value >= 85
      ? 'linear-gradient(90deg,#71e0af,#32c27d)'
      : value >= 70
        ? 'linear-gradient(90deg,#ffd76a,#ffb340)'
        : 'linear-gradient(90deg,#ff8a7a,#ff5f57)';
}

async function detectPermission() {
  try {
    if (!navigator.permissions) return '浏览器不支持';
    const result = await navigator.permissions.query({ name: 'camera' });
    if (result.state === 'granted') return '已授予';
    if (result.state === 'denied') return '已拒绝';
    return '待确认';
  } catch {
    return '浏览器不支持';
  }
}

async function postJson(path, payload) {
  const resp = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.message || '请求失败');
  return data;
}

async function fetchJson(path) {
  const resp = await fetch(apiUrl(path));
  return await resp.json();
}

async function listVideoDevices() {
  if (!navigator.mediaDevices?.enumerateDevices) {
    setPill(els.videoStatus, '设备枚举不可用', 'error');
    return;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    cameraDevices = devices.filter((d) => d.kind === 'videoinput');
    els.cameraSelect.innerHTML = '';
    cameraDevices.forEach((cam, index) => {
      const opt = document.createElement('option');
      opt.value = cam.deviceId;
      opt.textContent = cam.label || `摄像头 ${index + 1}`;
      els.cameraSelect.appendChild(opt);
    });
    const preferred = cameraDevices.find((cam) => /obs|virtual/i.test(cam.label || ''));
    if (preferred) els.cameraSelect.value = preferred.deviceId;
    els.cameraCountValue.textContent = String(cameraDevices.length);
    els.activeCameraValue.textContent = els.cameraSelect.options[els.cameraSelect.selectedIndex]?.textContent || '未选择';
    els.deviceList.innerHTML = cameraDevices.map((cam) => {
      const tag = /obs|virtual/i.test(cam.label || '') ? 'OBS 候选' : '摄像设备';
      return `<article class="history-item"><header><strong>${cam.label || '未命名设备'}</strong><small>${tag}</small></header><p>${cam.deviceId}</p></article>`;
    }).join('') || '<article class="history-item"><p>未检测到视频设备</p></article>';
  } catch (err) {
    setPill(els.videoStatus, '识别设备失败', 'error');
    els.deviceList.innerHTML = `<article class="history-item"><p>${err?.message || '设备枚举失败'}</p></article>`;
  }
}

async function startPreview() {
  if (!navigator.mediaDevices?.getUserMedia) return false;
  try {
    if (cameraStream) cameraStream.getTracks().forEach((t) => t.stop());
    const deviceId = els.cameraSelect.value;
    if (!deviceId) return false;
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        deviceId: { exact: deviceId },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
    els.liveVideo.srcObject = cameraStream;
    setPill(els.videoStatus, '视频已连接', 'ok');
    els.activeCameraValue.textContent = els.cameraSelect.options[els.cameraSelect.selectedIndex]?.textContent || '未选择';
    return true;
  } catch (err) {
    setPill(els.videoStatus, '视频连接失败', 'warn');
    console.error(err);
    return false;
  }
}

function updateStandardSource(reset = false) {
  const src = assetUrl(standardVideoPath());
  if (!reset && els.standardVideo.dataset.src === src) return;
  els.standardVideo.dataset.src = src;
  els.standardVideo.src = src;
  els.standardVideo.load();
  els.standardEmpty.textContent = `未找到标准视频：${src.split('/').pop()}`;
}

async function prepareStandardVideo(resetTime = true) {
  updateStandardSource();
  if (resetTime) {
    try { els.standardVideo.currentTime = 0; } catch (_) {}
  }
  applyStandardAudio();
}

function updateStandardProgress() {
  const duration = Number(els.standardVideo.duration || 0);
  const current = Number(els.standardVideo.currentTime || 0);
  els.standardSeek.value = duration > 0 ? String(Math.round((current / duration) * 1000)) : '0';
  els.standardCurrentTime.textContent = mmss(current);
  els.standardDuration.textContent = mmss(duration);
}

function seekStandardBySlider() {
  const duration = Number(els.standardVideo.duration || 0);
  if (!duration) return;
  const ratio = Number(els.standardSeek.value || 0) / 1000;
  try { els.standardVideo.currentTime = ratio * duration; } catch (_) {}
  updateStandardProgress();
}

async function playStandard() {
  try {
    await els.standardVideo.play();
  } catch (err) {
    console.error(err);
  }
}

function connectStream() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(apiUrl('/api/stream'));
  eventSource.addEventListener('state', (ev) => {
    try { applyState(JSON.parse(ev.data)); } catch (_) {}
  });
  eventSource.addEventListener('history', (ev) => {
    try { renderHistory(JSON.parse(ev.data) || []); } catch (_) {}
  });
  eventSource.addEventListener('imports', (ev) => {
    try { renderImports(JSON.parse(ev.data) || []); } catch (_) {}
  });
}

function applyState(snapshot) {
  const state = snapshot.state || {};
  const feed = snapshot.feed || [];
  els.timerValue.textContent = mmss(Number(state.elapsed_sec || 0));
  els.scoreValue.textContent = String(Math.round(Number(state.score || 0)));
  els.bestCombo.textContent = String(state.best_combo || 0);
  els.feedbackValue.textContent = state.feedback || '等待开始';
  els.weakestJointValue.textContent = state.weakest_joint || '--';
  els.scoreFocusRank.textContent = state.rank || 'IDLE';
  els.scoreBar.style.width = `${Math.max(0, Math.min(100, Number(state.score || 0)))}%`;
  setPill(els.mobileSessionState, state.active ? '评估中' : '待机', state.active ? 'ok' : 'neutral');

  const cfpi = state.cfpi || {};
  const dims = cfpi.dimensions || {};
  setPill(els.cfpiTotalBadge, `CFPI ${Number(cfpi.total || 0).toFixed(1)}`, 'neutral');
  els.scoreCfpiAccuracy.textContent = Number(dims.accuracy || 0).toFixed(1);
  els.scoreCfpiRhythm.textContent = Number(dims.rhythm || 0).toFixed(1);
  els.scoreCfpiFluency.textContent = Number(dims.fluency || 0).toFixed(1);
  els.scoreCfpiExpression.textContent = Number(dims.expression || 0).toFixed(1);

  const cf = cfpi.cultural_features || {};
  colorBar(els.cfpiLiveNeck, cf.neck_shift || 0);
  colorBar(els.cfpiLiveWrist, cf.wrist_flip || 0);
  colorBar(els.cfpiLiveShoulder, cf.shoulder_shimmy || 0);
  colorBar(els.cfpiLiveHat, cf.hat_hold || 0);
  els.cfpiLiveNeckValue.textContent = Number(cf.neck_shift || 0).toFixed(1);
  els.cfpiLiveWristValue.textContent = Number(cf.wrist_flip || 0).toFixed(1);
  els.cfpiLiveShoulderValue.textContent = Number(cf.shoulder_shimmy || 0).toFixed(1);
  els.cfpiLiveHatValue.textContent = Number(cf.hat_hold || 0).toFixed(1);

  const vmc = state.vmc_metrics || {};
  els.vmcFpsValue.textContent = Number(vmc.fps || 0).toFixed(2);
  els.vmcBoneCountValue.textContent = String(vmc.bone_count || 0);
  els.vmcPacketCountValue.textContent = String(vmc.packet_count || 0);
  els.serverDeviceSummary.textContent = vmc.connected
    ? `VMC 已连接，FPS ${Number(vmc.fps || 0).toFixed(2)}`
    : '后端暂未收到骨骼流';

  els.feedList.innerHTML = (feed || []).map((item) => {
    return `<article class="feed-item"><header><strong>${item.title}</strong><small>${item.time}</small></header><p>${item.detail}</p></article>`;
  }).join('') || '<article class="feed-item"><p>暂无实时反馈</p></article>';
}

function renderHistory(items) {
  els.historyList.innerHTML = (items || []).map((item) => {
    return `<article class="history-item" data-id="${item.id}"><header><strong>${item.dance_type} / ${item.grade}</strong><small>${item.created_at}</small></header><p>均分 ${Number(item.avg_score || 0).toFixed(1)}，时长 ${mmss(item.duration_sec || 0)}</p></article>`;
  }).join('') || '<article class="history-item"><p>暂无历史记录</p></article>';
  els.historyList.querySelectorAll('[data-id]').forEach((node) => node.addEventListener('click', () => loadHistoryDetail(Number(node.dataset.id))));
}

async function loadHistoryDetail(id) {
  const data = await fetchJson(`/api/history/get?id=${id}`);
  const item = data.item;
  if (!item) {
    els.historyDetail.textContent = '未找到历史记录';
    return;
  }
  const cfpi = item.analysis?.cfpi || {};
  const dims = cfpi.dimensions || {};
  els.historyDetail.innerHTML = `
    <div class="stack-form">
      <strong>${item.dance_type} / ${item.grade}</strong>
      <span>${item.created_at}</span>
      <span>均分 ${Number(item.avg_score || 0).toFixed(1)}</span>
      <span>CFPI ${Number(cfpi.total || 0).toFixed(1)}</span>
      <span>最弱关节 ${item.analysis?.worst_joint || '--'}</span>
      <span>准确度 ${Number(dims.accuracy || 0).toFixed(1)} / 节奏 ${Number(dims.rhythm || 0).toFixed(1)}</span>
      <div class="action-row">
        <button id="replayHistoryBtn" class="btn secondary" type="button">重新评估</button>
        <button id="deleteHistoryBtn" class="btn secondary" type="button">删除记录</button>
      </div>
    </div>`;
  document.getElementById('replayHistoryBtn').onclick = async () => {
    toast((await postJson('/api/history/replay', { id })).message || '历史记录已重新评估');
  };
  document.getElementById('deleteHistoryBtn').onclick = async () => {
    toast((await postJson('/api/history/delete', { id })).message || '历史记录已删除');
  };
}

function renderImports(items) {
  els.importList.innerHTML = (items || []).map((item) => {
    const score = item.eval_score != null ? `，得分 ${Number(item.eval_score).toFixed(1)}` : '';
    return `<article class="history-item"><header><strong>${item.file_type || '未知文件'}</strong><small>${item.created_at}</small></header><p>${item.eval_status || '待处理'}${score}</p></article>`;
  }).join('') || '<article class="history-item"><p>暂无导入记录</p></article>';
}

function renderModels(items) {
  els.modelList.innerHTML = (items || []).map((item) => {
    return `<article class="history-item"><header><strong>${item.name}</strong><small>${item.exists ? 'READY' : 'MISSING'}</small></header><p>${item.desc}</p><p>${item.weight}</p></article>`;
  }).join('');
}

function renderUsers(items, state) {
  setPill(els.accountState, `${state.current_user || '游客'} / ${state.current_role || '学生'}`, 'neutral');
  els.userList.innerHTML = (items || []).map((item) => {
    return `<article class="history-item"><header><strong>${item.username}</strong><small>${item.role}</small></header><p>创建时间 ${item.created_at}</p><p>最近登录 ${item.last_login || '未登录'}</p></article>`;
  }).join('');
}

async function refreshModels() {
  renderModels((await fetchJson('/api/models')).items || []);
}

async function refreshUser() {
  const data = await fetchJson('/api/user');
  renderUsers(data.users || [], data.state || {});
}

async function saveBackendBase() {
  backendBaseUrl = (els.backendBaseUrl.value || '').trim().replace(/\/$/, '');
  try { localStorage.setItem(BACKEND_KEY, backendBaseUrl); } catch (_) {}
  connectStream();
  await refreshModels();
  await refreshUser();
  toast(`后端地址已保存：${backendBaseUrl || '同源'}`);
}

navBtns.forEach((btn) => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
els.saveBackendBtn.addEventListener('click', saveBackendBase);
els.refreshVideoBtn.addEventListener('click', async () => {
  await listVideoDevices();
  if (els.cameraSelect.options.length) await startPreview();
});
els.cameraSelect.addEventListener('change', startPreview);
els.danceType.addEventListener('change', async () => {
  updateStandardSource(true);
  await prepareStandardVideo(true);
});

els.startBtn.addEventListener('click', async () => {
  const previewOk = await startPreview();
  if (!previewOk) {
    setPill(els.videoStatus, '视频预览失败，评分继续', 'warn');
  }
  try {
    const result = await postJson('/api/start', {
      dance_type: els.danceType.value,
      host: els.vmcHost.value,
      port: Number(els.vmcPort.value || 39539),
    });
    toast(result.message || '评分链路已启动');
    setPill(els.mobileSessionState, '连接中', 'neutral');
  } catch (err) {
    toast(err.message || '启动失败');
    setPill(els.mobileSessionState, '启动失败', 'error');
  }
});

els.stopBtn.addEventListener('click', async () => {
  try {
    toast((await postJson('/api/stop', {})).message || '评分会话已停止');
  } catch (err) {
    toast(err.message || '停止失败');
  }
});

els.swapVideoBtn.addEventListener('click', () => {
  stageSwapped = !stageSwapped;
  syncStage();
});

els.fullscreenBtn.addEventListener('click', async () => {
  if (document.fullscreenElement === els.videoStage) {
    await document.exitFullscreen();
  } else {
    await els.videoStage.requestFullscreen().catch(() => {});
  }
});

els.standardPlayBtn.addEventListener('click', async () => {
  if (els.standardVideo.paused) await playStandard();
  else els.standardVideo.pause();
});

els.standardAudioBtn.addEventListener('click', async () => {
  standardAudioEnabled = !standardAudioEnabled;
  try { localStorage.setItem(AUDIO_KEY, standardAudioEnabled ? '1' : '0'); } catch (_) {}
  applyStandardAudio();
  if (standardAudioEnabled && !els.standardVideo.paused) {
    try { await els.standardVideo.play(); } catch (_) {}
  }
});

els.standardSeek.addEventListener('input', () => {
  const duration = Number(els.standardVideo.duration || 0);
  const preview = duration * (Number(els.standardSeek.value || 0) / 1000);
  els.standardCurrentTime.textContent = mmss(preview);
});

els.standardSeek.addEventListener('change', seekStandardBySlider);

els.standardVideo.addEventListener('loadeddata', () => {
  els.standardEmpty.style.display = 'none';
  updateStandardProgress();
});

els.standardVideo.addEventListener('timeupdate', updateStandardProgress);
els.standardVideo.addEventListener('play', () => {
  els.standardPlayBtn.textContent = '暂停';
});
els.standardVideo.addEventListener('pause', () => {
  els.standardPlayBtn.textContent = '播放';
});
els.standardVideo.addEventListener('error', () => {
  els.standardEmpty.style.display = 'grid';
});

els.historyFilterBtn.addEventListener('click', async () => {
  const params = new URLSearchParams();
  if (els.historyDanceFilter.value) params.set('dance_type', els.historyDanceFilter.value);
  if (els.historyGradeFilter.value) params.set('grade', els.historyGradeFilter.value);
  if (els.historyKeyword.value.trim()) params.set('keyword', els.historyKeyword.value.trim());
  renderHistory((await fetchJson(`/api/history?${params.toString()}`)).items || []);
});

els.importForm.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const file = els.importFile.files?.[0];
  if (!file) {
    toast('请选择上传文件');
    return;
  }
  const form = new FormData();
  form.append('file', file);
  form.append('dance_type', els.importDanceType.value);
  const resp = await fetch(apiUrl('/api/import/upload'), { method: 'POST', body: form });
  const data = await resp.json();
  els.importResult.textContent = data.message || '导入完成';
});

els.loginBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/login', {
    username: els.loginUsername.value.trim(),
    password: els.loginPassword.value,
  })).message || '登录成功');
  await refreshUser();
});

els.logoutBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/logout', {})).message || '已退出登录');
  await refreshUser();
});

els.registerBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/register', {
    username: els.registerUsername.value.trim(),
    password: els.registerPassword.value,
    role: els.registerRole.value,
  })).message || '注册成功');
  await refreshUser();
});

els.resetPasswordBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/reset_password', {
    username: els.registerUsername.value.trim(),
    password: els.registerPassword.value,
  })).message || '密码已重置');
});

(async function boot() {
  try { backendBaseUrl = (localStorage.getItem(BACKEND_KEY) || '').trim(); } catch (_) { backendBaseUrl = ''; }
  try { standardAudioEnabled = localStorage.getItem(AUDIO_KEY) === '1'; } catch (_) { standardAudioEnabled = false; }
  els.backendBaseUrl.value = backendBaseUrl;
  syncStage();
  applyStandardAudio();
  els.permissionValue.textContent = await detectPermission();
  updateStandardSource(true);
  await prepareStandardVideo(true);
  await listVideoDevices();
  if (els.cameraSelect.options.length) await startPreview();
  await refreshModels();
  await refreshUser();
  connectStream();
})();
