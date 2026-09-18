from django.urls import reverse
from django.utils import timezone
from .models import Notification, Conversation, Message


def notify_user(recipient, title, message, action_url="", sender=None, notification_type="system"):
    """
    Creates an in-app notification for the recipient.
    """
    if not recipient or not recipient.is_authenticated:
        return None
    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        action_url=action_url,
        notification_type=notification_type,
    )


def get_or_create_conversation(candidate, company, application=None, subject=None):
    """
    Finds or creates a 2-way conversation thread between a Candidate and a Company.
    """
    qs = Conversation.objects.filter(candidate=candidate, company=company)
    if application:
        existing = qs.filter(application=application).first()
        if existing:
            return existing, False

    existing = qs.first()
    if existing:
        if application and not existing.application:
            existing.application = application
            existing.save(update_fields=["application", "updated_at"])
        return existing, False

    if not subject:
        if application:
            subject = f"Application: {application.target_title}"
        else:
            subject = f"Opportunity Discussion: {company.company_name}"

    convo = Conversation.objects.create(
        candidate=candidate,
        company=company,
        application=application,
        subject=subject
    )
    return convo, True


def send_conversation_message(conversation, sender_user, text):
    """
    Appends a message to a conversation thread and alerts the other party.
    """
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        raise ValueError("Message cannot be empty.")

    msg = Message.objects.create(
        conversation=conversation,
        sender=sender_user,
        text=cleaned_text
    )
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=["updated_at"])

    # Determine recipient
    is_candidate_sender = (sender_user.id == conversation.candidate.user_id)
    if is_candidate_sender:
        recipient = conversation.company.user
        sender_name = f"{conversation.candidate.first_name} {conversation.candidate.last_name}".strip()
        action_url = f"{reverse('company:inbox')}?chat_id={conversation.id}"
    else:
        recipient = conversation.candidate.user
        sender_name = conversation.company.company_name or "Hiring Manager"
        action_url = f"{reverse('candidate:inbox')}?chat_id={conversation.id}"

    # Fire notification
    snippet = cleaned_text[:120] + ("..." if len(cleaned_text) > 120 else "")
    notify_user(
        recipient=recipient,
        sender=sender_user,
        title=f"New message from {sender_name}",
        message=snippet,
        action_url=action_url,
        notification_type="new_message"
    )

    return msg
