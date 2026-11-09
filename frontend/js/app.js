/* Tasks remain browser-local. Authentication uses the API in session.js.
   Replace task read/write operations when a task API is implemented. */
window.taskwellSession.done(function (user) { $(function () {
  'use strict';
  const STORAGE_KEY = `taskwell.tasks.user.${user.id}.v1`;
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const uid = () => window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const escape = value => $('<span>').text(value).html().replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const dateLabel = value => !value ? 'No due date' : new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  let tasks = [], view = 'all', status = 'all', editingId = null;
  const modal = new bootstrap.Modal(document.getElementById('task-modal'));
  function storageError(message) { $('#storage-error').text(message).prop('hidden', false); }
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) {
      const parsed = JSON.parse(saved);
      if (!Array.isArray(parsed) || !parsed.every(t => t && typeof t.id === 'string' && typeof t.title === 'string' && typeof t.notes === 'string' && ['low', 'medium', 'high'].includes(t.priority) && typeof t.completed === 'boolean' && typeof t.createdAt === 'number' && typeof t.due === 'string' && (t.due === '' || /^\d{4}-\d{2}-\d{2}$/.test(t.due)))) throw new Error('Invalid saved tasks');
      tasks = parsed;
    } else {
      tasks = [
        { title: 'Plan the week ahead', notes: 'A few clear priorities make all the difference.', priority: 'high', due: today(), completed: false },
        { title: 'Make time for a little learning', notes: 'Read a chapter, try something new, stay curious.', priority: 'medium', due: '', completed: false },
        { title: 'Organize your workspace', notes: 'A fresh space for a fresh start.', priority: 'low', due: '', completed: true }
      ].map((t, i) => ({ ...t, id: uid(), createdAt: Date.now() - i }));
      persist();
    }
  } catch (_) { storageError('Saved tasks could not be loaded. Your existing browser data has not been changed. Changes may overwrite it; back it up before continuing.'); }
  function persist() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks)); }
    catch (_) { storageError('Changes are available for this session only. Browser storage is unavailable or full.'); }
  }
  function changed(message) { persist(); render(); $('#announcement').text(message); }
  function render() {
    const done = tasks.filter(t => t.completed).length;
    const percentage = tasks.length ? Math.round(done / tasks.length * 100) : 0;
    $('#stat-total, #nav-count').text(tasks.length);
    $('#stat-active').text(tasks.length - done); $('#stat-done').text(done);
    $('#stat-progress').html(`${percentage}<span>%</span>`); $('#progress-fill').css('width', `${percentage}%`);
    $('#remaining-count').text(`${tasks.length - done} ${tasks.length - done === 1 ? 'task' : 'tasks'} left in total`);
    $('#clear-completed').prop('disabled', !done);
    const query = $('#search').val().trim().toLowerCase();
    let visible = tasks.filter(t => (view !== 'today' || t.due === today()) && (view !== 'upcoming' || t.due > today() && !t.completed) && (view !== 'completed' || t.completed) && (status !== 'active' || !t.completed) && (status !== 'completed' || t.completed) && `${t.title} ${t.notes}`.toLowerCase().includes(query));
    const priority = { high: 0, medium: 1, low: 2 };
    const sort = $('#sort').val();
    visible.sort((a, b) => sort === 'due' ? (a.due || '9999').localeCompare(b.due || '9999') || b.createdAt - a.createdAt : sort === 'priority' ? priority[a.priority] - priority[b.priority] || b.createdAt - a.createdAt : b.createdAt - a.createdAt);
    $('#list-count').text(`${visible.length} ${visible.length === 1 ? 'task' : 'tasks'}`);
    $('#task-list').html(visible.length ? visible.map(t => `<article class="task-row ${t.completed ? 'done' : ''}" data-id="${escape(t.id)}"><div class="task-main"><input type="checkbox" class="task-check" aria-label="${escape(`Mark ${t.title} ${t.completed ? 'active' : 'complete'}`)}" ${t.completed ? 'checked' : ''}><div class="task-copy"><div class="task-title">${escape(t.title)}</div>${t.notes ? `<div class="task-notes">${escape(t.notes)}</div>` : ''}</div></div><span class="badge-priority priority-${t.priority}">${t.priority}</span><span class="due-date ${t.due && t.due < today() && !t.completed ? 'overdue' : ''}">${escape(dateLabel(t.due))}</span><div class="task-actions"><button class="icon-btn edit-task" aria-label="${escape(`Edit ${t.title}`)}" title="Edit task">✎</button><button class="icon-btn delete-task" aria-label="${escape(`Delete ${t.title}`)}" title="Delete task">×</button></div></article>`).join('') : '<div class="empty-state"><strong>A little breathing room.</strong>No tasks here. Add a new task or try another filter.</div>');
  }
  function openForm(task) {
    editingId = task ? task.id : null;
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
    const values = { title, notes: $('#task-notes').val().trim(), priority: $('#task-priority').val(), due: $('#task-due').val() };
    if (editingId) tasks = tasks.map(t => t.id === editingId ? { ...t, ...values } : t);
    else tasks.unshift({ ...values, id: uid(), completed: false, createdAt: Date.now() });
    changed(editingId ? 'Task updated.' : 'Task added.'); modal.hide();
  });
  $('#task-title').on('input', function () { this.setCustomValidity(''); });
  $('#task-list').on('change', '.task-check', function () { const id = $(this).closest('.task-row').attr('data-id'); tasks = tasks.map(t => t.id === id ? { ...t, completed: this.checked } : t); changed('Task status updated.'); });
  $('#task-list').on('click', '.edit-task', function () { openForm(tasks.find(t => t.id === $(this).closest('.task-row').attr('data-id'))); });
  $('#task-list').on('click', '.delete-task', function () { const id = $(this).closest('.task-row').attr('data-id'); const task = tasks.find(t => t.id === id); if (window.confirm(`Delete “${task.title}”?`)) { tasks = tasks.filter(t => t.id !== id); changed('Task deleted.'); } });
  $('#clear-completed').on('click', () => { if (window.confirm('Delete all completed tasks?')) { tasks = tasks.filter(t => !t.completed); changed('Completed tasks cleared.'); } });
  $('.nav-item').on('click', function () {
    view = $(this).attr('data-view'); status = 'all';
    $('.nav-item').removeClass('active'); $(this).addClass('active');
    $('.filter-tabs button').removeClass('active').filter('[data-status="all"]').addClass('active');
    const titles = { all: 'All tasks', today: 'Today', upcoming: 'Upcoming', completed: 'Completed' };
    $('#view-title').html(`${titles[view]}<span>.</span>`); render();
  });
  $('.filter-tabs button').on('click', function () { status = $(this).attr('data-status'); $('.filter-tabs button').removeClass('active'); $(this).addClass('active'); render(); });
  $('#search').on('input', render); $('#sort').on('change', render);
  $('#header-date').text(new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }));
  render();
}); });
