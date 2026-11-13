// Gate the demo dashboard on an active server-side session.
window.taskwellSession = $.ajax({ url: `${window.TASKWELL_API}/me`, xhrFields: { withCredentials: true } });
window.taskwellSession.done(function (user) {
  window.taskwellUser = user;
  $(function () {
    $('.account-name').text(user.name);
    document.documentElement.classList.remove('auth-checking');
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
