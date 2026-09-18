from .models import Notification, Conversation, Message


def communications_context(request):
    """
    Supplies unread notification and messaging metrics to all templates.
    """
    if not request.user.is_authenticated:
        return {
            "unread_notifications_count": 0,
            "recent_notifications": [],
            "unread_messages_count": 0,
        }

    unread_notifs = Notification.objects.filter(recipient=request.user, is_read=False)
    unread_notifs_count = unread_notifs.count()
    recent_notifs = Notification.objects.filter(recipient=request.user)[:5]

    # Unread messages count
    # Count messages in user's conversations where sender != current user and is_read == False
    unread_messages_count = Message.objects.filter(
        conversation__candidate__user=request.user,
        is_read=False
    ).exclude(sender=request.user).count() + Message.objects.filter(
        conversation__company__user=request.user,
        is_read=False
    ).exclude(sender=request.user).count()

    return {
        "unread_notifications_count": unread_notifs_count,
        "recent_notifications": recent_notifs,
        "unread_messages_count": unread_messages_count,
    }
