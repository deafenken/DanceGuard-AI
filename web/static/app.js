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
  cfpiTotalBadge: document.getElementById('cfpiTotalBadge'),
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
  countdownFx: document.getElementById('countdownFx'),
  video: document.getElementById('video'),
  videoStage: document.getElementById('videoStage'),
  standardPane: document.getElementById('standardPane'),
  standardVideo: document.getElementById('standardVideo'),
  standardEmpty: document.getElementById('standardEmpty'),
  standardPrimarySurface: document.getElementById('standardPrimarySurface'),
  standardPrimaryVideo: document.getElementById('standardPrimaryVideo'),
  standardPrimaryEmpty: document.getElementById('standardPrimaryEmpty'),
  standardPrimaryControls: document.getElementById('standardPrimaryControls'),
  standardPrimaryProgressShell: document.getElementById('standardPrimaryProgressShell'),
  standardPrimaryProgressBar: document.getElementById('standardPrimaryProgressBar'),
  standardPrimaryCurrentTime: document.getElementById('standardPrimaryCurrentTime'),
  standardPrimaryDuration: document.getElementById('standardPrimaryDuration'),
  standardReplayBtn: document.getElementById('standardReplayBtn'),
  standardPlayBtn: document.getElementById('standardPlayBtn'),
  standardAudioBtn: document.getElementById('standardAudioBtn'),
  standardAudioBtnMini: document.getElementById('standardAudioBtnMini'),
  standardResetBtn: document.getElementById('standardResetBtn'),
  standardProgressBar: document.getElementById('standardProgressBar'),
  standardCurrentTime: document.getElementById('standardCurrentTime'),
  standardDuration: document.getElementById('standardDuration'),
  fullscreenBtn: document.getElementById('fullscreenBtn'),
  swapVideoBtn: document.getElementById('swapVideoBtn'),
  swapVideoBtnMini: document.getElementById('swapVideoBtnMini'),
  fullscreenHint: document.getElementById('fullscreenHint'),
  videoPrimaryLabel: document.getElementById('videoPrimaryLabel'),
  videoPrimarySubtag: document.getElementById('videoPrimarySubtag'),
  videoDebug: document.getElementById('videoDebug'),
  pipSizeHint: document.getElementById('pipSizeHint'),
  pipBoundHint: document.getElementById('pipBoundHint'),
  swapFlash: document.getElementById('swapFlash'),
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
let lastJudgeToken = '';
let countdownRunning = false;
const stageState = {
  swapped: false,
};
let standardPlaying = false;
let standardAudioEnabled = false;
let audioCtx = null;
let resizeState = null;
let standardScrubState = null;
const PIP_STORAGE_KEYS = {
  normal: 'danceguard:pip-width',
  fullscreen: 'danceguard:pip-width-fullscreen',
};
const STANDARD_AUDIO_KEY = 'danceguard:standard-audio-enabled';
try { standardAudioEnabled = localStorage.getItem(STANDARD_AUDIO_KEY) === '1'; } catch (_) {}

const STANDARD_VIDEO_MAP = {
  karaJorga: '/assets/standard/kara-jorga.mp4',
  muqam: '/assets/standard/muqam.mp4',
};

const COUNTDOWN_STEPS = [
  ['3', 520],
  ['2', 520],
  ['1', 520],
  ['\u9884\u5907', 700],
  ['\u5f00\u59cb', 860],
];
const STAGE_BUTTON_ICONS = {
  swap: '<span class="stage-btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 7h9"></path><path d="m14 4 3 3-3 3"></path><path d="M16 17H7"></path><path d="m10 14-3 3 3 3"></path></svg></span>',
  fullscreen: '<span class="stage-btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 4H4v4"></path><path d="M16 4h4v4"></path><path d="M20 16v4h-4"></path><path d="M4 16v4h4"></path></svg></span>',
  shrink: '<span class="stage-btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M9 4H4v5"></path><path d="m4 4 6-6"></path><path d="M15 20h5v-5"></path><path d="m20-4-6 6"></path></svg></span>',
  play: '<span class="stage-mini-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 6v12l9-6z"></path></svg></span>',
  pause: '<span class="stage-mini-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M9 6v12"></path><path d="M15 6v12"></path></svg></span>',
  replay: '<span class="stage-mini-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 12a8 8 0 1 0 2.3-5.7"></path><path d="M4 5v5h5"></path></svg></span>',
  miniSwap: '<span class="stage-mini-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 7h9"></path><path d="m14 4 3 3-3 3"></path><path d="M16 17H7"></path><path d="m10 14-3 3 3 3"></path></svg></span>',
  reset: '<span class="stage-mini-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 6h5"></path><path d="M6 6v5"></path><path d="M18 18h-5"></path><path d="M18 18v-5"></path><path d="M9 15 6 18"></path><path d="M15 9l3-3"></path></svg></span>',
  audioOn: '<span class="stage-btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 15v-6"></path><path d="M9 9 13 6v12l-4-3H5z"></path><path d="M16 10a4 4 0 0 1 0 4"></path><path d="M18.5 7.5a7 7 0 0 1 0 9"></path></svg></span>',
  audioOff: '<span class="stage-btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 15v-6"></path><path d="M9 9 13 6v12l-4-3H5z"></path><path d="m16 9 4 4"></path><path d="m20 9-4 4"></path></svg></span>',
  miniAudioOn: '<span class="stage-mini-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 15v-6"></path><path d="M9 9 13 6v12l-4-3H5z"></path><path d="M16 10a4 4 0 0 1 0 4"></path></svg></span>',
  miniAudioOff: '<span class="stage-mini-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 15v-6"></path><path d="M9 9 13 6v12l-4-3H5z"></path><path d="m16 10 4 4"></path><path d="m20 10-4 4"></path></svg></span>'
};

function setStageActionButton(button, iconKey, label, active = false) {
  if (!button) return;
  button.innerHTML = `${STAGE_BUTTON_ICONS[iconKey] || ''}<span class="stage-btn-label">${label}</span>`;
  button.classList.toggle('is-active', active);
}

function setMiniStageActionButton(button, iconKey, active = false) {
  if (!button) return;
  button.innerHTML = STAGE_BUTTON_ICONS[iconKey] || '';
  button.classList.toggle('is-active', active);
}
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
  panels.forEach((panel) => {
    const active = panel.id === `panel-${name}`;
    panel.classList.toggle('active', active);
    panel.classList.remove('panel-enter');
    if (active) requestAnimationFrame(() => panel.classList.add('panel-enter'));
  });
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

function cfpiTone(score) {
  if (score < 70) return 'error';
  if (score < 85) return 'warn';
  if (score < 92) return 'ok';
  return 'neutral';
}

function culturalBarColor(score) {
  if (score < 70) return 'linear-gradient(90deg, #ff8a7a, #ff5f57)';
  if (score < 85) return 'linear-gradient(90deg, #ffd76a, #ffb340)';
  if (score < 92) return 'linear-gradient(90deg, #71e0af, #32c27d)';
  return 'linear-gradient(90deg, #8b5cff, #1fc8ff)';
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toneContext() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!audioCtx) audioCtx = new Ctx();
  return audioCtx;
}

async function playCueTone(freq = 660, duration = 0.12, gainValue = 0.035) {
  const ctx = toneContext();
  if (!ctx) return;
  if (ctx.state === 'suspended') {
    try { await ctx.resume(); } catch (_) { return; }
  }
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(freq, ctx.currentTime);
  gain.gain.setValueAtTime(0.0001, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(gainValue, ctx.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + duration + 0.02);
}

function standardVideoPath(danceType) {
  return /muqam/i.test(String(danceType || '')) ? STANDARD_VIDEO_MAP.muqam : STANDARD_VIDEO_MAP.karaJorga;
}

function standardVideoNodes() {
  return [stateEls.standardVideo, stateEls.standardPrimaryVideo].filter(Boolean);
}

function standardVideoSnapshot(video) {
  if (!video) return null;
  return {
    src: video.currentSrc || video.src || '',
    datasetSrc: video.dataset?.src || '',
    currentTime: Number(video.currentTime || 0),
    paused: Boolean(video.paused),
    readyState: Number(video.readyState || 0),
    playbackRate: Number(video.playbackRate || 1),
  };
}

function waitForVideoReady(video, timeoutMs = 2400) {
  if (!video) return Promise.resolve(false);
  if (Number(video.readyState || 0) >= 2) return Promise.resolve(true);
  return new Promise((resolve) => {
    let done = false;
    const cleanup = () => {
      video.removeEventListener('loadeddata', onReady);
      video.removeEventListener('canplay', onReady);
      video.removeEventListener('error', onError);
    };
    const finish = (ok) => {
      if (done) return;
      done = true;
      cleanup();
      resolve(ok);
    };
    const onReady = () => finish(true);
    const onError = () => finish(false);
    video.addEventListener('loadeddata', onReady, { once: true });
    video.addEventListener('canplay', onReady, { once: true });
    video.addEventListener('error', onError, { once: true });
    setTimeout(() => finish(Number(video.readyState || 0) >= 2), timeoutMs);
  });
}

async function mirrorStandardVideoState(targetVideo, snapshot) {
  if (!targetVideo || !snapshot?.src) return false;
  const srcChanged = (targetVideo.currentSrc || targetVideo.src || '') !== snapshot.src;
  targetVideo.dataset.src = snapshot.datasetSrc || snapshot.src;
  targetVideo.muted = true;
  targetVideo.loop = true;
  targetVideo.playsInline = true;
  targetVideo.playbackRate = snapshot.playbackRate || 1;
  if (srcChanged) {
    targetVideo.src = snapshot.src;
    targetVideo.load();
  }
  const ready = await waitForVideoReady(targetVideo);
  if (!ready) return false;
  try {
    targetVideo.currentTime = snapshot.currentTime || 0;
  } catch (_) {}
  if (snapshot.paused) {
    targetVideo.pause();
    return true;
  }
  try {
    await targetVideo.play();
    return true;
  } catch (_) {
    return false;
  }
}

function activeStandardVideo() {
  return stageState.swapped ? (stateEls.standardPrimaryVideo || stateEls.standardVideo) : stateEls.standardVideo;
}

function inactiveStandardVideo() {
  return stageState.swapped ? stateEls.standardVideo : stateEls.standardPrimaryVideo;
}

function showStandardPlaceholder(message) {
  if (stateEls.standardEmpty) {
    stateEls.standardEmpty.textContent = message;
    stateEls.standardEmpty.classList.remove('hidden-media');
  }
  if (stateEls.standardPrimaryEmpty) {
    stateEls.standardPrimaryEmpty.textContent = message;
    stateEls.standardPrimaryEmpty.classList.remove('hidden-media');
  }
}

function hideStandardPlaceholder() {
  stateEls.standardEmpty?.classList.add('hidden-media');
  stateEls.standardPrimaryEmpty?.classList.add('hidden-media');
}

function updateStandardPlayButton() {
  if (!stateEls.standardPlayBtn) return;
  setMiniStageActionButton(stateEls.standardPlayBtn, standardPlaying ? 'pause' : 'play', standardPlaying);
}

function updateStandardAudioButtons() {
  setStageActionButton(stateEls.standardAudioBtn, standardAudioEnabled ? 'audioOn' : 'audioOff', '\u4f34\u594f', standardAudioEnabled);
  setMiniStageActionButton(stateEls.standardAudioBtnMini, standardAudioEnabled ? 'miniAudioOn' : 'miniAudioOff', standardAudioEnabled);
}

function applyStandardAudioState() {
  const activeVideo = activeStandardVideo();
  const inactiveVideo = inactiveStandardVideo();
  standardVideoNodes().forEach((video) => {
    if (!video) return;
    video.defaultMuted = true;
    video.volume = 1;
  });
  if (inactiveVideo) {
    inactiveVideo.muted = true;
    inactiveVideo.defaultMuted = true;
  }
  if (activeVideo) {
    activeVideo.muted = !standardAudioEnabled;
    activeVideo.defaultMuted = !standardAudioEnabled;
  }
  updateStandardAudioButtons();
}

async function toggleStandardAudio() {
  standardAudioEnabled = !standardAudioEnabled;
  try { localStorage.setItem(STANDARD_AUDIO_KEY, standardAudioEnabled ? '1' : '0'); } catch (_) {}
  applyStandardAudioState();
  const activeVideo = activeStandardVideo();
  if (standardAudioEnabled && activeVideo?.src) {
    try {
      await activeVideo.play();
      standardPlaying = !activeVideo.paused;
    } catch (_) {}
  }
  updateStandardPlayButton();
}

function updateStandardProgress(preview = null) {
  const activeVideo = activeStandardVideo();
  if (!activeVideo) return;
  const duration = Number(activeVideo.duration || 0);
  const current = preview && Number.isFinite(preview.current) ? Number(preview.current) : Number(activeVideo.currentTime || 0);
  const ratio = preview && Number.isFinite(preview.ratio) ? Math.max(0, Math.min(1, Number(preview.ratio))) : (duration > 0 ? Math.max(0, Math.min(1, current / duration)) : 0);
  const width = `${(ratio * 100).toFixed(2)}%`;
  if (stateEls.standardProgressBar) stateEls.standardProgressBar.style.width = width;
  if (stateEls.standardPrimaryProgressBar) stateEls.standardPrimaryProgressBar.style.width = width;
  const currentText = mmss(Math.floor(current));
  const durationText = mmss(Math.floor(duration));
  if (stateEls.standardCurrentTime) stateEls.standardCurrentTime.textContent = currentText;
  if (stateEls.standardDuration) stateEls.standardDuration.textContent = durationText;
  if (stateEls.standardPrimaryCurrentTime) stateEls.standardPrimaryCurrentTime.textContent = currentText;
  if (stateEls.standardPrimaryDuration) stateEls.standardPrimaryDuration.textContent = durationText;
}

function syncInactiveStandardVideoPosition(force = false) {
  const activeVideo = activeStandardVideo();
  const inactiveVideo = inactiveStandardVideo();
  if (!activeVideo?.src || !inactiveVideo?.src) return;
  const activeTime = Number(activeVideo.currentTime || 0);
  const inactiveTime = Number(inactiveVideo.currentTime || 0);
  if (!force && Math.abs(activeTime - inactiveTime) < 0.22) return;
  try {
    inactiveVideo.currentTime = activeTime;
  } catch (_) {}
}

function syncInactiveStandardVideoPlayback() {
  const activeVideo = activeStandardVideo();
  const inactiveVideo = inactiveStandardVideo();
  if (!activeVideo?.src || !inactiveVideo?.src) return;
  inactiveVideo.muted = true;
  inactiveVideo.defaultMuted = true;
  inactiveVideo.playbackRate = activeVideo.playbackRate || 1;
  inactiveVideo.pause();
}

function seekVideoToTime(video, timeSec) {
  if (!video) return false;
  const target = Math.max(0, Math.min(Number(video.duration || 0), Number(timeSec || 0)));
  if (!Number.isFinite(target)) return false;
  try {
    video.currentTime = target;
    return true;
  } catch (_) {
    return false;
  }
}


function seekStandardVideoByRatio(ratio) {
  const activeVideo = activeStandardVideo();
  if (!activeVideo?.duration) return false;
  const clamped = Math.max(0, Math.min(1, ratio));
  const targetTime = clamped * activeVideo.duration;
  const inactiveVideo = inactiveStandardVideo();
  if (inactiveVideo?.src) {
    inactiveVideo.pause();
    inactiveVideo.playbackRate = Number(activeVideo.playbackRate || 1);
  }
  const ok = seekVideoToTime(activeVideo, targetTime);
  if (!ok) return false;
  updateStandardProgress();
  return true;
}

function progressRatioFromEvent(ev, shell) {
  const rect = shell.getBoundingClientRect();
  if (!rect.width) return 0;
  return Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
}

function beginStandardScrub(ev) {
  const shell = ev.target.closest('#standardPrimaryProgressShell, .standard-progress-shell');
  if (!shell) return;
  ev.preventDefault();
  ev.stopPropagation();
  const activeVideo = activeStandardVideo();
  if (!activeVideo?.duration) return;
  standardScrubState = {
    shell,
    wasPlaying: !activeVideo.paused,
    activeVideo,
  };
  activeVideo.pause();
  const ratio = progressRatioFromEvent(ev, shell);
  const previewTime = ratio * Number(activeVideo.duration || 0);
  updateStandardProgress({ ratio, current: previewTime });
  shell.classList.add('is-scrubbing');
  document.body.style.userSelect = 'none';
}

function updateStandardScrub(ev) {
  if (!standardScrubState) return;
  const ratio = progressRatioFromEvent(ev, standardScrubState.shell);
  const previewTime = ratio * Number(standardScrubState.activeVideo.duration || 0);
  standardScrubState.ratio = ratio;
  standardScrubState.previewTime = previewTime;
  updateStandardProgress({ ratio, current: previewTime });
}

async function endStandardScrub() {
  if (!standardScrubState) return;
  const state = standardScrubState;
  standardScrubState = null;
  state.shell?.classList.remove('is-scrubbing');
  document.body.style.userSelect = '';
  const ratio = Number.isFinite(state.ratio) ? state.ratio : (Number(state.activeVideo.currentTime || 0) / Math.max(1, Number(state.activeVideo.duration || 1)));
  const ok = seekStandardVideoByRatio(ratio);
  if (ok && state.wasPlaying) {
    try { await state.activeVideo.play(); } catch (_) {}
  }
  updateStandardProgress();
}

function isVideoStageFullscreen() {
  return document.fullscreenElement === stateEls.videoStage;
}

function currentVideoStageState() {
  return {
    fullscreen: isVideoStageFullscreen(),
    swapped: stageState.swapped,
  };
}

function syncVideoStageState() {
  const state = currentVideoStageState();
  stateEls.videoStage?.classList.toggle('fullscreen-active', state.fullscreen);
  stateEls.videoStage?.classList.toggle('stage-swapped', state.swapped);
  stateEls.video?.parentElement?.classList.toggle('is-primary', !state.swapped);
  stateEls.video?.parentElement?.classList.toggle('is-secondary', state.swapped);
  stateEls.standardPane?.classList.toggle('is-primary', state.swapped);
  stateEls.standardPane?.classList.toggle('is-secondary', !state.swapped);
  setStageActionButton(stateEls.fullscreenBtn, state.fullscreen ? 'shrink' : 'fullscreen', state.fullscreen ? '\u9000\u51fa\u5168\u5c4f' : '\u5168\u5c4f', state.fullscreen);
  stateEls.fullscreenHint?.classList.toggle('hidden', !state.fullscreen);
  updateSwapButtons(state);
  updatePrimaryStageMeta(state);
  applyStandardAudioState();
  stateEls.standardPrimaryControls?.classList.toggle('is-visible', state.swapped);
  if (stateEls.videoDebug && stateEls.videoStage) {
    const normalWidth = getComputedStyle(stateEls.videoStage).getPropertyValue('--pip-width').trim() || '--';
    const fullscreenWidth = getComputedStyle(stateEls.videoStage).getPropertyValue('--pip-width-fullscreen').trim() || '--';
    const pipOwner = state.swapped ? 'live' : 'standard';
    const primaryOwner = state.swapped ? 'standard' : 'live';
    stateEls.videoDebug.textContent = `FS:${state.fullscreen ? 1 : 0} | SW:${state.swapped ? 1 : 0} | PRIMARY:${primaryOwner} | PIP:${pipOwner} | N:${normalWidth} | F:${fullscreenWidth}`;
  }
}

function updateSwapButtons(state = currentVideoStageState()) {
  const label = state.swapped ? '\u6062\u590d\u5e03\u5c40' : '\u4ea4\u6362\u753b\u9762';
  setStageActionButton(stateEls.swapVideoBtn, 'swap', label, state.swapped);
  setMiniStageActionButton(stateEls.swapVideoBtnMini, 'miniSwap', state.swapped);
}
function updatePrimaryStageMeta(state = currentVideoStageState()) {
  if (!stateEls.videoPrimaryLabel || !stateEls.videoPrimarySubtag) return;
  if (state.swapped) {
    stateEls.videoPrimaryLabel.textContent = 'Standard Demo';
    stateEls.videoPrimarySubtag.textContent = stateEls.danceType?.value || 'Standard Reference';
  } else {
    stateEls.videoPrimaryLabel.textContent = 'Live Capture';
    stateEls.videoPrimarySubtag.innerHTML = 'OBS / &#x4e91;&#x666f;&#x865a;&#x62df;&#x6444;&#x50cf;&#x5934;';
  }
}

function activePipVarName() {
  return isVideoStageFullscreen() ? '--pip-width-fullscreen' : '--pip-width';
}
function activePipStorageKey() {
  return isVideoStageFullscreen() ? PIP_STORAGE_KEYS.fullscreen : PIP_STORAGE_KEYS.normal;
}
let pipHintTimer = null;

function clearPipStateFlags() {
  stateEls.videoStage?.classList.remove('pip-bound-min', 'pip-bound-max', 'pip-reset');
}

function flashPipStateFlag(flag) {
  if (!stateEls.videoStage) return;
  clearPipStateFlags();
  if (!flag) return;
  stateEls.videoStage.classList.add(flag);
  setTimeout(() => stateEls.videoStage?.classList.remove(flag), 720);
}

function showPipHint(width, bound = '') {
  if (stateEls.pipSizeHint) {
    stateEls.pipSizeHint.textContent = `${Math.round(width)} px`;
    stateEls.pipSizeHint.classList.remove('hidden');
  }
  if (stateEls.pipBoundHint) {
    if (bound) {
      if (bound === 'min') {
        stateEls.pipBoundHint.textContent = '\u5df2\u8fbe\u6700\u5c0f\u5c3a\u5bf8';
        flashPipStateFlag('pip-bound-min');
      } else if (bound === 'max') {
        stateEls.pipBoundHint.textContent = '\u5df2\u8fbe\u6700\u5927\u5c3a\u5bf8';
        flashPipStateFlag('pip-bound-max');
      } else if (bound === 'reset') {
        stateEls.pipBoundHint.textContent = '\u5df2\u6062\u590d\u9ed8\u8ba4\u5927\u5c0f';
        flashPipStateFlag('pip-reset');
      }
      stateEls.pipBoundHint.classList.remove('hidden');
    } else {
      stateEls.pipBoundHint.classList.add('hidden');
      clearPipStateFlags();
    }
  }
  clearTimeout(pipHintTimer);
  pipHintTimer = setTimeout(() => {
    stateEls.pipSizeHint?.classList.add('hidden');
    stateEls.pipBoundHint?.classList.add('hidden');
    clearPipStateFlags();
  }, 900);
}

function playSwapFlash() {
  if (!stateEls.swapFlash) return;
  stateEls.swapFlash.classList.remove('hidden', 'show');
  void stateEls.swapFlash.offsetWidth;
  stateEls.swapFlash.classList.add('show');
  setTimeout(() => stateEls.swapFlash?.classList.add('hidden'), 420);
}

function beginPipResize(ev) {
  const handle = ev.target.closest('.pip-resize-handle');
  if (!handle || !stateEls.videoStage) return;
  ev.preventDefault();
  const pane = handle.parentElement;
  const rect = pane.getBoundingClientRect();
  resizeState = {
    startX: ev.clientX,
    startWidth: rect.width,
    varName: activePipVarName(),
    storageKey: activePipStorageKey(),
    pane,
  };
  pane.classList.add('is-resizing');
  document.body.style.userSelect = 'none';
}

function updatePipResize(ev) {
  if (!resizeState || !stateEls.videoStage) return;
  const stageRect = stateEls.videoStage.getBoundingClientRect();
  const maxWidth = Math.min(stageRect.width * 0.48, isVideoStageFullscreen() ? 520 : 360);
  const minWidth = isVideoStageFullscreen() ? 260 : 180;
  const rawWidth = resizeState.startWidth + (ev.clientX - resizeState.startX);
  const width = Math.max(minWidth, Math.min(maxWidth, rawWidth));
  stateEls.videoStage.style.setProperty(resizeState.varName, `${width}px`);
  try { localStorage.setItem(resizeState.storageKey, String(Math.round(width))); } catch (_) {}
  showPipHint(width, rawWidth <= minWidth ? 'min' : rawWidth >= maxWidth ? 'max' : '');
}

function endPipResize() {
  if (!resizeState) return;
  resizeState.pane?.classList.remove('is-resizing');
  resizeState = null;
  document.body.style.userSelect = '';
}


async function toggleVideoSwap() {
  const sourceVideo = activeStandardVideo();
  const sourceSnapshot = standardVideoSnapshot(sourceVideo);
  stageState.swapped = !stageState.swapped;
  const targetVideo = activeStandardVideo();
  endPipResize();
  clearPipStateFlags();
  stateEls.pipSizeHint?.classList.add("hidden");
  stateEls.pipBoundHint?.classList.add("hidden");
  ensurePipWidthForCurrentMode();
  if (sourceVideo && targetVideo && sourceVideo !== targetVideo && sourceSnapshot?.src) {
    const mirrored = await mirrorStandardVideoState(targetVideo, sourceSnapshot);
    if (!mirrored && !sourceSnapshot.paused) {
      await playStandardVideo();
    }
  }
  syncVideoStageState();
  updateStandardProgress();
  if (isVideoStageFullscreen() && stateEls.videoStage) {
    void stateEls.videoStage.offsetWidth;
    requestAnimationFrame(async () => {
      if (sourceSnapshot?.src) {
        await mirrorStandardVideoState(activeStandardVideo(), sourceSnapshot);
      }
      syncVideoStageState();
      updateStandardProgress();
    });
  }
  playSwapFlash();
}

function defaultPipWidthForCurrentMode() {
  const fullscreen = isVideoStageFullscreen();
  const stageWidth = stateEls.videoStage?.getBoundingClientRect().width || 0;
  const fallback = fullscreen ? 420 : 280;
  if (!stageWidth) return fallback;
  return Math.round(Math.min(stageWidth * (fullscreen ? 0.34 : 0.31), fullscreen ? 520 : 280));
}

function resetPipSize() {
  if (!stateEls.videoStage) return;
  const width = defaultPipWidthForCurrentMode();
  stateEls.videoStage.style.setProperty(activePipVarName(), `${width}px`);
  try { localStorage.setItem(activePipStorageKey(), String(width)); } catch (_) {}
  showPipHint(width, 'reset');
}

function applyStoredPipWidths() {
  if (!stateEls.videoStage) return;
  try {
    const normalWidth = Number(localStorage.getItem(PIP_STORAGE_KEYS.normal) || 0);
    const fullscreenWidth = Number(localStorage.getItem(PIP_STORAGE_KEYS.fullscreen) || 0);
    if (Number.isFinite(normalWidth) && normalWidth > 0) {
      stateEls.videoStage.style.setProperty('--pip-width', `${normalWidth}px`);
    }
    if (Number.isFinite(fullscreenWidth) && fullscreenWidth > 0) {
      stateEls.videoStage.style.setProperty('--pip-width-fullscreen', `${fullscreenWidth}px`);
    }
  } catch (_) {}
}

function ensurePipWidthForCurrentMode() {
  if (!stateEls.videoStage) return;
  const varName = activePipVarName();
  const currentValue = getComputedStyle(stateEls.videoStage).getPropertyValue(varName).trim();
  if (currentValue) return;
  const width = defaultPipWidthForCurrentMode();
  stateEls.videoStage.style.setProperty(varName, `${width}px`);
  try { localStorage.setItem(activePipStorageKey(), String(width)); } catch (_) {}
}

async function requestVideoFullscreenChange() {
  if (!stateEls.videoStage) return;
  if (isVideoStageFullscreen()) {
    await document.exitFullscreen();
  } else {
    await stateEls.videoStage.requestFullscreen();
  }
}

async function toggleVideoFullscreen() {
  if (!stateEls.videoStage) return;
  endPipResize();
  clearPipStateFlags();
  stateEls.pipSizeHint?.classList.add('hidden');
  stateEls.pipBoundHint?.classList.add('hidden');
  try {
    await requestVideoFullscreenChange();
  } catch (_) {
    ensurePipWidthForCurrentMode();
    syncVideoStageState();
  }
}


function updateStandardVideoSource(force = false) {
  const videos = standardVideoNodes();
  if (!videos.length) return;
  const src = standardVideoPath(stateEls.danceType.value);
  if (!force && videos.every((video) => video.dataset.src === src)) return;
  videos.forEach((video) => {
    video.dataset.src = src;
    video.src = src;
    video.load();
  });
  showStandardPlaceholder(`未找到标准视频：${src.split("/").pop()}`);
}

async function prepareStandardVideo() {
  updateStandardVideoSource();
  const videos = standardVideoNodes();
  if (!videos.length || !videos[0]?.src) return false;
  try {
    videos.forEach((video) => {
      video.pause();
      video.currentTime = 0;
    });
    await Promise.all(videos.map((video) => waitForVideoReady(video)));
    standardPlaying = false;
    applyStandardAudioState();
    updateStandardPlayButton();
    updateStandardProgress();
    return true;
  } catch (_) {
    showStandardPlaceholder("\u6807\u51c6\u89c6\u9891\u51c6\u5907\u5931\u8d25");
    return false;
  }
}

async function playStandardVideo() {
  const activeVideo = activeStandardVideo();
  if (!activeVideo?.src) return false;
  try {
    const ready = await waitForVideoReady(activeVideo);
    if (!ready) return false;
    applyStandardAudioState();
    const otherVideo = inactiveStandardVideo();
    if (otherVideo?.src) {
      otherVideo.pause();
    }
    await activeVideo.play();
    standardPlaying = true;
    updateStandardPlayButton();
    return true;
  } catch (_) {
    standardPlaying = false;
    updateStandardPlayButton();
    showStandardPlaceholder("\u6807\u51c6\u89c6\u9891\u9700\u8981\u7528\u6237\u4ea4\u4e92\u540e\u624d\u80fd\u64ad\u653e");
    return false;
  }
}

async function toggleStandardPlayback() {
  const activeVideo = activeStandardVideo();
  if (!activeVideo?.src) return;
  if (activeVideo.paused) {
    await playStandardVideo();
  } else {
    activeVideo.pause();
    inactiveStandardVideo()?.pause();
    standardPlaying = false;
    updateStandardPlayButton();
  }
}

async function replayStandardVideo() {
  const activeVideo = activeStandardVideo();
  if (!activeVideo?.src) return;
  seekVideoToTime(activeVideo, 0);
  const otherVideo = inactiveStandardVideo();
  if (otherVideo?.src) {
    try { otherVideo.currentTime = 0; } catch (_) {}
    otherVideo.pause();
  }
  updateStandardProgress();
  await playStandardVideo();
}

function flashElement(el, text, hold = 900) {
  if (!el) return;
  el.textContent = text;
  el.classList.remove('hidden', 'show', 'countdown-pop');
  void el.offsetWidth;
  el.classList.add('show');
  setTimeout(() => el.classList.add('hidden'), hold);
}

async function runCountdownSequence() {
  if (countdownRunning || !stateEls.countdownFx) return;
  countdownRunning = true;
  for (let i = 0; i < COUNTDOWN_STEPS.length; i += 1) {
    const [label, hold] = COUNTDOWN_STEPS[i];
    stateEls.countdownFx.textContent = label;
    stateEls.countdownFx.classList.remove('hidden', 'show', 'countdown-pop');
    void stateEls.countdownFx.offsetWidth;
    stateEls.countdownFx.classList.add('show', 'countdown-pop');
    const freq = i < 3 ? 620 + (2 - i) * 70 : i === 3 ? 720 : 860;
    playCueTone(freq, i === COUNTDOWN_STEPS.length - 1 ? 0.18 : 0.12, i === COUNTDOWN_STEPS.length - 1 ? 0.05 : 0.035);
    if (i === COUNTDOWN_STEPS.length - 1) await playStandardVideo();
    await wait(hold);
  }
  stateEls.countdownFx.classList.remove('show', 'countdown-pop');
  stateEls.countdownFx.classList.add('hidden');
  countdownRunning = false;
}

function rankTone(rank) {
  const value = String(rank || 'IDLE').toUpperCase();
  if (value === 'PERFECT') return 'ok';
  if (value === 'GREAT') return 'neutral';
  if (value === 'GOOD') return 'warn';
  if (value === 'WARN') return 'error';
  return 'neutral';
}

function applyStateSnapshot(payload) {
  const snap = payload?.state || {};
  const feed = payload?.feed || [];
  const record = payload?.record || {};
  renderFeed(feed);
  const token = JSON.stringify([snap.active, snap.last_update, snap.score, snap.rank, snap.combo, snap.best_combo, snap.feedback, snap.elapsed_sec, snap.dance_type, snap.weakest_joint, record.bvh, record.npy]);
  if (token === lastStateToken) return;
  lastStateToken = token;

  const score = Number(snap.score || 0);
  const rank = String(snap.rank || 'IDLE').toUpperCase();
  const feedback = snap.feedback || '\u7b49\u5f85\u5f00\u59cb';
  const weakest = snap.weakest_joint || '--';
  const combo = Number(snap.combo || 0);
  const bestCombo = Number(snap.best_combo || 0);
  const metrics = snap.vmc_metrics || {};
  const cfpi = snap.cfpi || {};
  const cfpiDimensions = cfpi.dimensions || {};
  const cfpiCultural = cfpi.cultural_features || {};
  const scoreText = Number.isFinite(score) ? String(Math.round(score)) : '0';

  stateEls.timerValue.textContent = mmss(Number(snap.elapsed_sec || 0));
  stateEls.scoreValue.textContent = scoreText;
  stateEls.scoreBar.style.width = `${Math.max(0, Math.min(100, score))}%`;
  stateEls.scoreBar.style.background = scoreColor(score);
  stateEls.rankPill.textContent = rank;
  stateEls.rankPill.className = `pill status-${rankTone(rank)}`;
  if (stateEls.cfpiTotalBadge) {
    const cfpiTotal = Number(cfpi.total || score);
    stateEls.cfpiTotalBadge.textContent = `CFPI ${cfpiTotal.toFixed(1)}`;
    stateEls.cfpiTotalBadge.className = `pill status-${cfpiTone(cfpiTotal)}`;
  }
  stateEls.danceValue.textContent = snap.dance_type || '\u672a\u542f\u52a8';
  stateEls.bestCombo.textContent = String(bestCombo);
  stateEls.feedbackValue.textContent = feedback;
  stateEls.weakestJointValue.textContent = weakest;
  stateEls.scoreFocusValue.textContent = scoreText;
  stateEls.scoreFocusBar.style.width = `${Math.max(0, Math.min(100, score))}%`;
  stateEls.scoreFocusBar.style.background = scoreColor(score);
  stateEls.scoreFocusRank.textContent = rank;
  stateEls.scoreFocusFeedback.textContent = feedback;
  stateEls.scoreFocusCombo.textContent = String(combo);
  stateEls.scoreFocusWeakest.textContent = weakest;
  stateEls.scoreCfpiAccuracy.textContent = Number(cfpiDimensions.accuracy || 0).toFixed(1);
  stateEls.scoreCfpiRhythm.textContent = Number(cfpiDimensions.rhythm || 0).toFixed(1);
  stateEls.scoreCfpiFluency.textContent = Number(cfpiDimensions.fluency || 0).toFixed(1);
  stateEls.scoreCfpiExpression.textContent = Number(cfpiDimensions.expression || 0).toFixed(1);
  const neckScore = Number(cfpiCultural.neck_shift || 0);
  const wristScore = Number(cfpiCultural.wrist_flip || 0);
  const shoulderScore = Number(cfpiCultural.shoulder_shimmy || 0);
  const hatScore = Number(cfpiCultural.hat_hold || 0);
  if (stateEls.cfpiLiveNeck) { stateEls.cfpiLiveNeck.style.width = `${Math.max(0, Math.min(100, neckScore))}%`; stateEls.cfpiLiveNeck.style.background = culturalBarColor(neckScore); stateEls.cfpiLiveNeckValue.textContent = neckScore.toFixed(1); }
  if (stateEls.cfpiLiveWrist) { stateEls.cfpiLiveWrist.style.width = `${Math.max(0, Math.min(100, wristScore))}%`; stateEls.cfpiLiveWrist.style.background = culturalBarColor(wristScore); stateEls.cfpiLiveWristValue.textContent = wristScore.toFixed(1); }
  if (stateEls.cfpiLiveShoulder) { stateEls.cfpiLiveShoulder.style.width = `${Math.max(0, Math.min(100, shoulderScore))}%`; stateEls.cfpiLiveShoulder.style.background = culturalBarColor(shoulderScore); stateEls.cfpiLiveShoulderValue.textContent = shoulderScore.toFixed(1); }
  if (stateEls.cfpiLiveHat) { stateEls.cfpiLiveHat.style.width = `${Math.max(0, Math.min(100, hatScore))}%`; stateEls.cfpiLiveHat.style.background = culturalBarColor(hatScore); stateEls.cfpiLiveHatValue.textContent = hatScore.toFixed(1); }
  stateEls.userValue.textContent = `${snap.current_user || '\u6e38\u5ba2'} / ${snap.current_role || '\u5b66\u751f'}`;
  stateEls.vmcValue.textContent = `${snap.host || '0.0.0.0'}:${snap.port || 39539}`;
  stateEls.recordValue.textContent = record.bvh || record.npy || '\u5c1a\u672a\u751f\u6210';
  stateEls.lastImportValue.textContent = snap.last_import_path ? String(snap.last_import_path).split(/[\\/]/).pop() : '\u5c1a\u672a\u5bfc\u5165';
  stateEls.vmcFpsValue.textContent = `${Number(metrics.fps || 0).toFixed(2)} fps`;
  stateEls.vmcBoneCountValue.textContent = String(metrics.bone_count || 0);
  stateEls.vmcPacketCountValue.textContent = String(metrics.packet_count || 0);
  stateEls.serverDeviceSummary.innerHTML = `<span class="status-dot ${metrics.connected ? 'live' : 'idle'}"></span>${metrics.connected ? '\u540e\u7aef VMC \u5df2\u63a5\u901a' : '\u7b49\u5f85 VMC \u6570\u636e\u6d41\u8fdb\u5165'}`;
  setStatus(stateEls.sessionState, snap.active ? '\u5b9e\u65f6\u8bc4\u4f30\u4e2d' : '\u5f85\u673a', snap.active ? 'ok' : 'neutral');
  setStatus(stateEls.modelStatus, snap.model_status || '\u672a\u52a0\u8f7d', snap.model_status === '\u771f\u5b9e\u6a21\u578b' ? 'ok' : snap.model_status === '\u964d\u7ea7\u8bc4\u5206' ? 'warn' : 'neutral');

  if (snap.active) {
    if (!scoreSeries.length || scoreSeries[scoreSeries.length - 1] !== score) pushScorePoint(score);
    const judgeToken = `${rank}|${combo}|${snap.last_update}`;
    if (judgeToken !== lastJudgeToken) {
      lastJudgeToken = judgeToken;
      flashElement(stateEls.judgeFx, rank, 900);
      if (combo > 0) flashElement(stateEls.comboFx, `COMBO x${combo}`, 900);
      if (rank === 'PERFECT' && Date.now() - lastPerfectAt > 3000) {
        lastPerfectAt = Date.now();
        flashElement(stateEls.perfectFx, 'PERFECT!', 1000);
      }
    }
  } else {
    lastJudgeToken = '';
    [stateEls.judgeFx, stateEls.comboFx, stateEls.perfectFx, stateEls.countdownFx].forEach((el) => el && el.classList.add('hidden'));
  }
}

function connectStream() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource('/api/stream');
  eventSource.addEventListener('state', (ev) => {
    try {
      applyStateSnapshot(JSON.parse(ev.data));
    } catch (_) {}
  });
  eventSource.addEventListener('history', async (ev) => {
    try {
      const items = JSON.parse(ev.data);
      renderHistory(items || []);
      if (activeHistoryId) await loadHistoryDetail(activeHistoryId);
    } catch (_) {}
  });
  eventSource.addEventListener('imports', (ev) => {
    try {
      renderImports(JSON.parse(ev.data) || []);
    } catch (_) {}
  });
  eventSource.onerror = () => {
    if (eventSource) eventSource.close();
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectStream();
    }, 1500);
  };
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
    stateEls.historyDetail.innerHTML = '<div class="section-eyebrow">Record Detail</div><h3>选择一条历史记录</h3><p>展开后可查看平均分、CFPI 维度、关节级分析和原始文件。</p><div class="history-preview">暂无截图预览</div>';
    return;
  }
  const score = Number(item.avg_score || 0);
  const gradeTone = item.grade === 'S' ? 'ok' : item.grade === 'A' ? 'neutral' : item.grade === 'B' ? 'warn' : 'error';
  const preview = item.summary_image_url ? `<div class="history-preview has-image"><img src="${item.summary_image_url}" alt="历史截图"></div>` : '<div class="history-preview">暂无截图预览</div>';
  const joints = (item.analysis?.joint_scores || []).map((x) => `<div class="analysis-row"><span>${x.joint}</span><div class="analysis-bar"><i style="width:${Math.max(6, Number(x.score) || 0)}%"></i></div><em>${Number(x.score || 0).toFixed(1)}</em></div>`).join('');
  const segments = (item.analysis?.segments || []).map((x) => `<div class="analysis-row"><span>片段 ${x.index}</span><div class="analysis-bar energy"><i style="width:${Math.max(6, Math.min(100, Number(x.energy || 0) * 2000 + 8))}%"></i></div><em>${x.start_sec}-${x.end_sec}s</em></div>`).join('');
  const cfpi = item.analysis?.cfpi || {};
  const cfpiDimensions = Object.entries(cfpi.dimensions || {}).map(([key, value]) => {
    const labelMap = { accuracy: '动作准确度', rhythm: '节奏同步性', fluency: '流畅度', expression: '表现力' };
    const label = labelMap[key] || key;
    return `<div class="analysis-row"><span>${label}</span><div class="analysis-bar cfpi"><i style="width:${Math.max(6, Number(value) || 0)}%"></i></div><em>${Number(value).toFixed(1)}</em></div>`;
  }).join('');
  const cfpiComponents = Object.entries(cfpi.components || {}).map(([key, value]) => {
    const labelMap = { joint_angle: '关键角度', trajectory: '空间轨迹', cultural: '文化动作', beat: '节拍匹配', accent: '重音对齐', smoothness: '转换平滑', stability: '速度稳定', extension: '肢体舒展', expression: '情感强度' };
    const label = labelMap[key] || key;
    return `<div class="analysis-row compact"><span>${label}</span><div class="analysis-bar cfpi-sub"><i style="width:${Math.max(6, Number(value) || 0)}%"></i></div><em>${Number(value).toFixed(1)}</em></div>`;
  }).join('');
  const culturalFeatures = Object.entries(cfpi.cultural_features || {}).map(([key, value]) => {
    const labelMap = { neck_shift: '移颈', wrist_flip: '翻腕', shoulder_shimmy: '抖肩', hat_hold: '托帽' };
    const label = labelMap[key] || key;
    return `<div class="analysis-row compact"><span>${label}</span><div class="analysis-bar cultural"><i style="width:${Math.max(6, Number(value) || 0)}%"></i></div><em>${Number(value).toFixed(1)}</em></div>`;
  }).join('');
  stateEls.historyDetail.className = 'history-detail';
  stateEls.historyDetail.innerHTML = `
    <div class="detail-header"><div><div class="section-eyebrow">Record Detail</div><h3>${item.dance_type} / ${item.grade}</h3><p>${item.created_at}</p></div><div class="detail-badges"><span class="pill status-${gradeTone}">${item.grade} 等级</span><span class="pill status-neutral">均分 ${score.toFixed(1)}</span><span class="pill status-ok">CFPI ${Number(cfpi.total || score).toFixed(1)}</span></div></div>
    ${preview}
    <div class="history-detail-grid">
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 4v16"></path><path d="M7 9h10"></path><path d="M9 15h6"></path></svg></span>平均分</span><strong>${score.toFixed(1)}</strong></div>
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M13 3 6 13h5l-1 8 8-11h-5l0-7z"></path></svg></span>最高连击</span><strong>${item.best_combo || 0}</strong></div>
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 5v7l4 2"></path><circle cx="12" cy="12" r="8"></circle></svg></span>舞蹈时长</span><strong>${mmss(item.duration_sec || 0)}</strong></div>
      <div class="mini-card"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"></circle><path d="M12 9v3l2 2"></path></svg></span>最弱关节</span><strong>${item.analysis?.worst_joint || '未知'}</strong></div>
    </div>
    <div class="mini-card report-card" style="margin-top:12px;"><span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 8h14"></path><path d="M5 12h10"></path><path d="M5 16h8"></path></svg></span>评估报告</span><strong>${item.summary_report || item.record_text || '暂无说明'}</strong></div>
    <div class="section-eyebrow" style="margin-top:16px;">CFPI 四维指标</div>
    <div class="analysis-grid">${cfpiDimensions || '<div class="mini-card"><span>暂无</span><strong>无 CFPI 维度数据</strong></div>'}</div>
    <div class="section-eyebrow" style="margin-top:16px;">CFPI 分项指标</div>
    <div class="analysis-grid">${cfpiComponents || '<div class="mini-card"><span>暂无</span><strong>无 CFPI 分项数据</strong></div>'}</div>
    <div class="section-eyebrow" style="margin-top:16px;">文化特征完成度</div>
    <div class="analysis-grid">${culturalFeatures || '<div class="mini-card"><span>暂无</span><strong>无文化特征数据</strong></div>'}</div>
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
    const lines = [
      `舞种: ${item.dance_type}`,
      `等级: ${item.grade}`,
      `平均分: ${score.toFixed(1)}`,
      `CFPI 主评分: ${Number(cfpi.total || score).toFixed(1)}`,
      `最弱关节: ${item.analysis?.worst_joint || '未知'}`,
      `报告: ${item.summary_report || item.record_text || '暂无说明'}`,
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
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
  stateEls.modelList.innerHTML = items.map((item) => `<article class="mini-card model-card ${item.exists ? 'ok' : 'warn'}"><div class="model-head"><span class="model-badge ${item.exists ? 'ok' : 'warn'}"></span><span class="model-code">${item.code}</span><span class="pill ${item.exists ? 'status-ok' : 'status-warn'}">${item.exists ? 'READY' : 'MISSING'}</span></div><strong>${item.name}</strong><p class="card-subline">${item.desc}</p><p class="model-path"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="5" y="6" width="14" height="12" rx="3"></rect><path d="M10 10h4"></path><path d="M10 14h4"></path></svg></span><span>权重：${item.weight}</span></p><em class="model-state ${item.exists ? 'ok' : 'warn'}">${item.exists ? '权重已就绪，可进入实时评分' : '缺少权重文件，当前将降级评分'}</em></article>`).join('');
}

function renderUsers(items, state) {
  stateEls.accountState.innerHTML = `<span class="status-dot ${state.current_user && state.current_user !== '游客' ? 'live' : 'idle'}"></span>${state.current_user || '游客'} / ${state.current_role || '学生'}`;
  stateEls.userList.innerHTML = items.map((item) => `<article class="device-item user-card"><header><strong>${item.username}</strong><small><span class="pill ${item.role === '管理员' ? 'status-error' : item.role === '教师' ? 'status-warn' : 'status-neutral'}">${item.role}</span></small></header><p class="card-subline">创建时间：${item.created_at}</p><p>最近登录：${item.last_login || '从未登录'}</p></article>`).join('');
}

async function listVideoDevices() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    setStatus(stateEls.videoStatus, '浏览器不支持设备枚举', 'error');
    stateEls.videoHint.textContent = '当前浏览器没有提供 mediaDevices.enumerateDevices。请改用较新的 Chrome 或 Edge。';
    stateEls.cameraCountValue.textContent = '0';
    stateEls.activeCameraValue.textContent = '不可用';
    stateEls.deviceList.innerHTML = '<article class="device-item device-normal"><header><strong>设备枚举不可用</strong><small><span class="device-badge normal">ERR</span>Browser</small></header><p>当前浏览器不支持本地视频设备检测。</p></article>';
    return;
  }
  try {
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
    stateEls.deviceList.innerHTML = cameraDevices.map((cam, index) => `<article class="device-item ${/obs|virtual/i.test(cam.label || '') ? 'device-obs' : 'device-normal'}"><header><strong>${cam.label || `摄像头 ${index + 1}`}</strong><small><span class="device-badge ${/obs|virtual/i.test(cam.label || '') ? 'obs' : 'normal'}">${/obs|virtual/i.test(cam.label || '') ? 'OBS' : 'CAM'}</span>${/obs|virtual/i.test(cam.label || '') ? '候选 OBS 虚拟摄像头' : '普通视频设备'}</small></header><p>deviceId: ${cam.deviceId || '无'}</p></article>`).join('') || '<article class="device-item device-normal"><header><strong>未检测到设备</strong><small><span class="device-badge normal">CAM</span>Empty</small></header><p>请确认浏览器权限已授予，或 OBS 虚拟摄像头已经启动。</p></article>';
  } catch (err) {
    setStatus(stateEls.videoStatus, '识别设备失败', 'error');
    stateEls.videoHint.textContent = `设备枚举失败：${err?.message || '未知错误'}。请先授予浏览器摄像头权限，再刷新设备。`;
    stateEls.cameraCountValue.textContent = '0';
    stateEls.activeCameraValue.textContent = '失败';
    stateEls.deviceList.innerHTML = `<article class="device-item device-normal"><header><strong>设备识别失败</strong><small><span class="device-badge normal">ERR</span>Enum</small></header><p>${err?.message || '未知错误'}</p></article>`;
  }
}

async function startPreview() {
  try {
    if (stream) stream.getTracks().forEach((t) => t.stop());
    const deviceId = stateEls.cameraSelect.value;
    if (!deviceId) return false;
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        deviceId: { exact: deviceId },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
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
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.message || '请求失败');
  return data;
}

async function refreshModels() {
  renderModels((await (await fetch('/api/models')).json()).items || []);
}

async function refreshUser() {
  const data = await (await fetch('/api/user')).json();
  renderUsers(data.users || [], data.state || {});
}

navItems.forEach((btn) => btn.addEventListener('click', () => switchPanel(btn.dataset.panel)));
stateEls.sidebarToggle?.addEventListener('click', () => stateEls.appShell.classList.toggle('sidebar-collapsed'));
stateEls.cameraSelect.addEventListener('change', startPreview);
stateEls.danceType.addEventListener('change', async () => { updateStandardVideoSource(true); await prepareStandardVideo(); });
stateEls.swapVideoBtn?.addEventListener('click', toggleVideoSwap);
stateEls.swapVideoBtnMini?.addEventListener('click', toggleVideoSwap);
stateEls.fullscreenBtn?.addEventListener('click', toggleVideoFullscreen);
stateEls.standardReplayBtn?.addEventListener('click', replayStandardVideo);
stateEls.standardPlayBtn?.addEventListener('click', toggleStandardPlayback);
stateEls.standardAudioBtn?.addEventListener('click', toggleStandardAudio);
stateEls.standardAudioBtnMini?.addEventListener('click', toggleStandardAudio);
stateEls.standardResetBtn?.addEventListener('click', resetPipSize);
document.addEventListener('fullscreenchange', () => { endPipResize(); clearPipStateFlags(); stateEls.pipSizeHint?.classList.add('hidden'); stateEls.pipBoundHint?.classList.add('hidden'); ensurePipWidthForCurrentMode(); syncVideoStageState(); });
standardVideoNodes().forEach((video) => {
  video.addEventListener("loadeddata", () => { hideStandardPlaceholder(); if (video === activeStandardVideo()) { standardPlaying = !video.paused; updateStandardProgress(); } updateStandardPlayButton(); });
  video.addEventListener("timeupdate", () => { if (video === activeStandardVideo()) { updateStandardProgress(); } });
  video.addEventListener("ended", () => { if (video === activeStandardVideo()) { standardPlaying = false; updateStandardPlayButton(); updateStandardProgress(); } });
  video.addEventListener("pause", () => { if (video === activeStandardVideo()) { standardPlaying = false; updateStandardPlayButton(); } });
  video.addEventListener("play", () => { if (video === activeStandardVideo()) { standardPlaying = true; inactiveStandardVideo()?.pause(); updateStandardPlayButton(); } });
  video.addEventListener("error", () => showStandardPlaceholder(`未找到标准视频：${(video?.dataset?.src || "").split("/").pop() || "demo.mp4"}`));
});
stateEls.standardProgressBar?.parentElement?.addEventListener("pointerdown", beginStandardScrub);
stateEls.standardPrimaryProgressShell?.addEventListener("pointerdown", beginStandardScrub);
stateEls.refreshVideoBtn.addEventListener('click', async () => {
  await listVideoDevices();
  if (stateEls.cameraSelect.options.length) await startPreview();
});
stateEls.startBtn.addEventListener('click', async () => {
  if (!(await startPreview())) return;
  toast((await postJson('/api/start', {
    dance_type: stateEls.danceType.value,
    host: stateEls.vmcHost.value,
    port: Number(stateEls.vmcPort.value || 39539),
  })).message || '已启动');
  scoreSeries = [];
  renderChart();
});
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
stateEls.importForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = stateEls.importFile.files?.[0];
  if (!file) return toast('请先选择文件');
  const form = new FormData();
  form.append('file', file);
  form.append('dance_type', stateEls.importDanceType.value);
  stateEls.importResult.innerHTML = `<span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 8h14"></path><path d="M5 12h10"></path><path d="M5 16h8"></path></svg></span>导入结果</span><strong><span class="status-dot warn"></span>上传中...</strong><p class="card-subline">正在提交文件并等待后端评估</p>`;
  const resp = await fetch('/api/import/upload', { method: 'POST', body: form });
  const data = await resp.json();
  stateEls.importResult.innerHTML = `<span class="meta-label"><span class="meta-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 8h14"></path><path d="M5 12h10"></path><path d="M5 16h8"></path></svg></span>导入结果</span><strong><span class="status-dot live"></span>${data.message || '处理完成'}</strong><p class="card-subline">评估结果已写入导入记录与历史记录</p>`;
});
stateEls.loginBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/login', {
    username: stateEls.loginUsername.value.trim(),
    password: stateEls.loginPassword.value,
  })).message || '已登录');
  await refreshUser();
});
stateEls.logoutBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/logout', {})).message || '已退出');
  await refreshUser();
});
stateEls.registerBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/register', {
    username: stateEls.registerUsername.value.trim(),
    password: stateEls.registerPassword.value,
    role: stateEls.registerRole.value,
  })).message || '注册成功');
  await refreshUser();
});
stateEls.resetPasswordBtn.addEventListener('click', async () => {
  toast((await postJson('/api/auth/reset_password', {
    username: stateEls.registerUsername.value.trim(),
    password: stateEls.registerPassword.value,
  })).message || '密码已重置');
});
if (navigator.mediaDevices?.addEventListener) {
  navigator.mediaDevices.addEventListener('devicechange', listVideoDevices);
}

(async function boot() {
  stateEls.permissionValue.textContent = await detectPermission();
  if (navigator.mediaDevices?.getUserMedia) {
    try {
      await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      stateEls.permissionValue.textContent = '已授予';
    } catch {
      stateEls.permissionValue.textContent = '已拒绝';
    }
  } else {
    stateEls.permissionValue.textContent = '浏览器不支持';
  }
  updateStandardVideoSource(true);
  applyStoredPipWidths();
  ensurePipWidthForCurrentMode();
  syncVideoStageState();
  await listVideoDevices();
  if (stateEls.cameraSelect.options.length) await startPreview();
  await prepareStandardVideo();
  renderChart();
  renderHistoryDetail(null);
  await refreshModels();
  await refreshUser();
  connectStream();
})();


document.addEventListener('pointermove', (ev) => { updatePipResize(ev); updateStandardScrub(ev); });
document.addEventListener('pointerup', async () => { endPipResize(); await endStandardScrub(); });
document.addEventListener('pointercancel', async () => { endPipResize(); await endStandardScrub(); });
stateEls.videoStage?.addEventListener('pointerdown', beginPipResize);









