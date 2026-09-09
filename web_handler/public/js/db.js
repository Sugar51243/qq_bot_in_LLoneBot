// 数据库管理页逻辑：库/表切换、分页查看、增删改行
'use strict';

(function () {
  const state = {
    dbs: [],
    curDb: null,      // {name, file, size...}
    tables: [],
    curTable: null,
    columns: [],      // [{name, type, notnull, pk}]
    indexes: [],      // [{name, unique, origin, cols:[{name, desc}]}]，来自 /api/db/schema
    sort: [],         // [{col, dir:'asc'|'desc'}]，服务端 ORDER BY
    q: '',            // 关键词过滤（全列 LIKE 匹配）
    unfiltered: null, // 过滤前总行数（无过滤时为 null）
    total: 0,
    page: 1,
    pageSize: 100,
  };

  const dbListEl = document.getElementById('db-list');
  const tableWrap = document.getElementById('table-wrap');
  const curDbEl = document.getElementById('cur-db');
  const tableSelect = document.getElementById('table-select');

  loadTopbar('db.html');

  // —— 左侧：数据库与表导航 ——
  async function loadDbs(preselect) {
    const { dbs } = await api('/api/db/list');
    state.dbs = dbs;
    dbListEl.innerHTML = dbs.map((d) => `
      <div class="db-item" data-db="${escapeHtml(d.name)}">
        <div class="db-name">
          <span>🗄️</span><span class="t">${escapeHtml(d.name)}</span>
          <span class="size">${fmtSize(d.size)}</span>
        </div>
        <div class="tables"><span style="color:var(--muted);font-size:12px;padding:4px 10px">加载中…</span></div>
      </div>`).join('') || '<div class="empty-hint">data/db 下没有数据库</div>';

    dbListEl.querySelectorAll('.db-item').forEach((item) => {
      const name = item.getAttribute('data-db');
      item.querySelector('.db-name').addEventListener('click', () => toggleDb(item, name));
    });

    if (preselect) {
      const item = dbListEl.querySelector(`.db-item[data-db="${cssEscape(preselect)}"]`);
      if (item) toggleDb(item, preselect);
    }
  }

  function cssEscape(s) {
    return String(s).replace(/"/g, '\\"');
  }

  async function toggleDb(item, name) {
    const d = state.dbs.find((x) => x.name === name);
    if (!d) return;
    const wasOpen = item.classList.contains('open');
    dbListEl.querySelectorAll('.db-item').forEach((x) => x.classList.remove('open', 'active'));
    if (!wasOpen) item.classList.add('open', 'active');
    // 切换当前数据库
    state.curDb = d;
    state.tables = [];
    state.curTable = null;
    curDbEl.textContent = 'data/db/' + d.file;
    tableSelect.innerHTML = '<option value="">— 请选择表格 —</option>';
    renderTableArea();
    const tEl = item.querySelector('.tables');
    if (wasOpen) return;
    try {
      const { tables } = await api('/api/db/tables?db=' + encodeURIComponent(name));
      state.tables = tables;
      tEl.innerHTML = tables.length
        ? tables.map((t) => `<div class="tname" data-table="${cssEscape(t)}">${escapeHtml(t)}</div>`).join('')
        : '<span style="color:var(--muted);font-size:12px;padding:4px 10px">（空库，无表格）</span>';
      tableSelect.innerHTML = '<option value="">— 请选择表格 —</option>' +
        tables.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
      tableSelect.disabled = !tables.length;
      tEl.querySelectorAll('.tname').forEach((n) => {
        n.addEventListener('click', () => selectTable(n.getAttribute('data-table'), n));
      });
      if (tables.length) selectTable(tables[0], tEl.querySelector('.tname'));
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  function selectTable(name, el) {
    state.curTable = name;
    state.page = 1;
    state.columns = [];
    state.indexes = [];
    state.sort = [];
    state.q = '';
    document.getElementById('search-input').value = '';
    tableSelect.value = name;
    document.querySelectorAll('.tname').forEach((n) => n.classList.toggle('active', n.getAttribute('data-table') === name));
    document.getElementById('btn-insert').disabled = false;
    renderSortSelect();
    loadRows();
    loadIndexes();
  }

  // 拉取表索引（"按索引排序"预设）
  async function loadIndexes() {
    if (!state.curDb || !state.curTable) return;
    try {
      const r = await api(`/api/db/schema?db=${encodeURIComponent(state.curDb.name)}&table=${encodeURIComponent(state.curTable)}`);
      state.indexes = r.indexes || [];
    } catch { /* 忽略，仅影响排序预设 */ }
    renderSortSelect();
  }

  // —— 表格数据 ——
  async function loadRows() {
    if (!state.curDb || !state.curTable) return;
    const pageSize = state.pageSize;
    const page = state.page;
    try {
      let url = `/api/db/rows?db=${encodeURIComponent(state.curDb.name)}&table=${encodeURIComponent(state.curTable)}&page=${page}&pageSize=${pageSize}`;
      if (state.sort.length) url += '&sort=' + encodeURIComponent(JSON.stringify(state.sort));
      if (state.q) url += '&q=' + encodeURIComponent(state.q);
      const r = await api(url);
      state.columns = r.columns;
      state.sort = r.sort || []; // 以服务端校验后的排序为准
      state.q = r.q || ''; // 以服务端裁剪后的关键词为准（用于高亮）
      state.unfiltered = r.unfilteredTotal != null ? r.unfilteredTotal : null;
      state.total = r.total;
      state.page = r.page;
      state.pageSize = r.pageSize;
      renderTableArea();
      renderRows(r.rows);
      renderPager();
      renderSortSelect();
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  // —— 排序 ——
  // 排序键序列化（与下拉选项 value 一致，用于回显当前排序）
  const sortKey = (arr) => JSON.stringify(arr.map((s) => ({ col: s.col, dir: s.dir === 'desc' ? 'desc' : 'asc' })));

  // 重建排序下拉：默认 + 按列（升/降序）+ 按索引预设
  function renderSortSelect() {
    const sel = document.getElementById('sort-select');
    if (!state.curDb || !state.curTable) {
      sel.innerHTML = '<option value="">默认（rowid 升序）</option>';
      sel.disabled = true;
      return;
    }
    const curKey = sortKey(state.sort);
    let html = '<option value="">默认（rowid 升序）</option>';
    const cols = state.columns.filter((c) => c.name !== 'rowid');
    if (cols.length) {
      html += '<optgroup label="按列排序">';
      for (const c of cols) {
        for (const [dir, arrow] of [['asc', '↑ 升序'], ['desc', '↓ 降序']]) {
          const key = sortKey([{ col: c.name, dir }]);
          html += `<option value="${escapeHtml(key)}" ${key === curKey ? 'selected' : ''}>${escapeHtml(c.name)} ${arrow}</option>`;
        }
      }
      const rowidDescKey = sortKey([{ col: 'rowid', dir: 'desc' }]);
      html += `<option value="${escapeHtml(rowidDescKey)}" ${rowidDescKey === curKey ? 'selected' : ''}>rowid ↓ 降序</option>`;
      html += '</optgroup>';
    }
    if (state.indexes.length) {
      html += '<optgroup label="按索引排序">';
      for (const ix of state.indexes) {
        const key = sortKey(ix.cols.map((c) => ({ col: c.name, dir: c.desc ? 'desc' : 'asc' })));
        const label = ix.name + '（' + ix.cols.map((c) => c.name + (c.desc ? '↓' : '↑')).join(', ') + '）' + (ix.unique ? ' · 唯一' : '');
        html += `<option value="${escapeHtml(key)}" ${key === curKey ? 'selected' : ''}>${escapeHtml(label)}</option>`;
      }
      html += '</optgroup>';
    }
    sel.innerHTML = html;
    sel.disabled = false;
    sel.value = curKey; // 回显当前排序；无匹配时停留默认选项
    if (sel.value === '' && curKey) {
      sel.value = ''; // 回到默认选项显示（如 rowid 升序，等效默认）
      sel.innerHTML += `<option value="${escapeHtml(curKey)}" selected>自定义排序</option>`;
    }
  }

  function renderTableArea() {
    if (!state.curDb || !state.curTable) {
      tableWrap.innerHTML = '<div class="empty-hint">← 请在左侧选择一个数据库，再选择要查看的表格</div>';
      return;
    }
    const marker = (col) => {
      const s = state.sort.find((x) => x.col === col);
      return s ? ` <span class="sort-mark">${s.dir === 'desc' ? '▼' : '▲'}</span>` : '';
    };
    // 空数据也显示表头；列头可点击循环排序：升序 → 降序 → 取消
    let html = '<table class="data"><thead><tr><th class="sortable" data-col="rowid" title="点击按 rowid 排序">rowid' + marker('rowid') + '</th>';
    for (const c of state.columns) {
      html += `<th class="sortable" data-col="${escapeHtml(c.name)}" title="点击排序：升序 → 降序 → 取消">${escapeHtml(c.name)}${marker(c.name)}${c.pk ? ' <span class="pk">★</span>' : ''}<br><span style="font-weight:400;font-size:10.5px;color:#5c6d8f">${escapeHtml(c.type || '')}</span></th>`;
    }
    html += '<th>操作</th></tr></thead><tbody id="tbody"></tbody></table>';
    tableWrap.innerHTML = html;
    tableWrap.querySelectorAll('th.sortable').forEach((th) => {
      th.addEventListener('click', () => {
        const col = th.getAttribute('data-col');
        const cur = state.sort.find((x) => x.col === col);
        let next;
        if (!cur) next = [{ col, dir: col === 'rowid' ? 'desc' : 'asc' }]; // rowid 默认已升序，直接降序
        else if (cur.dir === 'asc') next = [{ col, dir: 'desc' }];
        else next = [];
        state.sort = next;
        state.page = 1; // 排序变化后页码语义变化，回到第一页
        loadRows();
      });
    });
  }

  function renderRows(rows) {
    const tbody = document.getElementById('tbody');
    if (!rows.length) {
      const hint = state.q
        ? `（没有匹配「${escapeHtml(state.q)}」的行）`
        : '（该表没有数据，可点击右上角"新增行"）';
      tbody.innerHTML = `<tr><td colspan="99"><div class="empty-hint">${hint}</div></td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map((row) => {
      let html = `<tr><td class="rowid-cell">${highlightText(row._rowid, state.q)}</td>`;
      for (const c of state.columns) {
        html += `<td>${renderCell(row[c.name], c.name)}</td>`;
      }
      html += `<td><div class="acts">
        <button class="btn small" data-edit="${escapeHtml(row._rowid)}">编辑</button>
        <button class="btn small danger" data-del="${escapeHtml(row._rowid)}">删除</button>
      </div></td></tr>`;
      return html;
    }).join('');
    tbody.querySelectorAll('[data-edit]').forEach((b) => {
      b.addEventListener('click', () => openEditForm(Number(b.getAttribute('data-edit'))));
    });
    tbody.querySelectorAll('[data-del]').forEach((b) => {
      b.addEventListener('click', () => doDelete(Number(b.getAttribute('data-del'))));
    });
    tbody.querySelectorAll('td .cell[data-full]').forEach((c) => {
      c.addEventListener('click', () => showFullValue(c.getAttribute('data-col'), c.getAttribute('data-full')));
    });
  }

  function renderCell(v, colName) {
    if (v === null || v === undefined) return '<span class="null">NULL</span>';
    if (typeof v === 'object' && v.__blob !== undefined) {
      return `<span class="blob">&lt;BLOB ${v.size}字节&gt;</span>`;
    }
    const text = typeof v === 'object' && v.__truncated !== undefined ? v.value : String(v);
    const isTrunc = typeof v === 'object' && v.__truncated !== undefined;
    const isLong = text.length > 200;
    const display = isLong ? text.slice(0, 200) : text;
    if (isTrunc || isLong) {
      return `<span class="cell" data-full="${escapeHtml(text)}" data-col="${escapeHtml(colName)}" title="点击查看完整值">${highlightText(display, state.q)}…${isTrunc ? '<span class="trunc-badge">已截断</span>' : ''}</span>`;
    }
    return `<span class="cell">${highlightText(text, state.q)}</span>`;
  }

  function showFullValue(col, full) {
    showModal(`
      <div class="fullval-box">
        <h3>完整值 · ${escapeHtml(state.curTable)}.${escapeHtml(col)}</h3>
        <pre>${escapeHtml(full)}</pre>
        <div class="mactions" style="margin-top:12px">
          <button class="btn" data-act="close">关闭</button>
        </div>
      </div>`).overlay.querySelector('[data-act="close"]').addEventListener('click', function () {
        this.closest('.overlay').remove();
      });
  }

  // —— 分页 ——
  function renderPager() {
    const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
    let totalText = `共 ${state.total} 行`;
    if (state.q) totalText = `匹配「${state.q}」${state.total} 行 / 共 ${state.unfiltered != null ? state.unfiltered : state.total} 行`;
    document.getElementById('total-info').textContent =
      state.curTable ? `表 ${state.curTable} · ${totalText}` : '—';
    document.getElementById('page-input').value = state.page;
    document.getElementById('page-total').textContent = pages;
    document.getElementById('btn-prev').disabled = state.page <= 1;
    document.getElementById('btn-next').disabled = state.page >= pages;
  }

  // —— 行编辑 / 新增 ——
  function valueToInput(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'object' && v.__blob !== undefined) return null; // BLOB 只读
    if (typeof v === 'object' && v.__truncated !== undefined) return v.value;
    return String(v);
  }

  function coerceValue(text, type) {
    const t = text.trim();
    if (t === '') return '';
    const ty = (type || '').toUpperCase();
    if (ty.includes('INT')) {
      const n = parseInt(t, 10);
      return Number.isFinite(n) ? n : t;
    }
    if (ty.includes('REAL') || ty.includes('FLOA') || ty.includes('DOUB') || ty.includes('NUM')) {
      const n = parseFloat(t);
      return Number.isFinite(n) ? n : t;
    }
    return text;
  }

  async function openEditForm(rowid) {
    let full;
    try {
      full = await api(`/api/db/row?db=${encodeURIComponent(state.curDb.name)}&table=${encodeURIComponent(state.curTable)}&rowid=${rowid}`);
    } catch (err) {
      toast(err.message, 'error');
      return;
    }
    openFormModal('编辑行', `数据库 data/db/${state.curDb.file} ｜ 表 ${state.curTable} ｜ rowid = ${rowid}`, full.columns, full.row, async (data) => {
      await apiJson('/api/db/update', { db: state.curDb.name, table: state.curTable, rowid, data });
    });
  }

  function openInsertModal() {
    openFormModal('新增行', `数据库 data/db/${state.curDb.file} ｜ 表 ${state.curTable}`, state.columns, {}, async (data) => {
      const clean = {};
      for (const [k, v] of Object.entries(data)) {
        if (v === null || v === '') continue; // 空值走默认（如 INTEGER 主键自动分配）
        clean[k] = v;
      }
      await apiJson('/api/db/insert', { db: state.curDb.name, table: state.curTable, data: clean });
    });
  }

  function openFormModal(title, desc, columns, row, submitFn) {
    const isEdit = Object.keys(row).length > 0;
    const { overlay, close } = showModal(`
      <div class="modal-box wide">
        <h3>${escapeHtml(title)}</h3>
        <div class="mdesc">${escapeHtml(desc)}</div>
        <div class="mbody form-grid" id="form-grid">
          ${columns.map((c) => {
            const raw = isEdit ? row[c.name] : null;
            const isBlob = raw !== null && typeof raw === 'object' && raw.__blob !== undefined;
            const inputVal = isBlob ? '' : valueToInput(isEdit ? row[c.name] : '');
            const nullChecked = isEdit && !isBlob && (row[c.name] === null || row[c.name] === undefined);
            return `<div class="field-row">
              <div class="fname">${escapeHtml(c.name)} <span class="ftype">${escapeHtml(c.type || '')}${c.pk ? ' · 主键' : ''}${c.notnull ? ' · 非空' : ''}</span></div>
              <div class="finput">
                <input type="text" data-col="${escapeHtml(c.name)}" data-type="${escapeHtml(c.type || '')}"
                  value="${escapeHtml(inputVal)}" ${isBlob ? 'disabled placeholder="BLOB 不支持编辑"' : ''} autocomplete="off">
                <label class="null-check"><input type="checkbox" data-null="${escapeHtml(c.name)}" ${nullChecked ? 'checked' : ''} ${isBlob ? 'disabled' : ''}> NULL</label>
              </div>
              ${c.pk && (c.type || '').toUpperCase().includes('INT') ? '<div class="hint">留空或勾选 NULL：由 SQLite 自动分配主键值</div>' : ''}
            </div>`;
          }).join('')}
        </div>
        <div class="mactions">
          <button class="btn" data-act="cancel">取消</button>
          <button class="btn primary" data-act="save">保存</button>
        </div>
      </div>`);
    const grid = overlay.querySelector('#form-grid');
    overlay.querySelector('[data-act="cancel"]').addEventListener('click', close);
    overlay.querySelector('[data-act="save"]').addEventListener('click', async () => {
      const data = {};
      for (const c of columns) {
        const input = grid.querySelector(`input[data-col="${cssEscape(c.name)}"]`);
        if (!input || input.disabled) continue; // BLOB 列不提交
        const nullBox = grid.querySelector(`input[data-null="${cssEscape(c.name)}"]`);
        if (nullBox && nullBox.checked) {
          data[c.name] = null;
          continue;
        }
        data[c.name] = coerceValue(input.value, c.type);
      }
      const btn = overlay.querySelector('[data-act="save"]');
      btn.disabled = true;
      btn.textContent = '保存中…';
      try {
        await submitFn(data);
        toast('保存成功', 'success');
        close();
        loadRows();
      } catch (err) {
        // 503（数据库忙）/400（约束）等：保留弹窗与输入
        toast('保存失败：' + err.message, 'error', 4200);
        btn.disabled = false;
        btn.textContent = '保存';
      }
    });
  }

  async function doDelete(rowid) {
    if (!(await confirmDlg('删除行确认',
      `确定删除 data/db/${state.curDb.file} · 表 ${state.curTable} 中 rowid = ${rowid} 的这一行吗？此操作不可恢复。`))) return;
    try {
      await apiJson('/api/db/delete', { db: state.curDb.name, table: state.curTable, rowid });
      toast('已删除该行', 'success');
      // 若当前页删空则回退一页
      if (state.page > 1 && (state.page - 1) * state.pageSize >= state.total - 1) state.page -= 1;
      loadRows();
    } catch (err) {
      toast('删除失败：' + err.message, 'error');
    }
  }

  // —— 事件绑定 ——
  document.getElementById('table-select').addEventListener('change', (e) => {
    if (e.target.value) selectTable(e.target.value, null);
  });
  document.getElementById('btn-refresh').addEventListener('click', () => loadRows());
  document.getElementById('sort-select').addEventListener('change', (e) => {
    try { state.sort = e.target.value ? JSON.parse(e.target.value) : []; }
    catch { state.sort = []; }
    state.page = 1; // 排序变化后回到第一页
    loadRows();
  });

  // 关键词快速搜索（防抖 400ms；回车立即查询）
  const searchInput = document.getElementById('search-input');
  let searchTimer = 0;
  const doSearch = () => {
    state.q = searchInput.value.trim();
    state.page = 1; // 过滤变化后回到第一页
    loadRows();
  };
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(doSearch, 400);
  });
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { clearTimeout(searchTimer); doSearch(); }
  });
  document.getElementById('btn-insert').addEventListener('click', openInsertModal);
  document.getElementById('btn-prev').addEventListener('click', () => { state.page -= 1; loadRows(); });
  document.getElementById('btn-next').addEventListener('click', () => { state.page += 1; loadRows(); });
  document.getElementById('page-size').addEventListener('change', (e) => {
    state.pageSize = Number(e.target.value);
    state.page = 1;
    loadRows();
  });
  document.getElementById('page-input').addEventListener('change', (e) => {
    const n = Number(e.target.value);
    const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
    state.page = Math.min(pages, Math.max(1, Math.floor(n) || 1));
    loadRows();
  });

  // —— 初始化 ——
  const preselect = new URLSearchParams(location.search).get('db') || '';
  loadDbs(preselect).catch((err) => toast(err.message, 'error'));
})();
