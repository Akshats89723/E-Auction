"""
Context processors for adding global template variables
"""
from .models import Notification

def unread_notification_count(request):
    """Add unread notification count to all templates"""
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
