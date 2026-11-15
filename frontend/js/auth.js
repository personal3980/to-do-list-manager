$(function () {
  'use strict';
  const mode = document.body.dataset.authMode;
  const form = document.getElementById('auth-form');
  let resetToken = '';
  function message(text, error = false) {
    $('#auth-message').text(text).toggleClass('error', error).prop('hidden', false);
  }
  if (mode === 'reset-password') {
    resetToken = new URLSearchParams(location.hash.slice(1)).get('token') || '';
    // Remove the token from the address bar and history as soon as it is read.
    history.replaceState(null, '', location.pathname);
    if (!/^[A-Za-z0-9_-]{43}$/.test(resetToken)) {
      message('This reset link is missing or invalid. Request a new link below.', true);
      $('#auth-form :input').prop('disabled', true);
    }
  }
  if (mode === 'login' && new URLSearchParams(location.search).has('registered')) {
    message('Account created. You can now log in.');
  }
  $('#auth-form input').on('input', function () { this.setCustomValidity(''); });
  $('#password, #confirm_password').on('input', function () {
    document.getElementById('confirm_password')?.setCustomValidity('');
  });
  $('#auth-form').on('submit', function (event) {
    event.preventDefault();
    const data = {};
    $(this).serializeArray().forEach(field => { data[field.name] = field.value; });
    if (data.email !== undefined) { data.email = data.email.trim().toLowerCase(); $('#email').val(data.email); }
    if (data.name !== undefined) {
      data.name = data.name.trim(); $('#name').val(data.name);
      if (data.name.length < 2) document.getElementById('name').setCustomValidity('Enter at least two characters.');
    }
    if (mode === 'signup' || mode === 'reset-password') {
      if (!/[a-z]/i.test(data.password) || !/[0-9]/.test(data.password)) {
        document.getElementById('password').setCustomValidity('Include at least one letter and one number.');
      }
      if (data.password !== data.confirm_password) {
        document.getElementById('confirm_password').setCustomValidity('Passwords do not match.');
      }
    }
    if (!form.reportValidity()) return;
    if (mode === 'reset-password') data.token = resetToken;
    const button = $('#auth-form button[type="submit"]');
    button.prop('disabled', true); $('#auth-message').prop('hidden', true);
    $.ajax({ url: `${window.TASKWELL_API}/${mode}`, method: 'POST', contentType: 'application/json',
      data: JSON.stringify(data), xhrFields: { withCredentials: true }
    }).done(function (result) {
      if (mode === 'signup') location.replace('login.html?registered=1');
      else if (mode === 'login') location.replace('index.html');
      else {
        message(result.message); form.reset();
        if (mode === 'reset-password') $('#auth-form :input').prop('disabled', true);
      }
    }).fail(function (xhr) {
      const response = xhr.responseJSON;
      let text = response?.detail || 'Cannot reach the API. Check that the backend is running on localhost:8000.';
      if (Array.isArray(response?.errors)) text += '\n' + response.errors.map(e => `${e.field ? e.field + ': ' : ''}${e.message}`).join('\n');
      message(text, true);
    }).always(function () { if (mode !== 'reset-password' || !$('#password').prop('disabled')) button.prop('disabled', false); });
  });
});
