import uuid
from django.db import models
from django.utils import timezone
from user.models import Account


class UserChat(models.Model):
    chat_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1 = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='chats_as_user1')
    user2 = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='chats_as_user2')
    created = models.DateTimeField(default=timezone.now, editable=False)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'User Chats'
        ordering = ['-updated']
        unique_together = [['user1', 'user2']]

    def __str__(self):
        return f"Chat: {self.user1.username} - {self.user2.username}"


class GroupChat(models.Model):
    chat_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='groups_created')
    members = models.ManyToManyField(Account, related_name='groups_joined')
    profile_pic = models.URLField(blank=True, null=True)
    created = models.DateTimeField(default=timezone.now, editable=False)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Group Chats'
        ordering = ['-updated']

    def __str__(self):
        return self.name


class Message(models.Model):
    CHAT_TYPE_CHOICES = [
        ('user', 'User Chat'),
        ('group', 'Group Chat'),
    ]

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='messages_sent')
    text_content = models.TextField()
    file_content_url = models.URLField(blank=True, null=True)
    chat_type = models.CharField(max_length=10, choices=CHAT_TYPE_CHOICES)
    user_chat = models.ForeignKey(UserChat, on_delete=models.CASCADE, null=True, blank=True, related_name='user-messages')
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, null=True, blank=True, related_name='group-messages')
    created = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name_plural = 'Messages'
        ordering = ['created']

    def __str__(self):
        return f"{self.sender.username}: {self.text_content[:50]}"
