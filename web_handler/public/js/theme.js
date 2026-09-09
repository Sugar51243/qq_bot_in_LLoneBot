// 小生物v2 面板主题系统：浅蓝（默认）/ 青绿 / 白色 / 黑色 + 自定义背景（颜色或图片）
// 主题通过 <html data-theme="..."> 切换 CSS 变量调色板；自定义背景用 CSSOM setProperty 覆盖 --bg / --bg-image
// 选择器：页面放置 <span class="theme-slot"></span> 容器自动生成 🎨 下拉面板
'use strict';

const THEMES = ['teal', 'blue', 'light', 'dark']; // 显示顺序
const THEME_DEFAULT = 'blue';
const CUSTOM_BG_KEY = 'xsw_custom_bg';
const THEME_KEY = 'xsw_theme';

function readCustomBg() {
  try { return JSON.parse(localStorage.getItem(CUSTOM_BG_KEY) || 'null') || null; }
  catch { return null; }
}

// 应用自定义背景（覆盖当前主题的页面背景；图片优先于颜色）
function applyCustomBg() {
  const root = document.documentElement;
  const cb = readCustomBg();
  if (cb && (cb.color || cb.image)) {
    root.setAttribute('data-custom-bg', '1');
    if (cb.color) root.style.setProperty('--bg', cb.color);
    else root.style.removeProperty('--bg');
    if (cb.image) root.style.setProperty('--bg-image', 'url("' + cb.image + '")');
    else root.style.removeProperty('--bg-image');
  } else {
    root.removeAttribute('data-custom-bg');
    root.style.removeProperty('--bg');
    root.style.removeProperty('--bg-image');
  }
}

function applyTheme(theme) {
  if (!THEMES.includes(theme)) theme = THEME_DEFAULT;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  applyCustomBg();
  updateThemePickerUI();
}

function clearCustomBg() {
  localStorage.removeItem(CUSTOM_BG_KEY);
  applyCustomBg();
  updateThemePickerUI();
}

function updateThemePickerUI() {
  const current = document.documentElement.getAttribute('data-theme') || THEME_DEFAULT;
  const hasCustom = document.documentElement.hasAttribute('data-custom-bg');
  document.querySelectorAll('.theme-pop').forEach((pop) => {
    pop.querySelectorAll('.theme-opt[data-theme]').forEach((b) => {
      const t = b.getAttribute('data-theme');
      if (t === 'custom') b.classList.toggle('active', hasCustom);
      else b.classList.toggle('active', t === current);
    });
  });
}

// 在每个 .theme-slot 容器内生成主题选择器
function buildThemePickers() {
  document.querySelectorAll('.theme-slot').forEach((slot) => {
    const pop = document.createElement('div');
    pop.className = 'theme-pop';
    pop.innerHTML = `
      <button class="btn small tb-icon" id="btn-theme" data-i18n-title="theme.title">🎨</button>
      <div class="pop-menu" hidden>
        ${THEMES.map((th) => `
          <button class="theme-opt" data-theme="${th}">
            <i class="swatch sw-${th}"></i><span data-i18n="theme.${th}"></span>
          </button>`).join('')}
        <button class="theme-opt" data-theme="custom">
          <i class="swatch sw-custom"></i><span data-i18n="theme.custom"></span>
        </button>
        <div class="custom-pane" hidden>
          <label><span data-i18n="theme.bgColor"></span><input type="color" id="bg-color" value="#0e1420"></label>
          <label><span data-i18n="theme.bgImage"></span><input type="text" id="bg-image" data-i18n-placeholder="theme.bgImagePh" autocomplete="off"></label>
          <div class="custom-acts">
            <button class="btn small primary" id="bg-apply" data-i18n="theme.apply"></button>
            <button class="btn small" id="bg-reset" data-i18n="theme.reset"></button>
          </div>
          <p class="custom-note" data-i18n="theme.customNote"></p>
        </div>
      </div>`;
    slot.appendChild(pop);

    const btn = pop.querySelector('#btn-theme');
    const menu = pop.querySelector('.pop-menu');
    const pane = pop.querySelector('.custom-pane');
    const colorIn = pop.querySelector('#bg-color');
    const imageIn = pop.querySelector('#bg-image');

    const closeMenu = () => { menu.hidden = true; pane.hidden = true; };

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const willOpen = menu.hidden;
      document.querySelectorAll('.pop-menu').forEach((m) => { m.hidden = true; });
      document.querySelectorAll('.custom-pane').forEach((p) => { p.hidden = true; });
      if (willOpen) {
        menu.hidden = false;
        // 回显已保存的自定义背景
        const cb = readCustomBg();
        colorIn.value = (cb && cb.color) || '#0e1420';
        imageIn.value = (cb && cb.image) || '';
      }
    });
    pop.querySelectorAll('.theme-opt[data-theme]').forEach((b) => {
      b.addEventListener('click', (e) => {
        e.stopPropagation();
        const th = b.getAttribute('data-theme');
        if (th === 'custom') {
          pane.hidden = !pane.hidden;
          return;
        }
        closeMenu();
        applyTheme(th);
      });
    });
    pop.querySelector('#bg-apply').addEventListener('click', () => {
      const image = imageIn.value.trim();
      if (image && !/^\/[\s\S]*$/.test(image) && !image.startsWith('data:image/')) {
        toast(t('theme.imageInvalid'), 'error', 4200);
        return;
      }
      const cb = {};
      if (image) cb.image = image;
      else cb.color = colorIn.value;
      localStorage.setItem(CUSTOM_BG_KEY, JSON.stringify(cb));
      applyCustomBg();
      updateThemePickerUI();
      closeMenu();
      toast(t('theme.custom'), 'success');
    });
    pop.querySelector('#bg-reset').addEventListener('click', () => {
      clearCustomBg();
      closeMenu();
      toast(t('theme.custom'), 'info');
    });
    document.addEventListener('mousedown', (e) => {
      if (!pop.contains(e.target)) closeMenu();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeMenu();
    });
  });
}

// 初始化：head 同步应用已保存主题（body 渲染前生效，避免闪屏）
applyTheme(localStorage.getItem(THEME_KEY) || THEME_DEFAULT);
document.addEventListener('DOMContentLoaded', () => {
  buildThemePickers();
  updateThemePickerUI(); // 标记当前主题/自定义背景
  applyI18n(); // 翻译选择器内新生成的元素
});
