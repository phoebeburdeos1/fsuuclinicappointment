from django.urls import path

from .views import (
    home_view,
    landing_page,
    login_view,
    logout_view,
    messages_page,
    notification_payload,
    register_view,
    send_message,
    user_profile_detail,
)

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('home/', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('messages/', messages_page, name='messages_page'),
    path('messages/send/', send_message, name='send_message'),
    path('messages/notifications/', notification_payload, name='notification_payload'),
    path('profile/view/<int:user_id>/', user_profile_detail, name='user_profile'),
    path('admin/patient/<int:user_id>/', user_profile_detail, name='admin_patient_profile'),
]
