// MeetingNote 프론트. 상태는 모듈 변수에 두고 DOM 을 직접 갱신한다.
'use strict';

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const SEARCH_DELAY_MS = 250;
const DELETE_CONFIRM_MS = 4000;

const CARD_CLASS =
  'rounded-2xl border border-white/50 bg-white/60 p-4 shadow-lg backdrop-blur-xl dark:border-white/10 dark:bg-white/5';
const COLUMN_TITLES = { summary: '요약', decisions: '결정사항', todos: '할일' };

// ---- 상태 ----
let currentNote = null;
let deleteTimer = null;
let searchTimer = null;

// ---- DOM 도우미 ----
const byId = (id) => document.getElementById(id);
const role = (name) => document.querySelector(`[data-role="${name}"]`);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setText(name, text) {
  role(name).textContent = text;
}

// ---- API ----
async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = '';
    try {
      const data = await response.json();
      detail = typeof data.detail === 'string' ? data.detail : '';
    } catch (e) {
      detail = '';
    }
    const error = new Error(detail || `요청에 실패했습니다 (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function jsonRequest(method, payload) {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  };
}

// ---- 시간 ----
function formatLocal(iso) {
  return new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function nowForInput() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function splitLines(text) {
  return text.split('\n').map((line) => line.trim()).filter(Boolean);
}

// ---- 테마 ----
function toggleTheme() {
  const dark = document.documentElement.classList.toggle('dark');
  try {
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  } catch (e) {
    // 저장이 막힌 환경에서는 이번 화면에만 적용한다.
  }
}

// ---- 탭 ----
function showTab(name) {
  document.querySelectorAll('[data-view]').forEach((section) => {
    section.classList.toggle('hidden', section.dataset.view !== name);
  });
  document.querySelectorAll('[data-tab]').forEach((button) => {
    const active = button.dataset.tab === name;
    button.classList.toggle('bg-blue-600', active);
    button.classList.toggle('text-white', active);
    button.classList.toggle('shadow', active);
  });
  if (name === 'list') loadNotes();
  if (name === 'todos') loadTodos();
}

// ---- 목록 ----
async function loadNotes() {
  const params = new URLSearchParams();
  if (byId('q').value.trim()) params.set('q', byId('q').value.trim());
  if (byId('from').value) params.set('from', byId('from').value);
  if (byId('to').value) params.set('to', byId('to').value);
  setText('listStatus', '');
  try {
    const notes = await api(`/api/notes?${params}`);
    renderCards(notes);
    if (notes.length === 0) setText('listStatus', '회의록이 없습니다.');
  } catch (error) {
    byId('cards').replaceChildren();
    setText('listStatus', error.message);
  }
}

function renderCards(notes) {
  const cards = notes.map((note) => {
    const card = el('button', `${CARD_CLASS} flex flex-col text-left transition hover:shadow-xl`);
    card.type = 'button';
    const meta = [formatLocal(note.met_at), note.attendees].filter(Boolean).join(' · ');
    const firstLine = splitLines(note.summary)[0] || '(요약 없음)';
    card.append(
      el('h3', 'break-words font-semibold', note.title),
      el('p', 'mt-1 text-xs text-slate-500 dark:text-neutral-400', meta),
      el('p', 'mt-2 line-clamp-2 break-words text-sm', firstLine),
    );
    card.addEventListener('click', () => openModal(note.id));
    return card;
  });
  byId('cards').replaceChildren(...cards);
}

// ---- 넣기 ----
async function uploadAudio() {
  const file = byId('file').files[0];
  if (!file) return setText('upStatus', '파일을 먼저 선택하세요.');
  if (!/\.(mp3|wav)$/i.test(file.name)) return setText('upStatus', 'mp3, wav 파일만 올릴 수 있습니다.');
  if (file.size > MAX_UPLOAD_BYTES) return setText('upStatus', '25MB 이하 파일만 올릴 수 있습니다.');

  const button = byId('btnUp');
  button.disabled = true;
  setText('upStatus', '받아쓰는 중…');
  try {
    const formData = new FormData();
    formData.append('file', file);
    const data = await api('/api/upload', { method: 'POST', body: formData });
    byId('body').value = data.text;
    setText('upStatus', '받아쓰기 완료');
  } catch (error) {
    setText('upStatus', error.message);
  } finally {
    button.disabled = false;
  }
}

async function saveNote() {
  const title = byId('title').value.trim();
  const metAt = byId('metAt').value;
  const body = byId('body').value.trim();
  if (!title || !metAt || !body) return setText('saveStatus', '제목, 일시, 본문을 모두 입력하세요.');

  const button = byId('btnSave');
  button.disabled = true;
  setText('saveStatus', '정리하는 중…');
  try {
    const note = await api('/api/notes', jsonRequest('POST', {
      title,
      // datetime-local 값은 로컬 시각이므로 UTC 로 바꿔 보낸다.
      met_at: new Date(metAt).toISOString(),
      attendees: byId('attendees').value.trim(),
      body,
    }));
    renderResult(note);
    const failed = !note.summary && !note.decisions && !note.todos;
    setText('saveStatus', failed ? '저장했지만 구분에 실패했습니다.' : '저장했습니다.');
  } catch (error) {
    setText('saveStatus', error.message);
  } finally {
    button.disabled = false;
  }
}

function buildColumn(key, text) {
  const column = el('div', 'rounded-xl bg-black/5 p-3 dark:bg-white/5');
  column.append(el('h4', 'mb-2 text-sm font-semibold', COLUMN_TITLES[key]));
  const lines = splitLines(text);
  if (lines.length === 0) {
    column.append(el('p', 'text-sm text-slate-400 dark:text-neutral-500', '없음'));
    return column;
  }
  const list = el('ul', 'space-y-1 text-sm');
  lines.forEach((line) => {
    const shown = key === 'todos' ? line.split('|').map((part) => part.trim()).join(' · ') : line;
    list.append(el('li', 'break-words', `- ${shown}`));
  });
  column.append(list);
  return column;
}

function buildColumns(note, className) {
  const wrapper = el('div', className);
  ['summary', 'decisions', 'todos'].forEach((key) => wrapper.append(buildColumn(key, note[key])));
  return wrapper;
}

function renderResult(note) {
  const result = byId('result');
  result.classList.remove('hidden');
  const children = [];
  if (!note.summary && !note.decisions && !note.todos) {
    children.push(el('p', 'mb-3 rounded-xl bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300',
      '구분 실패: 본문은 저장했지만 요약 · 결정사항 · 할일을 만들지 못했습니다.'));
  }
  children.push(buildColumns(note, 'grid grid-cols-1 gap-3 md:grid-cols-3'));
  result.replaceChildren(...children);
}

// ---- 상세 ----
async function openModal(id) {
  try {
    currentNote = await api(`/api/notes/${id}`);
  } catch (error) {
    return setText('listStatus', error.message);
  }
  setText('detailTitle', currentNote.title);
  setText('detailMeta', [formatLocal(currentNote.met_at), currentNote.attendees].filter(Boolean).join(' · '));
  setText('detailBody', currentNote.body);
  role('detailColumns').replaceChildren(...buildColumns(currentNote, 'contents').children);
  byId('mTitle').value = currentNote.title;
  setText('modalStatus', '');
  resetDeleteButton();
  const modal = byId('modal');
  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function closeModal() {
  const modal = byId('modal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
  currentNote = null;
  resetDeleteButton();
}

function resetDeleteButton() {
  clearTimeout(deleteTimer);
  deleteTimer = null;
  role('deleteBtn').textContent = '삭제';
}

async function renameNote() {
  const title = byId('mTitle').value.trim();
  if (!currentNote || !title) return setText('modalStatus', '제목을 입력하세요.');
  const button = role('renameBtn');
  button.disabled = true;
  try {
    // PUT 은 id 를 뺀 전 필드를 받는다. 제목만 바꾸고 나머지는 그대로 보낸다.
    const { id, ...fields } = currentNote;
    currentNote = await api(`/api/notes/${id}`, jsonRequest('PUT', { ...fields, title }));
    setText('detailTitle', currentNote.title);
    setText('modalStatus', '제목을 수정했습니다.');
    loadNotes();
  } catch (error) {
    setText('modalStatus', error.message);
  } finally {
    button.disabled = false;
  }
}

async function deleteNote() {
  if (!currentNote) return;
  const button = role('deleteBtn');
  // 삭제는 한 번 더 눌러야 지워진다.
  if (deleteTimer === null) {
    button.textContent = '정말 삭제';
    deleteTimer = setTimeout(resetDeleteButton, DELETE_CONFIRM_MS);
    return;
  }
  try {
    await api(`/api/notes/${currentNote.id}`, { method: 'DELETE' });
    closeModal();
    loadNotes();
  } catch (error) {
    setText('modalStatus', error.message);
    resetDeleteButton();
  }
}

// ---- 할일 ----
async function loadTodos() {
  setText('todoStatus', '');
  const tbody = byId('todoBody');
  try {
    const todos = await api('/api/todos');
    if (todos.length === 0) {
      tbody.replaceChildren();
      return setText('todoStatus', '할일이 없습니다.');
    }
    const rows = todos.map((todo) => {
      const row = el('tr', 'border-b border-black/5 last:border-0 dark:border-white/5');
      [todo.what, todo.who, todo.when, todo.note_title].forEach((value) => {
        row.append(el('td', 'break-words px-4 py-3', value));
      });
      return row;
    });
    tbody.replaceChildren(...rows);
  } catch (error) {
    tbody.replaceChildren();
    setText('todoStatus', error.message);
  }
}

// ---- 시작 ----
function scheduleSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadNotes, SEARCH_DELAY_MS);
}

function init() {
  document.querySelectorAll('[data-tab]').forEach((button) => {
    button.addEventListener('click', () => showTab(button.dataset.tab));
  });
  role('theme').addEventListener('click', toggleTheme);
  ['q', 'from', 'to'].forEach((id) => byId(id).addEventListener('input', scheduleSearch));
  byId('btnUp').addEventListener('click', uploadAudio);
  byId('btnSave').addEventListener('click', saveNote);
  role('closeModal').addEventListener('click', closeModal);
  role('renameBtn').addEventListener('click', renameNote);
  role('deleteBtn').addEventListener('click', deleteNote);
  // 바깥 어두운 영역을 누르면 닫힌다.
  byId('modal').addEventListener('click', (event) => {
    if (event.target === byId('modal')) closeModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeModal();
  });
  byId('metAt').value = nowForInput();
  showTab('list');
}

init();
