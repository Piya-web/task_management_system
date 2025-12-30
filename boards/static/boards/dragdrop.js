function allowDrop(ev) {
    ev.preventDefault();
}

function dragTask(ev) {
    // Store the ID of the task being dragged
    ev.dataTransfer.setData("taskId", ev.target.getAttribute("data-task-id"));
}

function dropTask(ev) {
    ev.preventDefault();
    const taskId = ev.dataTransfer.getData("taskId");
    const taskElement = document.querySelector(`[data-task-id='${taskId}']`);
    
    // Find the column where the task was dropped
    const columnElement = ev.currentTarget;
    const columnId = columnElement.getAttribute("data-column-id");
    const taskList = columnElement.querySelector(".kanban-tasks");

    // Move visually immediately for the current user
    taskList.appendChild(taskElement);

    // Save to Database via AJAX
    const formData = new FormData();
    formData.append("task_id", taskId);
    formData.append("new_column_id", columnId);

    fetch("/boards/move-task/", {
        method: "POST",
        body: formData,
        headers: {
            "X-CSRFToken": getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log("Task moved and saved to DB");
            // TRIGGER WEBSOCKET BROADCAST (Step 7 Logic)
            if (window.boardSocket) {
                window.boardSocket.send(JSON.stringify({
                    'type': 'task_moved',
                    'task_id': taskId,
                    'new_column_id': columnId
                }));
            }
        }
    })
    .catch(error => console.error("Error moving task:", error));
}

function getCSRFToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === ('csrftoken' + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}