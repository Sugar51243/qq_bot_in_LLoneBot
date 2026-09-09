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
    rows: [],         // 当前页数据（语言切换重绘用）
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
  const dbLayout = document.getElementById('db-layout');

  loadTopbar('db.html');

  // —— 左侧：数据库与表导航 ——
  // 渲染数据库列表（保留展开/激活状态，语言切换时重绘也走这里）
  function renderDbList() {
    const activeName = dbListEl.querySelector('.db-item.active')?.getAttribute('data-db') || null;
    const openName = dbListEl.querySelector('.db-item.open')?.getAttribute('data-db') || null;
    dbListEl.innerHTML = state.dbs.map((d) => `
      <div class="db-item" data-db="${escapeHtml(d.name)}">
        <div class="db-name">
          <span>🗄️</span><span class="t">${escapeHtml(d.name)}</span>
          <span class="size">${fmtSize(d.size)}</span>
        </div>
        <div class="tables"><span style="color:var(--muted);font-size:12px;padding:4px 10px">${escapeHtml(t('common.loading'))}</span></div>
      </div>`).join('') || `<div class="empty-hint">${escapeHtml(t('db.noDbs'))}</div>`;
    dbListEl.querySelectorAll('.db-item').forEach((item) => {
      const name = item.getAttribute('data-db');
      item.querySelector('.db-name').addEventListener('click', () => toggleDb(item, name));
    });
    if (activeName) {
      const item = dbListEl.querySelector(`.db-item[data-db="${cssEscape(activeName)}"]`);
      if (item) item.classList.add('active');
    }
    if (openName) {
      const item = dbListEl.querySelector(`.db-item[data-db="${cssEscape(openName)}"]`);
      if (item) {
        item.classList.add('open');
        renderTablesEl(item.querySelector('.tables'));
      }
    }
  }

  // 渲染某数据库的表格子列表
  function renderTablesEl(tEl) {
    tEl.innerHTML = state.tables.length
      ? state.tables.map((tb) => `<div class="tname" data-table="${cssEscape(tb)}">${escapeHtml(tb)}</div>`).join('')
      : `<span style="color:var(--muted);font-size:12px;padding:4px 10px">${escapeHtml(t('db.emptyDb'))}</span>`;
    tEl.querySelectorAll('.tname').forEach((n) => {
      n.addEventListener('click', () => selectTable(n.getAttribute('data-table'), n));
      n.classList.toggle('active', n.getAttribute('data-table') === state.curTable);
    });
  }

  // 重建右上角表格下拉
  function renderTableSelect() {
    tableSelect.innerHTML = `<option value="">${escapeHtml(t('db.selectTable'))}</option>` +
      state.tables.map((tb) => `<option value="${escapeHtml(tb)}">${escapeHtml(tb)}</option>`).join('');
    tableSelect.disabled = !state.tables.length;
    tableSelect.value = state.curTable || '';
  }

  async function loadDbs(preselect) {
    const { dbs } = await api('/api/db/list');
    state.dbs = dbs;
    renderDbList();
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
    state.rows = [];
    curDbEl.textContent = 'data/db/' + d.file;
    renderTableSelect();
    renderTableArea();
    const tEl = item.querySelector('.tables');
    if (wasOpen) return;
    try {
      const { tables } = await api('/api/db/tables?db=' + encodeURIComponent(name));
      state.tables = tables;
      renderTablesEl(tEl);
      renderTableSelect();
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
    state.rows = [];
    state.sort = [];
    state.q = '';
    dbLayout.classList.remove('side-open'); // 移动端选择表格后收起侧栏
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
      state.rows = r.rows;
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
      sel.innerHTML = `<option value="">${escapeHtml(t('db.sortDefault'))}</option>`;
      sel.disabled = true;
      return;
    }
    const curKey = sortKey(state.sort);
    let html = `<option value="">${escapeHtml(t('db.sortDefault'))}</option>`;
    const cols = state.columns.filter((c) => c.name !== 'rowid');
    if (cols.length) {
      html += `<optgroup label="${escapeHtml(t('db.sortByColumn'))}">`;
      for (const c of cols) {
        for (const [dir, label] of [['asc', t('db.asc')], ['desc', t('db.desc')]]) {
          const key = sortKey([{ col: c.name, dir }]);
          html += `<option value="${escapeHtml(key)}" ${key === curKey ? 'selected' : ''}>${escapeHtml(c.name)} ${escapeHtml(label)}</option>`;
        }
      }
      const rowidDescKey = sortKey([{ col: 'rowid', dir: 'desc' }]);
      html += `<option value="${escapeHtml(rowidDescKey)}" ${rowidDescKey === curKey ? 'selected' : ''}>${escapeHtml(t('db.rowidDesc'))}</option>`;
      html += '</optgroup>';
    }
    if (state.indexes.length) {
      html += `<optgroup label="${escapeHtml(t('db.sortByIndex'))}">`;
      for (const ix of state.indexes) {
        const key = sortKey(ix.cols.map((c) => ({ col: c.name, dir: c.desc ? 'desc' : 'asc' })));
        const label = ix.name + '（' + ix.cols.map((c) => c.name + (c.desc ? '↓' : '↑')).join(', ') + '）' + (ix.unique ? t('db.unique') : '');
        html += `<option value="${escapeHtml(key)}" ${key === curKey ? 'selected' : ''}>${escapeHtml(label)}</option>`;
      }
      html += '</optgroup>';
    }
    sel.innerHTML = html;
    sel.disabled = false;
    sel.value = curKey; // 回显当前排序；无匹配时停留默认选项
    if (sel.value === '' && curKey) {
      sel.value = ''; // 回到默认选项显示（如 rowid 升序，等效默认）
      sel.innerHTML += `<option value="${escapeHtml(curKey)}" selected>${escapeHtml(t('db.customSort'))}</option>`;
    }
  }

  function renderTableArea() {
    if (!state.curDb || !state.curTable) {
      tableWrap.innerHTML = `<div class="empty-hint">${escapeHtml(t('db.emptyHint'))}</div>`;
      return;
    }
    const marker = (col) => {
      const s = state.sort.find((x) => x.col === col);
      return s ? ` <span class="sort-mark">${s.dir === 'desc' ? '▼' : '▲'}</span>` : '';
    };
    // 空数据也显示表头；列头可点击循环排序：升序 → 降序 → 取消
    let html = `<table class="data"><thead><tr><th class="sortable" data-col="rowid" title="${escapeHtml(t('db.rowidSortT'))}">rowid` + marker('rowid') + '</th>';
    for (const c of state.columns) {
      html += `<th class="sortable" data-col="${escapeHtml(c.name)}" title="${escapeHtml(t('db.sortClickT'))}">${escapeHtml(c.name)}${marker(c.name)}${c.pk ? ' <span class="pk">★</span>' : ''}<br><span style="font-weight:400;font-size:10.5px;color:var(--placeholder)">${escapeHtml(c.type || '')}</span></th>`;
    }
    html += `<th>${escapeHtml(t('common.actions'))}</th></tr></thead><tbody id="tbody"></tbody></table>`;
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
    if (!tbody) return;
    if (!rows.length) {
      const hint = state.q
        ? t('db.noMatch', { q: state.q })
        : t('db.noRows');
      tbody.innerHTML = `<tr><td colspan="99"><div class="empty-hint">${escapeHtml(hint)}</div></td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map((row) => {
      let html = `<tr><td class="rowid-cell">${highlightText(row._rowid, state.q)}</td>`;
      for (const c of state.columns) {
        html += `<td>${renderCell(row[c.name], c.name)}</td>`;
      }
      html += `<td><div class="acts">
        <button class="btn small" data-edit="${escapeHtml(row._rowid)}">${escapeHtml(t('common.edit'))}</button>
        <button class="btn small danger" data-del="${escapeHtml(row._rowid)}">${escapeHtml(t('common.delete'))}</button>
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
      return `<span class="blob">&lt;${escapeHtml(t('db.blobSize', { n: v.size }))}&gt;</span>`;
    }
    const text = typeof v === 'object' && v.__truncated !== undefined ? v.value : String(v);
    const isTrunc = typeof v === 'object' && v.__truncated !== undefined;
    const isLong = text.length > 200;
    const display = isLong ? text.slice(0, 200) : text;
    if (isTrunc || isLong) {
      return `<span class="cell" data-full="${escapeHtml(text)}" data-col="${escapeHtml(colName)}" title="${escapeHtml(t('db.clickFull'))}">${highlightText(display, state.q)}…${isTrunc ? `<span class="trunc-badge">${escapeHtml(t('db.truncated'))}</span>` : ''}</span>`;
    }
    return `<span class="cell">${highlightText(text, state.q)}</span>`;
  }

  function showFullValue(col, full) {
    showModal(`
      <div class="fullval-box">
        <h3>${escapeHtml(t('db.fullValue', { t: state.curTable, c: col }))}</h3>
        <pre>${escapeHtml(full)}</pre>
        <div class="mactions" style="margin-top:12px">
          <button class="btn" data-act="close">${escapeHtml(t('common.close'))}</button>
        </div>
      </div>`).overlay.querySelector('[data-act="close"]').addEventListener('click', function () {
        this.closest('.overlay').remove();
      });
  }

  // —— 分页 ——
  function renderPager() {
    const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
    let totalText = t('db.totalRows', { n: state.total });
    if (state.q) totalText = t('db.matchedRows', { q: state.q, n: state.total, t: state.unfiltered != null ? state.unfiltered : state.total });
    document.getElementById('total-info').textContent =
      state.curTable ? t('db.tableInfo', { t: state.curTable, info: totalText }) : '—';
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
    openFormModal(t('db.editRow'), t('db.editRowDesc', { f: state.curDb.file, t: state.curTable, r: rowid }), full.columns, full.row, async (data) => {
      await apiJson('/api/db/update', { db: state.curDb.name, table: state.curTable, rowid, data });
    });
  }

  function openInsertModal() {
    openFormModal(t('db.insertRow'), t('db.insertRowDesc', { f: state.curDb.file, t: state.curTable }), state.columns, {}, async (data) => {
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
              <div class="fname">${escapeHtml(c.name)} <span class="ftype">${escapeHtml(c.type || '')}${c.pk ? t('db.pk') : ''}${c.notnull ? t('db.notNull') : ''}</span></div>
              <div class="finput">
                <input type="text" data-col="${escapeHtml(c.name)}" data-type="${escapeHtml(c.type || '')}"
                  value="${escapeHtml(inputVal)}" ${isBlob ? `disabled placeholder="${escapeHtml(t('db.blobNoEdit'))}"` : ''} autocomplete="off">
                <label class="null-check"><input type="checkbox" data-null="${escapeHtml(c.name)}" ${nullChecked ? 'checked' : ''} ${isBlob ? 'disabled' : ''}> NULL</label>
              </div>
              ${c.pk && (c.type || '').toUpperCase().includes('INT') ? `<div class="hint">${escapeHtml(t('db.pkHint'))}</div>` : ''}
            </div>`;
          }).join('')}
        </div>
        <div class="mactions">
          <button class="btn" data-act="cancel">${escapeHtml(t('common.cancel'))}</button>
          <button class="btn primary" data-act="save">${escapeHtml(t('common.save'))}</button>
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
      btn.textContent = t('db.saving');
      try {
        await submitFn(data);
        toast(t('db.saved'), 'success');
        close();
        loadRows();
      } catch (err) {
        // 503（数据库忙）/400（约束）等：保留弹窗与输入
        toast(t('db.saveFail', { e: err.message }), 'error', 4200);
        btn.disabled = false;
        btn.textContent = t('common.save');
      }
    });
  }

  async function doDelete(rowid) {
    if (!(await confirmDlg(t('db.delRowTitle'),
      t('db.delRowConfirm', { f: state.curDb.file, t: state.curTable, r: rowid })))) return;
    try {
      await apiJson('/api/db/delete', { db: state.curDb.name, table: state.curTable, rowid });
      toast(t('db.rowDeleted'), 'success');
      // 若当前页删空则回退一页
      if (state.page > 1 && (state.page - 1) * state.pageSize >= state.total - 1) state.page -= 1;
      loadRows();
    } catch (err) {
      toast(t('db.delFail', { e: err.message }), 'error');
    }
  }

  // —— 事件绑定 ——
  document.getElementById('btn-dbs').addEventListener('click', () => dbLayout.classList.toggle('side-open'));
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

  // 语言切换重绘（库列表/表格下拉/排序选项/表头/数据行/分页）
  window.__i18nRerender.push(() => {
    renderDbList();
    renderTableSelect();
    renderSortSelect();
    renderTableArea();
    if (state.rows.length) renderRows(state.rows);
    renderPager();
  });

  // —— 初始化 ——
  const preselect = new URLSearchParams(location.search).get('db') || '';
  loadDbs(preselect).catch((err) => toast(err.message, 'error'));
})();
