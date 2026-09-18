from django.urls import path
from . import views

app_name = "communications"

urlpatterns = [
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("notifications/api/unread/", views.unread_notifications_json, name="unread_notifications_api"),
    path("conversations/<int:conversation_id>/send/", views.conversation_send_message_api, name="send_message_api"),
    path("conversations/from-applicant/<int:app_id>/", views.start_conversation_from_applicant, name="start_from_applicant"),
]
