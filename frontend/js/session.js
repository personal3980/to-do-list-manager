// Gate the demo dashboard on an active server-side session.
window.taskwellSession = $.ajax({ url: `${window.TASKWELL_API}/me`, xhrFields: { withCredentials: true } });
window.taskwellSession.done(function (user) {
  window.taskwellUser = user;
  $(function () {
    $('.account-name').text(user.name);
    document.documentElement.classList.remove('auth-checking');
    let checking = false;
    function recheckSession() {
      if (checking || document.visibilityState === 'hidden') return;
      checking = true;
      $.ajax({ url: `${window.TASKWELL_API}/me`, xhrFields: { withCredentials: true } })
        .done(function (current) {
          if (current.id !== user.id) {
            document.documentElement.classList.add('auth-checking');
            location.replace('index.html');
          }
        }).fail(function (xhr) {
          if (xhr.status === 401) {
            document.documentElement.classList.add('auth-checking');
            location.replace('login.html');
          } else {
            $('#account-error').text('Session check failed. Check your connection and reload.');
          }
        }).always(function () { checking = false; });
    }
    // Check active tabs and pages restored from browser history, too.
    setInterval(recheckSession, 60000);
    window.addEventListener('focus', recheckSession);
    window.addEventListener('pageshow', event => { if (event.persisted) recheckSession(); });
    document.addEventListener('visibilitychange', recheckSession);
    $('#logout').on('click', function () {
      $(this).prop('disabled', true);
      $.ajax({ url: `${window.TASKWELL_API}/logout`, method: 'POST', contentType: 'application/json',
        data: '{}', xhrFields: { withCredentials: true }
      }).done(() => location.replace('login.html')).fail(() => {
        $('#account-error').text('Logout failed. Please try again.'); $('#logout').prop('disabled', false);
      });
    });
  });
}).fail(function (xhr) {
  if (xhr.status === 401) location.replace('login.html');
  else $(function () {
    // Keep private dashboard contents hidden when the session cannot be checked.
    const panel = $('<main class="empty-state">');
    panel.append($('<strong>').text('Unable to check your session.'));
    panel.append($('<p>').text('Start the backend on localhost:8000, then reload this page.'));
    panel.append($('<a href="login.html">').text('Go to login'));
    $('body').empty().append(panel);
  });
});
