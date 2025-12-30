from django.db import models
from django.contrib.auth.models import User
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_teams"
    )
    members = models.ManyToManyField(User, related_name="teams", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Board(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_boards"
    )
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="boards"
    )
    members = models.ManyToManyField(User, related_name="boards", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Column(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="columns")
    title = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.board.name} → {self.title}"


class Task(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="tasks")
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="tasks")
    assigned_to = models.ManyToManyField(User, blank=True, related_name="tasks")
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title
    
    # --- Locking fields ---
    is_locked = models.BooleanField(default=False)
    locked_by = models.ForeignKey(
    User, on_delete=models.SET_NULL, null=True, blank=True, related_name="task_locks"
)
lock_timestamp = models.DateTimeField(null=True, blank=True)

class Attachment(models.Model):
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="attachments/")
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name.split('/')[-1]}"

class SubTask(models.Model):
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="subtasks"
    )
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({'Done' if self.is_completed else 'Pending'})"

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username}: {self.content[:20]}"
    
    def save(self, *args, **kwargs):
        channel_layer = get_channel_layer()
        for u in self.task.assigned_to.exclude(id=self.author.id):
            async_to_sync(channel_layer.group_send)(f"notif_{u.id}",{"type": "notification_update","data": {"unread": u.notifications.filter(is_read=False).count()}})


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To {self.user.username}: {self.message}"
    
def user_initials(self):
    parts = (self.first_name + " " + self.last_name).strip().split()
    if parts:
        return "".join(p[0].upper() for p in parts)[:2]
    return self.username[:2].upper()

User.add_to_class("initials", user_initials)


@receiver(post_save, sender=Board)
def ensure_board_has_columns(sender, instance, created, **kwargs):
    """Automatically create Kanban stages whenever a new board is made."""
    if created:
        # These 3 lines ensure every new board is 'born' with its stages
        Column.objects.get_or_create(board=instance, title="To Do", defaults={'order': 1})
        Column.objects.get_or_create(board=instance, title="In Progress", defaults={'order': 2})
        Column.objects.get_or_create(board=instance, title="Done", defaults={'order': 3})

@receiver(post_save, sender=Board)
def ensure_board_has_columns(sender, instance, created, **kwargs):
    if created:
        Column.objects.get_or_create(board=instance, title="To Do", defaults={'order': 1})
        Column.objects.get_or_create(board=instance, title="In Progress", defaults={'order': 2})
        Column.objects.get_or_create(board=instance, title="Done", defaults={'order': 3})