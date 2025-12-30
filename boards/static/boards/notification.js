// --- Notifications WebSocket ---
const userId = document.body.dataset.userid; // from base.html body tag
const notifSocket = new WebSocket(
  'ws://' + window.location.host + '/ws/notifications/' + userId + '/'
);

notifSocket.onmessage = function(e) {
  const data = JSON.parse(e.data);
  // update badge instantly
  document.getElementById("notif-count").textContent = "(" + data.unread + ")";
};