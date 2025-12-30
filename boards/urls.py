from django.urls import path
from . import views

urlpatterns = [
    # Board & Team Management
    path('', views.board_list, name='board_list'),
    path('create/', views.create_board, name='create_board'),
    path('teams/', views.team_list, name='team_list'),
    path('teams/create/', views.create_team, name='create_team'),
    path('<int:board_id>/', views.board_detail, name='board_detail'),
    path('<int:board_id>/invite/', views.invite_user, name='invite_user'),
    
    # Task Management
    path('<int:board_id>/add_task/', views.add_task, name='add_task'),
    path('task/<int:task_id>/', views.task_detail, name='task_detail'),
    path('task/<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('move-task/', views.move_task, name='move_task'),
    
    # Subtasks & Attachments
    path('task/<int:task_id>/subtask/add/', views.add_subtask, name='add_subtask'),
    path('subtask/<int:subtask_id>/toggle/', views.toggle_subtask, name='toggle_subtask'),
    path('task/<int:task_id>/attachment/add/', views.add_attachment, name='add_attachment'),
    path('attachment/<int:attach_id>/delete/', views.delete_attachment, name='delete_attachment'),
    
    # Notifications & Auth
    path('notifications/', views.notifications_panel, name='notifications'),
    path('notifications/read/<int:note_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('signup/', views.signup, name='signup'),
]