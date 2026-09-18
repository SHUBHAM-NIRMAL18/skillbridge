from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

from .models import Notification, Conversation, Message
from .services import notify_user, get_or_create_conversation, send_conversation_message
from applications.models import Application


@login_required
def notifications_list(request):
    """
    Renders user's notifications center with status filtering and pagination.
    """
    filter_tab = request.GET.get("filter", "all")
    qs = Notification.objects.filter(recipient=request.user)

    if filter_tab == "unread":
        qs = qs.filter(is_read=False)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    base_template = "company/base.html" if getattr(request.user, "role", "") == "company" else "candidate/base.html"

    return render(request, "communications/notifications.html", {
        "base_template": base_template,
        "page_obj": page_obj,
        "filter_tab": filter_tab,
        "unread_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
    })


@login_required
def mark_notification_read(request, pk):
    """
    Marks single notification as read and navigates to target action URL.
    """
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=["is_read"])

    if notif.action_url:
        return redirect(notif.action_url)
    return redirect("communications:notifications_list")


@login_required
@require_POST
def mark_all_notifications_read(request):
    """
    Marks all notifications for current user as read.
    """
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({"ok": True})
    return redirect("communications:notifications_list")


@login_required
@require_GET
def unread_notifications_json(request):
    """
    Lightweight API endpoint for navbar polling.
    """
    unread_qs = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
    items = []
    for n in unread_qs:
        items.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "action_url": n.action_url or reverse("communications:notifications_list"),
            "time": n.created_at.strftime("%b %d, %H:%M"),
            "type": n.notification_type,
        })
    return JsonResponse({
        "count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
        "notifications": items,
    })


@login_required
def start_conversation_from_applicant(request, app_id):
    """
    Allows recruiter to open or start a chat thread with an applicant directly from the drawer.
    """
    app = get_object_or_404(
        Application.objects.select_related("candidate__user", "company__user"),
        pk=app_id
    )

    # Authorization: must be the company owning the posting
    if not hasattr(request.user, "company_profile") or app.company.user_id != request.user.id:
        return HttpResponseForbidden("Only the hiring employer can initiate messaging from an application.")

    convo, _ = get_or_create_conversation(
        candidate=app.candidate,
        company=app.company,
        application=app,
        subject=f"Application Discussion: {app.target_title}"
    )

    return redirect(f"{reverse('company:inbox')}?chat_id={convo.id}")


@login_required
@require_POST
def conversation_send_message_api(request, conversation_id):
    """
    AJAX / Form endpoint to send a message within a conversation.
    """
    convo = get_object_or_404(
        Conversation.objects.select_related("candidate__user", "company__user"),
        pk=conversation_id
    )

    # Permission check: sender must be either candidate user or company user
    if request.user.id != convo.candidate.user_id and request.user.id != convo.company.user_id:
        return HttpResponseForbidden("You are not a participant in this conversation.")

    text = request.POST.get("text", "").strip()
    if not text:
        return HttpResponseBadRequest("Message content cannot be blank.")

    msg = send_conversation_message(convo, request.user, text)

    is_ajax = (request.headers.get("x-requested-with") == "XMLHttpRequest")
    if is_ajax:
        return JsonResponse({
            "ok": True,
            "message": {
                "id": msg.id,
                "text": msg.text,
                "sender_id": msg.sender_id,
                "is_you": True,
                "time": msg.created_at.strftime("%I:%M %p"),
                "date": msg.created_at.strftime("%b %d, %Y"),
            }
        })

    # Non-AJAX fallback: redirect back to corresponding inbox
    if request.user.id == convo.candidate.user_id:
        return redirect(f"{reverse('candidate:inbox')}?chat_id={convo.id}")
    else:
        return redirect(f"{reverse('company:inbox')}?chat_id={convo.id}")
