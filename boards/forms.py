from django import forms
from .models import Task
from django.contrib.auth.models import User
from .models import SubTask
from .models import Attachment
from .models import Task, Column

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'column', 'priority', 'due_date', 'assigned_to']

    def __init__(self, *args, **kwargs):
        # We "pop" the board out of the arguments passed from the view
        board = kwargs.pop('board', None)
        super().__init__(*args, **kwargs)
        
        if board:
            # This line ensures the dropdown ONLY shows columns for THIS board
            self.fields['column'].queryset = Column.objects.filter(board=board)

class BoardInviteForm(forms.Form):
    username_or_email = forms.CharField(label="Username or Email")

    def clean_username_or_email(self):
        data = self.cleaned_data["username_or_email"]
        try:
            user = User.objects.get(username=data)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=data)
            except User.DoesNotExist:
                raise forms.ValidationError("No user found with that username or email.")
        return user
    
class SubTaskForm(forms.ModelForm):
    class Meta:
        model = SubTask
        fields = ["title", "is_completed"]

class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ["file"]