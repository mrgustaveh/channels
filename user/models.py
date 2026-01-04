import uuid
from django.db import models
from django.utils import timezone


class Account(models.Model):
    account_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clerk_id = models.TextField(blank=True, null=True, unique=True)
    username = models.CharField(max_length=16, blank=True, null=True, unique=True)
    display_pic = models.URLField(blank=True, null=True)
    created = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name_plural = 'Accounts'
        ordering = ['created']
    
    def __str__(self):
        return self.username if self.username else str(self.account_id).split('-')[0]
        