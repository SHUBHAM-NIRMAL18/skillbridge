from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

User = get_user_model()

class CandidateEvent(models.Model):
    VIEW="view"; SAVE="save"; APPLY="apply"; DISMISS="dismiss"
    EVENT_CHOICES=[(VIEW,"view"),(SAVE,"save"),(APPLY,"apply"),(DISMISS,"dismiss")]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    item_object_id = models.PositiveIntegerField()
    item = GenericForeignKey("item_content_type","item_object_id")
    event_type = models.CharField(max_length=16, choices=EVENT_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["user","created_at"]),
            models.Index(fields=["item_content_type","item_object_id"]),
            models.Index(fields=["event_type"]),
        ]
