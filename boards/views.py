from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Board, Column, Task, SubTask, Notification, Team, Attachment
from .forms import TaskForm, SubTaskForm, BoardInviteForm, AttachmentForm

# --- User Authentication ---
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("board_list")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})

# --- Team Management ---
@login_required
def team_list(request):
    """List all teams the user belongs to or owns."""
    teams = request.user.teams.all() | Team.objects.filter(owner=request.user)
    return render(request, "boards/team_list.html", {"teams": teams.distinct()})

@login_required
def create_team(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if Team.objects.filter(name=name).exists():
            messages.error(request, "Team name already exists.")
        else:
            team = Team.objects.create(name=name, owner=request.user)
            team.members.add(request.user)
            messages.success(request, f"Team '{name}' created!")
            return redirect("team_list")
    return render(request, "boards/create_team.html")

# --- Board Management ---
@login_required
def board_list(request):
    team_id = request.GET.get("team")
    if team_id:
        boards = Board.objects.filter(team_id=team_id, members=request.user)
    else:
        boards = Board.objects.filter(members=request.user)
    return render(request, 'boards/board_list.html', {'boards': boards})

@login_required
def create_board(request):
    teams = request.user.teams.all()
    if request.method == "POST":
        name = request.POST.get("name")
        desc = request.POST.get("description", "")
        team_id = request.POST.get("team_id")
        team = get_object_or_404(Team, id=team_id) if team_id else None
        board = Board.objects.create(name=name, description=desc, owner=request.user, team=team)
        board.members.add(request.user)
        return redirect("board_detail", board_id=board.id)
    return render(request, "boards/create_board.html", {"teams": teams})

@login_required
def board_detail(request, board_id):
    # 1. Get the board and verify user is a member
    board = get_object_or_404(Board, id=board_id, members=request.user)
    
    # 2. Get columns for THIS board and "pre-fetch" their tasks
    # We use 'tasks' because that is the related_name we set in models.py
    columns = board.columns.all().order_by('order').prefetch_related('tasks', 'tasks__assigned_to')
    
    return render(request, 'boards/board_detail.html', {
        'board': board,
        'columns': columns
    })

@login_required
def invite_user(request, board_id):
    board = get_object_or_404(Board, id=board_id, owner=request.user)
    if request.method == "POST":
        form = BoardInviteForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["username_or_email"]
            board.members.add(user)
            Notification.objects.create(user=user, message=f"Invited to {board.name}")
            messages.success(request, f"{user.username} added!")
            return redirect('board_detail', board_id=board.id)
    else:
        form = BoardInviteForm()
    return render(request, "boards/invite_user.html", {"board": board, "form": form})

# --- Task Management ---
@login_required
def add_task(request, board_id):
    board = get_object_or_404(Board, id=board_id, members=request.user)
    if request.method == "POST":
        form = TaskForm(request.POST, board=board)
        if form.is_valid():
            task = form.save(commit=False)
            task.board = board
            task.created_by = request.user
            task.save()
            form.save_m2m() # Saves assigned users
            return redirect("board_detail", board_id=board.id)
    else:
        form = TaskForm(board=board)
    return render(request, "boards/add_task.html", {"form": form, "board": board})

@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return render(request, "boards/task_detail.html", {"task": task})

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    board = task.board
    channel_layer = get_channel_layer()

    # Collision Prevention
    if task.is_locked and task.locked_by and task.locked_by != request.user:
        messages.error(request, f"This task is being edited by {task.locked_by.username}")
        return redirect("board_detail", board.id)

    if request.method == "GET":
        task.is_locked, task.locked_by, task.lock_timestamp = True, request.user, timezone.now()
        task.save()
        # Broadcast Lock
        async_to_sync(channel_layer.group_send)(f"board_{board.id}", {"type": "board_update", "data": {"type": "task_locked", "task_id": task.id, "locked_by": request.user.username}})

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, board=board)
        if form.is_valid():
            form.save()
            task.is_locked, task.locked_by = False, None
            task.save()
            # Broadcast Unlock
            async_to_sync(channel_layer.group_send)(f"board_{board.id}", {"type": "board_update", "data": {"type": "task_unlocked", "task_id": task.id}})
            return redirect("task_detail", task_id=task.id)
    else:
        form = TaskForm(instance=task, board=board)
    return render(request, "boards/edit_task.html", {"form": form, "task": task})

@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    board_id = task.board.id
    task.delete()
    return redirect('board_detail', board_id=board_id)

@login_required
@require_POST
def move_task(request):
    task_id = request.POST.get("task_id")
    new_col_id = request.POST.get("new_column_id")
    task = get_object_or_404(Task, id=task_id)
    new_col = get_object_or_404(Column, id=new_col_id)
    task.column = new_col
    task.save()
    
    # WebSocket Broadcast
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"board_{task.board.id}", {"type": "board_update", "data": {"type": "task_moved", "task_id": task.id}})
    return JsonResponse({"success": True})

# --- Subtasks & Attachments ---
@login_required
def add_subtask(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == "POST":
        form = SubTaskForm(request.POST)
        if form.is_valid():
            sub = form.save(commit=False); sub.task = task; sub.save()
            return redirect("task_detail", task_id=task.id)
    return render(request, "boards/add_subtask.html", {"form": SubTaskForm(), "task": task})

@login_required
def toggle_subtask(request, subtask_id):
    sub = get_object_or_404(SubTask, id=subtask_id)
    sub.is_completed = not sub.is_completed; sub.save()
    return redirect("task_detail", task_id=sub.task.id)

@login_required
def add_attachment(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == "POST":
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attach = form.save(commit=False); attach.task, attach.uploaded_by = task, request.user; attach.save()
            return redirect("task_detail", task_id=task.id)
    return render(request, "boards/add_attachment.html", {"form": AttachmentForm(), "task": task})

@login_required
def delete_attachment(request, attach_id):
    attach = get_object_or_404(Attachment, id=attach_id)
    task_id = attach.task.id
    attach.delete()
    return redirect("task_detail", task_id=task_id)

# --- Notifications ---
@login_required
def notifications_panel(request):
    notes = request.user.notifications.all().order_by('-created_at')
    return render(request, "boards/notifications.html", {"notifications": notes})

@login_required
def mark_notification_read(request, note_id):
    note = get_object_or_404(Notification, id=note_id, user=request.user)
    note.is_read = True; note.save()
    return redirect('notifications')

@login_required
def clear_notifications(request):
    request.user.notifications.all().delete()
    return redirect('notifications')