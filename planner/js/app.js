// 1. 요소 선택
const form = document.getElementById("goal-form");
const input = document.getElementById("goal-input");
const category = document.getElementById("goal-category");
const dueInput = document.getElementById("goal-due");
const searchInput = document.getElementById("goal-search");
const listEl = document.getElementById("goal-list");
const emptyEl = document.getElementById("list-empty");
const errorEl = document.getElementById("form-error");
const tabsEl = document.getElementById("filter-tabs");
const sortSelect = document.getElementById("sort-select");
const fillEl = document.getElementById("progress-fill");
const textEl = document.getElementById("progress-text");
const summaryEl = document.getElementById("category-summary");
const tipEl = document.getElementById("tip");
const themeToggle = document.getElementById("theme-toggle");
const heatmapEl = document.getElementById("heatmap");
const streakCountEl = document.getElementById("streak-count");
const levelBadgeEl = document.getElementById("level-badge");
const levelCountEl = document.getElementById("level-count");
const xpFillEl = document.getElementById("xp-fill");
const xpTextEl = document.getElementById("xp-text");

// 2. 상태와 저장
const STORAGE_KEY = "skala-planner";
const THEME_KEY = "skala-planner-theme";
const XP_KEY = "skala-planner-xp";
const XP_PER_GOAL = 10;
const XP_PER_LEVEL = 50;
let goals = load();
let filter = "all";
let sortMode = "default"; // "default" | "due" | "newest"
let totalXp = Number(localStorage.getItem(XP_KEY)) || 0;
let previousLevel = Math.floor(totalXp / XP_PER_LEVEL) + 1;

function load() {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved ? JSON.parse(saved) : [];
}

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(goals));
}

// 사용자 입력을 화면에 안전하게 표시하기 위한 이스케이프 (XSS 방지)
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// F5: 마감일이 지났고 아직 완료되지 않은 목표인지 확인
function isOverdue(goal) {
  if (!goal.due || goal.done) return false;
  return goal.due < dateKey(new Date());
}

// 3. 진행률
function updateProgress() {
  const total = goals.length;
  const done = goals.filter((g) => g.done).length;
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);
  fillEl.style.width = percent + "%";
  textEl.textContent = `전체 ${total}개 중 ${done}개 완료 (${percent}%)`;
}

// 날짜를 "YYYY-MM-DD" 키로 통일 (완료 기록 · 히트맵 · 스트릭이 모두 이 형식을 쓴다)
function dateKey(date) {
  return date.toISOString().slice(0, 10);
}

// 차별화 요소: 완료한 목표를 날짜별로 쌓아 보여주는 학습 활동 히트맵 (GitHub 잔디 방식)
function buildHeatmap() {
  const WEEKS = 12;
  const totalDays = WEEKS * 7;
  const counts = {};
  goals.forEach((g) => {
    if (g.done && g.completedAt) {
      counts[g.completedAt] = (counts[g.completedAt] || 0) + 1;
    }
  });

  heatmapEl.innerHTML = "";
  for (let i = totalDays - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = dateKey(d);
    const count = counts[key] || 0;
    const level = count === 0 ? 0 : count === 1 ? 1 : count === 2 ? 2 : 3;
    const cell = document.createElement("span");
    cell.className = "heatmap-cell";
    cell.dataset.level = level;
    // 브라우저 기본 title 툴팁은 뜨는 데 1초 가까이 걸리므로,
    // CSS ::after로 직접 그리는 즉시 표시 툴팁을 쓴다 (아래 data-tooltip)
    cell.dataset.tooltip = `${key} · ${count}개 완료`;
    heatmapEl.appendChild(cell);
  }
}

// 차별화 요소: 완료 기록이 오늘부터 며칠 연속 이어지는지 계산
function updateStreak() {
  const doneDates = new Set(
    goals.filter((g) => g.done && g.completedAt).map((g) => g.completedAt)
  );
  let streak = 0;
  const cursor = new Date();
  while (doneDates.has(dateKey(cursor))) {
    streak++;
    cursor.setDate(cursor.getDate() - 1);
  }
  streakCountEl.textContent = streak;
}

// 도전 요소(게임화): 완료할 때마다 쌓이는 경험치(XP)로 레벨을 계산해 보여준다.
// XP는 목표를 나중에 지우거나 취소해도 깎이지 않는 누적 기록이다 — 실제로 완료했던 사실은 남아야 하니까.
function updateLevel() {
  const level = Math.floor(totalXp / XP_PER_LEVEL) + 1;
  const progressXp = totalXp % XP_PER_LEVEL;
  const percent = Math.round((progressXp / XP_PER_LEVEL) * 100);

  levelCountEl.textContent = level;
  xpFillEl.style.width = percent + "%";
  xpTextEl.textContent = `${progressXp} / ${XP_PER_LEVEL} XP`;

  if (level > previousLevel) {
    levelBadgeEl.classList.add("is-leveling");
    setTimeout(() => levelBadgeEl.classList.remove("is-leveling"), 700);
  }
  previousLevel = level;
}

// F7: 분류별 남은 개수 집계
function updateSummary() {
  const rest = goals.filter((g) => !g.done).reduce((acc, g) => {
    acc[g.category] = (acc[g.category] || 0) + 1;
    return acc;
  }, {});
  const categories = ["HTML", "CSS", "JS"];
  summaryEl.textContent = categories
    .map((cat) => `${cat} ${rest[cat] || 0}개`)
    .join(" · ");
}

// F3 + F6 + 도전 과제(정렬): 필터·검색어를 적용한 뒤 정렬 기준을 얹는다
function visible() {
  let list = goals;
  if (filter === "active") list = list.filter((g) => !g.done);
  if (filter === "done") list = list.filter((g) => g.done);
  const keyword = searchInput.value.trim();
  if (keyword !== "") list = list.filter((g) => g.title.includes(keyword));

  list = [...list]; // 정렬은 복사본에만 적용 — goals의 저장 순서 자체는 바꾸지 않는다
  if (sortMode === "due") {
    list.sort((a, b) => (a.due || "9999-99-99").localeCompare(b.due || "9999-99-99"));
  } else if (sortMode === "newest") {
    list.sort((a, b) => b.id - a.id);
  }
  return list;
}

// 도전 과제(빈 화면 안내): 상황에 맞는 안내 문구를 고른다
function emptyMessage() {
  if (goals.length === 0) {
    return '아직 등록된 목표가 없습니다. 예: "시맨틱 태그로 뼈대 만들기"처럼 오늘 배운 내용을 첫 목표로 추가해보세요.';
  }
  if (searchInput.value.trim() !== "") {
    return "검색 결과가 없습니다. 다른 검색어로 다시 시도해보세요.";
  }
  if (filter === "active") return "진행 중인 목표가 없습니다.";
  if (filter === "done") return "완료한 목표가 아직 없습니다.";
  return "표시할 목표가 없습니다.";
}

// 7. 렌더링 — 상태를 화면으로 (DOM을 직접 고치지 않고 항상 이 함수로만 그린다)
function render() {
  const items = visible();
  listEl.innerHTML = "";
  items.forEach((goal) => {
    const li = document.createElement("li");
    li.className = goal.done ? "item is-done" : "item";
    if (isOverdue(goal)) li.classList.add("is-overdue");
    li.dataset.id = goal.id;
    li.dataset.category = goal.category;
    li.innerHTML = `
      <input type="checkbox" class="item-check" aria-label="${escapeHtml(goal.title)} 완료" ${goal.done ? "checked" : ""}>
      <span class="item-text">${escapeHtml(goal.title)}</span>
      <span class="item-meta">${escapeHtml(goal.category)}</span>
      ${goal.due ? `<span class="item-due">${escapeHtml(goal.due)}</span>` : ""}
      <button type="button" class="item-del" aria-label="삭제">삭제</button>
    `;
    listEl.appendChild(li);
  });
  emptyEl.hidden = items.length > 0;
  emptyEl.textContent = emptyMessage();
  updateProgress();
  updateSummary();
  buildHeatmap();
  updateStreak();
  updateLevel();
}

// 4. 목표 추가 (F1: 빈 값·공백만 입력 거부 / F5: 마감일 저장)
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = input.value.trim();
  if (title === "") {
    errorEl.hidden = false;
    input.focus();
    return;
  }
  errorEl.hidden = true;
  // 키보드로 과거 날짜를 직접 입력했을 경우를 대비한 이중 방어 (min 속성 우회 가능성)
  const due = dueInput.value && dueInput.value < dateKey(new Date()) ? "" : dueInput.value;
  goals.push({
    id: Date.now(),
    title: title,
    category: category.value,
    due: due,
    done: false,
  });
  input.value = "";
  dueInput.value = "";
  save();
  render();
});

// 5. 완료 토글 · 삭제 · 도전 과제(삭제 애니메이션) (F2: 이벤트 위임 — 리스너는 listEl 하나뿐)
listEl.addEventListener("click", (event) => {
  const li = event.target.closest(".item");
  if (!li) return;
  const id = Number(li.dataset.id);

  if (event.target.matches(".item-check")) {
    const goal = goals.find((g) => g.id === id);
    goal.done = event.target.checked;
    goal.completedAt = goal.done ? dateKey(new Date()) : null;
    if (goal.done) {
      totalXp += XP_PER_GOAL;
      localStorage.setItem(XP_KEY, totalXp);
    }
    save();
    render();
    return;
  }

  if (event.target.matches(".item-del")) {
    const removeNow = () => {
      goals = goals.filter((g) => g.id !== id);
      save();
      render();
    };
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      removeNow();
    } else {
      li.classList.add("item-removing");
      li.addEventListener("transitionend", removeNow, { once: true });
    }
  }
});

// 도전 과제(수정 기능): 목표 제목을 더블클릭해 편집하고 저장 (8장 이벤트)
listEl.addEventListener("dblclick", (event) => {
  const textSpan = event.target.closest(".item-text");
  if (!textSpan) return;
  const li = textSpan.closest(".item");
  const id = Number(li.dataset.id);
  const goal = goals.find((g) => g.id === id);

  const editInput = document.createElement("input");
  editInput.type = "text";
  editInput.className = "item-edit";
  editInput.setAttribute("aria-label", "목표 제목 수정");
  editInput.value = goal.title;
  textSpan.replaceWith(editInput);
  editInput.focus();
  editInput.select();

  function commitEdit() {
    const newTitle = editInput.value.trim();
    if (newTitle !== "") goal.title = newTitle;
    save();
    render();
  }

  editInput.addEventListener("blur", commitEdit);
  editInput.addEventListener("keydown", (keyEvent) => {
    if (keyEvent.key === "Enter") editInput.blur();
    if (keyEvent.key === "Escape") {
      editInput.removeEventListener("blur", commitEdit);
      render();
    }
  });
});

// 6. 필터 탭 (F3)
tabsEl.addEventListener("click", (event) => {
  const tab = event.target.closest(".tab");
  if (!tab) return;
  filter = tab.dataset.filter;
  tabsEl.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("is-active", t === tab);
  });
  render();
});

// 도전 과제(정렬): 마감임박순 · 최신순 (7장 sort)
sortSelect.addEventListener("change", () => {
  sortMode = sortSelect.value;
  render();
});

// F6: 검색어 입력 시 실시간 반영
searchInput.addEventListener("input", () => {
  render();
});

// 도전 과제(다크 모드): CSS 변수만 교체해 테마 전환, localStorage에 기억
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
  themeToggle.textContent = theme === "dark" ? "라이트 모드" : "다크 모드";
}

let theme = localStorage.getItem(THEME_KEY) || "light";
applyTheme(theme);

themeToggle.addEventListener("click", () => {
  theme = theme === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
});

// 8. 오늘의 팁 불러오기 (fetch + async/await + try/catch)
async function loadTip() {
  try {
    const response = await fetch("data/tips.json");
    if (!response.ok) throw new Error("HTTP " + response.status);
    const tips = await response.json();
    const today = new Date().getDate() % tips.length;
    tipEl.textContent = tips[today];
  } catch (error) {
    tipEl.textContent = "팁을 불러오지 못했습니다.";
    console.error(error);
  }
}

// F5: 마감일은 앞으로의 기한이므로 과거 날짜는 선택하지 못하게 막는다
dueInput.min = dateKey(new Date());

// 초기 실행
render();
loadTip();
