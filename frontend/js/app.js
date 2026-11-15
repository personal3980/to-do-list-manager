window.taskwellSession.done(function (user) { $(function () {
  'use strict';
  const STORAGE_KEY = `taskwell.tasks.user.${user.id}.v1`;
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const escape = value => $('<span>').text(value).html().replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const dateLabel = value => !value ? 'No due date' : new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  let tasks = [], view = 'all', status = 'all', editingId = null;
  const modal = new bootstrap.Modal(document.getElementById('task-modal'));
  const api = window.TASKWELL_API.replace(/\/auth$/, '/tasks');
  let busy = false, loaded = false;
  const fromApi = task => ({ ...task, due: task.due || '', createdAt: Date.parse(task.created_at) });
  function showError(message) { $('#storage-error').text(message).prop('hidden', false); }
  function request(method, path = '', data) {
    return $.ajax({ url: api + path, method, contentType: 'application/json',
      data: data === undefined ? undefined : JSON.stringify(data), xhrFields: { withCredentials: true } });
  }
  function failure(xhr) {
    if (xhr.status === 401) { location.replace('login.html?expired=1'); return; }
    const detail = xhr.responseJSON;
    showError((detail?.detail || 'Unable to save or load tasks. Check your connection and try again.') +
      (detail?.errors ? ' ' + detail.errors.map(e => e.message).join(' ') : ''));
  }
  function controls() {
    $('#add-task, #clear-completed, #import-browser, #export-tasks, #task-form button[type="submit"]').prop('disabled', busy || !loaded);
    $('.task-check, .edit-task, .delete-task').prop('disabled', busy || !loaded);
    $('#refresh-tasks').prop('disabled', busy);
    if (!tasks.some(t => t.completed)) $('#clear-completed').prop('disabled', true);
  }
  async function load() {
    tasks = (await request('GET')).map(fromApi); loaded = true; render();
  }
  async function operation(work, message) {
    if (busy) return;
    busy = true; controls(); $('#storage-error').prop('hidden', true);
    try { await work(); if (message) $('#announcement, #task-status').text(message); }
    catch (xhr) { failure(xhr); }
    finally { busy = false; render(); controls(); }
  }
  function replaceTask(task) {
    const item = fromApi(task);
    tasks = [item, ...tasks.filter(t => t.id !== item.id)];
  }
  // Import is explicit and retryable; existing browser data is never removed.
  function browserTasks() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return [];
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed)) throw new Error('Invalid browser task data.');
    return parsed;
  }
  $('#import-browser').on('click', () => operation(async () => {
    let saved;
    try { saved = browserTasks(); }
    catch (_) { showError('Browser tasks could not be read. Existing data has not been changed.'); return; }
    if (!saved.length) { showError('No saved tasks were found for this account in this browser.'); return; }
    for (const task of saved) {
      if (!task || typeof task.id !== 'string') throw {responseJSON: {detail: 'A saved task is invalid. Existing browser data is unchanged.'}};
      replaceTask(await request('POST', '/import', {
        legacy_id: task.id, title: task.title, notes: task.notes,
        priority: task.priority, due: task.due || null, completed: task.completed
      }));
    }
    $('#announcement, #task-status').text('Browser tasks imported. Repeating an import will not duplicate tasks.');
  }));
  $('#refresh-tasks').on('click', () => operation(load, 'Tasks refreshed.'));
  $('#export-tasks').on('click', () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(tasks, null, 2)], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'taskwell-tasks.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  function render() {
    const done = tasks.filter(t => t.completed).length;
    const percentage = tasks.length ? Math.round(done / tasks.length * 100) : 0;
    $('#stat-total, #nav-count').text(tasks.length);
    $('#stat-active').text(tasks.length - done); $('#stat-done').text(done);
    $('#stat-progress').html(`${percentage}<span>%</span>`); $('#progress-fill').css('width', `${percentage}%`);
    $('#remaining-count').text(`${tasks.length - done} ${tasks.length - done === 1 ? 'task' : 'tasks'} left in total`);
    $('#clear-completed').prop('disabled', !done);
    const query = $('#search').val().trim().toLowerCase();
    let visible = tasks.filter(t => (view !== 'overdue' || t.due && t.due < today() && !t.completed) && (view !== 'today' || t.due === today()) && (view !== 'upcoming' || t.due > today() && !t.completed) && (view !== 'completed' || t.completed) && (status !== 'active' || !t.completed) && (status !== 'completed' || t.completed) && `${t.title} ${t.notes}`.toLowerCase().includes(query));
    const priority = { high: 0, medium: 1, low: 2 };
    const sort = $('#sort').val();
    visible.sort((a, b) => sort === 'due' ? (a.due || '9999').localeCompare(b.due || '9999') || b.createdAt - a.createdAt : sort === 'priority' ? priority[a.priority] - priority[b.priority] || b.createdAt - a.createdAt : b.createdAt - a.createdAt);
    $('#list-count').text(`${visible.length} ${visible.length === 1 ? 'task' : 'tasks'}`);
    $('#task-list').html(!loaded ? '<div class="empty-state"><strong>Tasks are not loaded yet.</strong>Use Refresh to try again if loading fails.</div>' : visible.length ? visible.map(t => `<article class="task-row ${t.completed ? 'done' : ''}" data-id="${escape(t.id)}"><div class="task-main"><input type="checkbox" class="task-check" aria-label="${escape(`Mark ${t.title} ${t.completed ? 'active' : 'complete'}`)}" ${t.completed ? 'checked' : ''}><div class="task-copy"><div class="task-title">${escape(t.title)}</div>${t.notes ? `<div class="task-notes">${escape(t.notes)}</div>` : ''}</div></div><span class="badge-priority priority-${t.priority}">${t.priority}</span><span class="due-date ${t.due && t.due < today() && !t.completed ? 'overdue' : ''}">${escape(dateLabel(t.due))}</span><div class="task-actions"><button class="icon-btn edit-task" aria-label="${escape(`Edit ${t.title}`)}" title="Edit task">✎</button><button class="icon-btn delete-task" aria-label="${escape(`Delete ${t.title}`)}" title="Delete task">×</button></div></article>`).join('') : '<div class="empty-state"><strong>A little breathing room.</strong>No tasks here. Add a new task or try another filter.</div>');
  }
  function openForm(task) {
    editingId = task ? task.id : null;
    $('#task-title')[0].setCustomValidity('');
    $('#task-form')[0].reset(); $('#modal-title').text(task ? 'Edit task' : 'New task');
    $('#task-title').val(task?.title || ''); $('#task-notes').val(task?.notes || '');
    $('#task-priority').val(task?.priority || 'medium'); $('#task-due').val(task?.due || '');
    modal.show();
  }
  $('#task-modal').on('shown.bs.modal', () => $('#task-title').trigger('focus'));
  $('#add-task').on('click', () => openForm());
  $('#task-form').on('submit', function (event) {
    event.preventDefault();
    const title = $('#task-title').val().trim();
    if (!title) { document.getElementById('task-title').setCustomValidity('Enter a task title.'); document.getElementById('task-title').reportValidity(); return; }
    const original = tasks.find(t => t.id === editingId);
    const values = { title, notes: $('#task-notes').val().trim(), priority: $('#task-priority').val(),
      due: $('#task-due').val() || null, completed: original?.completed || false };
    operation(async () => {
      replaceTask(await request(editingId ? 'PUT' : 'POST', editingId ? `/${editingId}` : '', values));
      modal.hide();
    }, editingId ? 'Task updated.' : 'Task added.');
  });
  $('#task-title').on('input', function () { this.setCustomValidity(''); });
  $('#task-list').on('change', '.task-check', function () {
    const id = $(this).closest('.task-row').attr('data-id'), completed = this.checked;
    if (busy) { render(); controls(); return; }
    operation(async () => replaceTask(await request('PATCH', `/${id}`, {completed})), 'Task status updated.');
  });
  $('#task-list').on('click', '.edit-task', function () { openForm(tasks.find(t => t.id === $(this).closest('.task-row').attr('data-id'))); });
  $('#task-list').on('click', '.delete-task', function () {
    const id = $(this).closest('.task-row').attr('data-id'), task = tasks.find(t => t.id === id);
    if (window.confirm(`Delete “${task.title}”?`)) operation(async () => {
      await request('DELETE', `/${id}`); tasks = tasks.filter(t => t.id !== id);
    }, 'Task deleted.');
  });
  $('#clear-completed').on('click', () => {
    if (window.confirm('Delete all completed tasks?')) operation(async () => {
      await request('DELETE', '/completed'); tasks = tasks.filter(t => !t.completed);
    }, 'Completed tasks cleared.');
  });
  $('.nav-item').on('click', function () {
    view = $(this).attr('data-view'); status = 'all';
    $('.nav-item').removeClass('active'); $(this).addClass('active');
    $('.filter-tabs button').removeClass('active').filter('[data-status="all"]').addClass('active');
    const titles = { overdue: 'Overdue', all: 'All tasks', today: 'Today', upcoming: 'Upcoming', completed: 'Completed' };
    $('#view-title').html(`${titles[view]}<span>.</span>`); render(); controls();
  });
  $('.filter-tabs button').on('click', function () { status = $(this).attr('data-status'); $('.filter-tabs button').removeClass('active'); $(this).addClass('active'); render(); controls(); });
  $('#search').on('input', () => {render(); controls();}); $('#sort').on('change', () => {render(); controls();});
  $('#header-date').text(new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }));
  render(); controls(); operation(load);
  // Refresh when returning from another tab/device, without clobbering an edit.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !$('#task-modal').hasClass('show') && !busy) operation(load);
  });
}); });
