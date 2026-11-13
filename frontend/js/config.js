// Keep the API on the page's hostname: localhost and 127.0.0.1 are
// different sites for session-cookie rules, even on the same computer.
const taskwellApiUrl = new URL(window.location.origin);
taskwellApiUrl.port = '8000';
taskwellApiUrl.pathname = '/api/auth';
window.TASKWELL_API = taskwellApiUrl.href;
