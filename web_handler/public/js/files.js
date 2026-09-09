// 项目架构页逻辑：目录浏览 / 编辑 / 预览 / 上传 / 重命名 / 删除 / 新建
'use strict';

(function () {
  let cur = ''; // 当前目录（相对项目根的路径，'' = 根）
  const rowsEl = document.getElementById('file-rows');
  const crumbEl = document.getElementById('crumb');

  loadTopbar('files.html');

  // —— 目录加载与渲染 ——
  async function load(path) {
    try {
      const data = await api('/api/fs/list?path=' + encodeURIComponent(path));
      cur = data.path;
      renderCrumb(data.path);
      renderRows(data.entries, data.truncated);
      document.getElementById('btn-up').disabled = data.path === ''; // 根目录无上级
      // 面板自身目录只读：禁用写操作按钮
      const writable = data.writable;
      document.getElementById('btn-mkdir').disabled = !writable;
      document.getElementById('btn-newfile').disabled = !writable;
      document.getElementById('btn-upload').disabled = !writable;
      if (!writable && data.path) {
        toast('当前目录（面板自身）为只读保护目录，仅可浏览', 'info', 2600);
      }
    } catch (err) {
      toast(err.message, 'error');
      load(''); // 出错回到根目录
    }
  }

  function renderCrumb(relPath) {
    const parts = relPath ? relPath.split('/') : [];
    let acc = '';
    let html = '<a href="#" data-path="">项目根</a>';
    for (const p of parts) {
      acc = acc ? acc + '/' + p : p;
      html += '<span class="sep">/</span><a href="#" data-path="' + escapeHtml(acc) + '">' + escapeHtml(p) + '</a>';
    }
    crumbEl.innerHTML = html;
    crumbEl.querySelectorAll('a').forEach((a) => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        load(a.getAttribute('data-path'));
      });
    });
  }

  function iconFor(entry) {
    if (entry.type === 'dir') return '📁';
    if (entry.isDb) return '🗄️';
    if (entry.ext === '.log') return '📜';
    if (entry.ext === '.py') return '🐍';
    if (entry.preview) {
      if (['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'].includes(entry.ext)) return '🖼️';
      if (['.mp3', '.wav', '.ogg', '.flac', '.m4a'].includes(entry.ext)) return '🎵';
      return '🎬';
    }
    if (entry.editable) return '📄';
    return '📦';
  }

  function renderRows(entries, truncated) {
    if (!entries.length) {
      rowsEl.innerHTML = '<div class="empty-hint">（空目录）</div>';
      return;
    }
    const html = entries.map((e) => {
      const full = cur ? cur + '/' + e.name : e.name;
      const enc = encodeURIComponent(full);
      const acts = [];
      if (e.type === 'dir') {
        acts.push(`<button class="btn small" data-open="${escapeHtml(enc)}">打开</button>`);
      } else if (e.isDb) {
        acts.push(`<button class="btn small primary" data-db="${escapeHtml(e.name.slice(0, -3))}">🗄 打开数据库</button>`);
      } else if (e.ext === '.log') {
        // 日志文件：只读实时跟踪查看（不进入编辑器）
        acts.push(`<button class="btn small" data-log="${escapeHtml(enc)}">📜 查看日志</button>`);
      } else if (e.editable) {
        // 写保护目录（面板自身）内文件：只读查看
        acts.push(`<button class="btn small" data-edit="${escapeHtml(enc)}" data-ro="${e.writable ? '0' : '1'}">${e.writable ? '编辑' : '查看'}</button>`);
      } else if (e.preview) {
        acts.push(`<button class="btn small" data-preview="${escapeHtml(enc)}" data-pname="${escapeHtml(e.name)}">预览</button>`);
      }
      acts.push(`<a class="btn small" href="/api/fs/raw?path=${enc}" target="_blank">下载</a>`);
      if (e.writable) {
        acts.push(`<button class="btn small" data-rename="${escapeHtml(enc)}" data-name="${escapeHtml(e.name)}">重命名</button>`);
        acts.push(`<button class="btn small danger" data-del="${escapeHtml(enc)}">删除</button>`);
      } else {
        acts.push(`<span class="fmeta" title="面板自身目录受写保护">🔒只读</span>`);
      }
      return `<div class="frow" data-type="${e.type}">
        <span class="fname">
          <span class="icon">${iconFor(e)}</span>
          ${e.type === 'dir'
            ? `<a class="link" href="#" data-open="${escapeHtml(enc)}">${escapeHtml(e.name)}</a>`
            : `<span class="link" style="color:var(--text)">${escapeHtml(e.name)}</span>`}
        </span>
        <span class="fmeta">${e.type === 'dir' ? '—' : fmtSize(e.size)}</span>
        <span class="fmeta mtime">${fmtTime(e.mtimeMs)}</span>
        <span class="facts">${acts.join('')}</span>
      </div>`;
    }).join('');
    rowsEl.innerHTML = (truncated ? '<div class="trunc-note">⚠ 目录条目过多，仅显示前 10000 条</div>' : '') + html;
    bindRowEvents();
  }

  function bindRowEvents() {
    rowsEl.querySelectorAll('[data-open]').forEach((b) => {
      b.addEventListener('click', (e) => {
        e.preventDefault();
        load(decodeURIComponent(b.getAttribute('data-open')));
      });
    });
    rowsEl.querySelectorAll('[data-db]').forEach((b) => {
      b.addEventListener('click', () => {
        location.href = '/db.html?db=' + encodeURIComponent(b.getAttribute('data-db'));
      });
    });
    rowsEl.querySelectorAll('[data-log]').forEach((b) => {
      b.addEventListener('click', () => openLogViewer(decodeURIComponent(b.getAttribute('data-log'))));
    });
    rowsEl.querySelectorAll('[data-edit]').forEach((b) => {
      const readOnly = b.getAttribute('data-ro') === '1';
      b.addEventListener('click', () => openEditor(decodeURIComponent(b.getAttribute('data-edit')), readOnly));
    });
    rowsEl.querySelectorAll('[data-preview]').forEach((b) => {
      b.addEventListener('click', () => openPreview(
        decodeURIComponent(b.getAttribute('data-preview')),
        b.getAttribute('data-pname')
      ));
    });
    rowsEl.querySelectorAll('[data-rename]').forEach((b) => {
      b.addEventListener('click', () => doRename(
        decodeURIComponent(b.getAttribute('data-rename')),
        b.getAttribute('data-name')
      ));
    });
    rowsEl.querySelectorAll('[data-del]').forEach((b) => {
      b.addEventListener('click', () => doDelete(decodeURIComponent(b.getAttribute('data-del'))));
    });
  }

  // —— 文本编辑器（readOnly=true 时仅查看，用于面板自身目录）——
  async function openEditor(full, readOnly) {
    let data;
    try {
      data = await api('/api/fs/read?path=' + encodeURIComponent(full));
    } catch (err) {
      toast(err.message, 'error');
      return;
    }
    const { overlay, close } = showModal(`
      <div class="editor-box">
        <div class="editor-head">
          <span class="path">${readOnly ? '🔒' : '📝'} ${escapeHtml(full)}</span>
          <span class="dirty" id="ed-dirty" hidden>● 未保存</span>
          <span class="spacer"></span>
          ${readOnly ? '<span class="dirty">面板自身目录只读</span>' : '<button class="btn small primary" id="ed-save">保存 (Ctrl+S)</button>'}
          <button class="btn small" id="ed-close">关闭</button>
        </div>
        <textarea id="ed-text" spellcheck="false" ${readOnly ? 'readonly' : ''}></textarea>
      </div>`);
    const ta = overlay.querySelector('#ed-text');
    const dirtyEl = overlay.querySelector('#ed-dirty');
    ta.value = data.content;

    if (readOnly) {
      overlay.querySelector('#ed-close').addEventListener('click', close);
      ta.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') close();
      });
      ta.focus();
      return;
    }

    const markDirty = (d) => { dirtyEl.hidden = !d; };
    ta.addEventListener('input', () => markDirty(ta.value !== data.content));

    const doSave = async () => {
      try {
        await apiJson('/api/fs/write', { path: full, content: ta.value });
        data.content = ta.value;
        markDirty(false);
        toast('已保存：' + full, 'success');
      } catch (err) {
        toast('保存失败：' + err.message, 'error');
      }
    };
    overlay.querySelector('#ed-save').addEventListener('click', doSave);
    overlay.querySelector('#ed-close').addEventListener('click', async () => {
      if (ta.value !== data.content) {
        if (!(await confirmDlg('关闭编辑器', '文件有未保存的修改，确定放弃并关闭吗？'))) return;
      }
      close();
    });
    ta.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        doSave();
      }
      if (e.key === 'Escape') overlay.querySelector('#ed-close').click();
    });
    ta.focus();
  }

  // —— 日志查看（只读 + 自动实时跟踪 + 关键词过滤）——
  const LOG_POLL_MS = 2000; // 轮询间隔
  const LOG_BUFFER_MAX = 8 * 1024 * 1024; // 显示缓冲上限，超出丢弃最早内容

  async function openLogViewer(full) {
    const { overlay, close } = showModal(`
      <div class="editor-box">
        <div class="editor-head">
          <span class="path">📜 ${escapeHtml(full)}</span>
          <span class="dirty" id="log-status">⏱ 自动刷新中</span>
          <span class="dirty" id="log-time"></span>
          <span class="spacer"></span>
          <input type="text" id="log-filter" class="log-filter" placeholder="🔍 过滤关键词…" autocomplete="off">
          <label class="log-opt"><input type="checkbox" id="log-ci" checked>忽略大小写</label>
          <button class="btn small" id="log-prev" title="上一个匹配">↑</button>
          <button class="btn small" id="log-next" title="下一个匹配">↓</button>
          <span class="dirty" id="log-match" hidden></span>
          <button class="btn small" id="log-toggle">⏸ 暂停刷新</button>
          <button class="btn small" id="log-scroll">🔻 自动滚动：开</button>
          <a class="btn small" href="/api/fs/raw?path=${encodeURIComponent(full)}" target="_blank">下载</a>
          <button class="btn small" id="log-close">关闭</button>
        </div>
        <pre id="log-view" class="log-view" tabindex="0"></pre>
      </div>`);
    const pre = overlay.querySelector('#log-view');
    const statusEl = overlay.querySelector('#log-status');
    const timeEl = overlay.querySelector('#log-time');
    const toggleBtn = overlay.querySelector('#log-toggle');
    const scrollBtn = overlay.querySelector('#log-scroll');
    const filterInput = overlay.querySelector('#log-filter');
    const ciBox = overlay.querySelector('#log-ci');
    const matchEl = overlay.querySelector('#log-match');
    let offset = 0; // 已消费的字节数
    let live = true; // 自动刷新开关
    let errored = false; // 读取失败后停止轮询
    let autoScroll = true;
    let inFlight = false;
    let timer = 0;
    let filterTimer = 0;
    let fullText = ''; // 已消费内容的显示缓冲（过滤时从它重建视图）
    let renderedLen = 0; // 已渲染到 pre 的 fullText 长度（仅无过滤时有效）
    let plainDirty = false; // 需要整块重绘（截断/缓冲裁剪/从过滤切回）
    let filter = ''; // 当前过滤关键词
    let ci = true; // 忽略大小写
    let navIdx = -1; // 匹配跳转游标

    const alive = () => document.body.contains(overlay);
    const setStatus = () => {
      if (errored) { statusEl.textContent = '⚠ 已停止（读取失败）'; return; }
      statusEl.textContent = live ? '⏱ 自动刷新中' : '⏸ 已暂停';
    };
    const setScrollBtn = () => {
      scrollBtn.textContent = '🔻 自动滚动：' + (autoScroll ? '开' : '关');
    };

    // 追加内容并做缓冲裁剪（从行边界丢弃最早内容）
    const applyAppend = (content) => {
      fullText += content;
      if (fullText.length > LOG_BUFFER_MAX) {
        const cut = fullText.indexOf('\n', fullText.length - LOG_BUFFER_MAX);
        const from = cut === -1 ? fullText.length - LOG_BUFFER_MAX : cut + 1;
        fullText = '…（缓冲区已满，较早内容已丢弃）…\n' + fullText.slice(from);
        plainDirty = true;
      }
    };

    // 过滤视图：只显示包含关键词的行并高亮，统计命中数
    const renderFiltered = () => {
      const needle = ci ? filter.toLowerCase() : filter;
      const prevScroll = pre.scrollTop;
      let html = '';
      let matches = 0;
      let idx = 0;
      while (idx <= fullText.length) {
        const nl = fullText.indexOf('\n', idx);
        const end = nl === -1 ? fullText.length : nl;
        const line = fullText.slice(idx, end);
        const hay = ci ? line.toLowerCase() : line;
        if (hay.indexOf(needle) !== -1) {
          html += highlightText(line, filter, ci);
          let p = 0;
          while ((p = hay.indexOf(needle, p)) !== -1) { matches++; p += needle.length; }
        }
        html += '\n';
        if (nl === -1) break;
        idx = nl + 1;
      }
      if (!matches) {
        html = `<span class="empty-hint" style="display:block;padding:24px">没有匹配「${escapeHtml(filter)}」的行</span>`;
      }
      pre.innerHTML = html;
      if (autoScroll) pre.scrollTop = pre.scrollHeight;
      else pre.scrollTop = prevScroll; // 保持用户浏览位置（innerHTML 重建会清零）
      matchEl.textContent = matches + ' 处匹配';
      matchEl.hidden = false;
      navIdx = -1;
      renderedLen = fullText.length;
    };

    const renderContent = () => {
      if (filter) { renderFiltered(); return; }
      if (plainDirty) {
        pre.textContent = fullText;
        plainDirty = false;
      } else if (fullText.length > renderedLen) {
        pre.append(document.createTextNode(fullText.slice(renderedLen)));
      }
      renderedLen = fullText.length;
      if (autoScroll) pre.scrollTop = pre.scrollHeight;
    };

    // 匹配跳转（↑/↓）
    const gotoMark = (delta) => {
      const marks = pre.querySelectorAll('mark.hl');
      if (!marks.length) return;
      navIdx = (navIdx + delta + marks.length) % marks.length;
      marks[navIdx].scrollIntoView({ block: 'center' });
    };

    const poll = async () => {
      if (!alive()) return;
      if (live && !errored && !inFlight) {
        inFlight = true;
        try {
          const data = await api('/api/fs/log?path=' + encodeURIComponent(full) + '&offset=' + offset);
          if (!alive()) return;
          if (data.truncated) {
            // 首次截尾 / 文件被轮转清空 / 增量过大：重置视图
            fullText = '…（已跳过较旧内容，仅显示文件尾部）…\n' + data.content;
            plainDirty = true;
          } else if (data.content) {
            applyAppend(data.content);
          }
          offset = data.offset;
          if (data.truncated || data.content) renderContent(); // 无新内容时不重绘，保持浏览位置
          timeEl.textContent = '更新于 ' + new Date().toLocaleTimeString('zh-CN', { hour12: false }) + ' · ' + fmtSize(data.size);
        } catch (err) {
          if (!alive()) return;
          errored = true;
          toast('日志读取失败，已停止自动刷新：' + err.message, 'error');
          setStatus();
        } finally {
          inFlight = false;
        }
      }
      clearTimeout(timer);
      if (alive()) timer = setTimeout(poll, LOG_POLL_MS);
    };

    // 用户手动滚动：离开底部自动关掉自动滚动，滚回底部自动恢复
    pre.addEventListener('scroll', () => {
      const atBottom = pre.scrollHeight - pre.scrollTop - pre.clientHeight < 20;
      if (atBottom !== autoScroll) {
        autoScroll = atBottom;
        setScrollBtn();
      }
    });

    toggleBtn.addEventListener('click', () => {
      if (errored) { // 失败后点击：立即重试并恢复刷新
        errored = false;
        live = true;
        poll();
      } else {
        live = !live;
      }
      toggleBtn.textContent = live ? '⏸ 暂停刷新' : '▶ 继续刷新';
      setStatus();
    });
    scrollBtn.addEventListener('click', () => {
      autoScroll = !autoScroll;
      setScrollBtn();
      if (autoScroll) pre.scrollTop = pre.scrollHeight;
    });

    // 关键词过滤（防抖）；清空后恢复完整视图
    const applyFilter = () => {
      const v = filterInput.value.trim();
      filter = v;
      if (!filter) {
        plainDirty = true; // 从过滤视图切回完整内容
        matchEl.hidden = true;
        matchEl.textContent = '';
        navIdx = -1;
      }
      renderContent();
    };
    filterInput.addEventListener('input', () => {
      clearTimeout(filterTimer);
      filterTimer = setTimeout(applyFilter, 250);
    });
    filterInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { clearTimeout(filterTimer); applyFilter(); }
    });
    ciBox.addEventListener('change', () => {
      ci = ciBox.checked;
      if (filter) renderFiltered();
    });
    overlay.querySelector('#log-prev').addEventListener('click', () => gotoMark(-1));
    overlay.querySelector('#log-next').addEventListener('click', () => gotoMark(1));
    overlay.querySelector('#log-close').addEventListener('click', () => {
      clearTimeout(timer);
      clearTimeout(filterTimer);
      close();
    });
    pre.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') overlay.querySelector('#log-close').click();
    });
    pre.focus();
    poll();
  }

  // —— 预览（图片/音频/视频/PDF）——
  function openPreview(full, name) {
    const src = '/api/fs/raw?path=' + encodeURIComponent(full);
    const ext = (name.split('.').pop() || '').toLowerCase();
    let media;
    if (['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'].includes('.' + ext)) {
      media = `<img src="${src}" alt="${escapeHtml(name)}">`;
    } else if (['.mp3', '.wav', '.ogg', '.flac', '.m4a'].includes('.' + ext)) {
      media = `<audio src="${src}" controls autoplay></audio>`;
    } else if (['.mp4', '.webm'].includes('.' + ext)) {
      media = `<video src="${src}" controls autoplay></video>`;
    } else {
      media = `<iframe src="${src}"></iframe>`;
    }
    showModal(`
      <div class="preview-box">
        <div class="phead">
          <span class="path">${escapeHtml(full)}</span>
          <a class="btn small" href="${src}" target="_blank">新窗口打开</a>
          <button class="btn small" data-act="close">关闭</button>
        </div>
        ${media}
      </div>`).overlay.querySelector('[data-act="close"]').addEventListener('click', function () {
        this.closest('.overlay').remove();
      });
  }

  // —— 重命名 / 删除 / 新建 ——
  async function doRename(full, oldName) {
    const newName = await promptDlg('重命名', '新的名称：', oldName);
    if (!newName || newName === oldName) return;
    try {
      await apiJson('/api/fs/rename', { path: full, newName });
      toast('已重命名', 'success');
      load(cur);
    } catch (err) {
      toast('重命名失败：' + err.message, 'error');
    }
  }

  async function doDelete(full) {
    if (!(await confirmDlg('删除确认', `确定删除以下内容吗？此操作不可恢复：\n\n${full}`))) return;
    try {
      await apiJson('/api/fs/delete', { path: full });
      toast('已删除', 'success');
      load(cur);
    } catch (err) {
      toast('删除失败：' + err.message, 'error');
    }
  }

  async function doMkdir() {
    const name = await promptDlg('新建文件夹', '文件夹名称：');
    if (!name) return;
    const full = cur ? cur + '/' + name : name;
    try {
      await apiJson('/api/fs/mkdir', { path: full });
      toast('已创建', 'success');
      load(cur);
    } catch (err) {
      toast('创建失败：' + err.message, 'error');
    }
  }

  async function doNewFile() {
    const name = await promptDlg('新建文件', '文件名（如 test.py）：');
    if (!name) return;
    const full = cur ? cur + '/' + name : name;
    try {
      await apiJson('/api/fs/write', { path: full, content: '' });
      toast('已创建：' + name, 'success');
      load(cur);
    } catch (err) {
      toast('创建失败：' + err.message, 'error');
    }
  }

  // —— 上传 ——
  async function uploadFiles(files) {
    for (const f of files) {
      const send = async (overwrite) => {
        const fd = new FormData();
        fd.append('path', cur);
        fd.append('overwrite', overwrite ? 'true' : 'false');
        fd.append('file', f);
        try {
          const r = await api('/api/fs/upload', { method: 'POST', body: fd });
          toast(`已上传：${r.name}（${fmtSize(r.size)}）`, 'success');
          load(cur);
        } catch (err) {
          if (err.status === 409) {
            if (await confirmDlg('覆盖确认', `"${f.name}" 已存在，是否覆盖？`)) await send(true);
          } else {
            toast(`上传 ${f.name} 失败：` + err.message, 'error');
          }
        }
      };
      await send(false);
    }
  }

  // —— 事件绑定 ——
  document.getElementById('btn-up').addEventListener('click', () => {
    if (!cur) return;
    load(cur.split('/').slice(0, -1).join('/'));
  });
  document.getElementById('btn-refresh').addEventListener('click', () => load(cur));
  document.getElementById('btn-mkdir').addEventListener('click', doMkdir);
  document.getElementById('btn-newfile').addEventListener('click', doNewFile);
  document.getElementById('btn-upload').addEventListener('click', () => document.getElementById('file-input').click());
  document.getElementById('file-input').addEventListener('change', (e) => {
    if (e.target.files.length) uploadFiles([...e.target.files]);
    e.target.value = '';
  });

  load('');
})();
