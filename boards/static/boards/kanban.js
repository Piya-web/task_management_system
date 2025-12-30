// --- WebSocket Setup ---
// boardId is provided globally in the template base.html
const board_id = typeof boardId !== 'undefined' ? boardId : null;

if (board_id) {
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    window.boardSocket = new WebSocket(
        ws_scheme + '://' + window.location.host + '/ws/boards/' + board_id + '/'
    );

    window.boardSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log("WebSocket Message Received:", data);

        // Handle Task Moved
        if (data.type === "task_moved") {
            // Smoothly move the task element to the new column on other screens
            const taskEl = document.querySelector(`[data-task-id='${data.task_id}']`);
            const targetCol = document.querySelector(`[data-column-id='${data.new_column_id}'] .kanban-tasks`);
            if (taskEl && targetCol) {
                targetCol.appendChild(taskEl);
            }
        }

        // Handle Task Locking
        if (data.type === "task_locked") {
            const el = document.querySelector(`[data-task-id='${data.task_id}']`);
            if (el) el.classList.add("locked");
        }

        // Handle Task Unlocking
        if (data.type === "task_unlocked") {
            const el = document.querySelector(`[data-task-id='${data.task_id}']`);
            if (el) el.classList.remove("locked");
        }
    };

    window.boardSocket.onclose = function(e) {
        console.error('Board socket closed unexpectedly');
    };
}