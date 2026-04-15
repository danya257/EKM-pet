# chat/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.http import HttpResponseForbidden
from .models import Chat, Message
from clinics.models import Clinic

@login_required
def chat_list_view(request):
    """Список чатов текущего пользователя"""
    user = request.user
    if user.user_type == 'owner':
        chats = Chat.objects.filter(owner=user)
    else:  # vet or clinic_admin
        chats = Chat.objects.filter(vet=user)
    return render(request, 'chat/chat_list.html', {'chats': chats})


@login_required
def chat_detail_view(request, chat_id):
    """Страница чата"""
    chat = get_object_or_404(Chat, id=chat_id)
    user = request.user

    # Проверка доступа
    if not ((user == chat.owner) or (user == chat.vet)):
        return HttpResponseForbidden("Доступ запрещён")

    if request.method == 'POST':
        text = request.POST.get('text')
        if text.strip():
            Message.objects.create(chat=chat, sender=user, text=text)
        return redirect('chat:chat_detail', chat_id=chat_id)

    messages = chat.messages.all()
    # Помечаем как прочитанные (если получатель — не отправитель)
    if user == chat.vet:
        chat.messages.filter(sender=chat.owner, is_read=False).update(is_read=True)
    elif user == chat.owner:
        chat.messages.filter(sender=chat.vet, is_read=False).update(is_read=True)

    return render(request, 'chat/chat_detail.html', {
        'chat': chat,
        'messages': messages,
    })


@login_required
def start_chat_view(request, clinic_id, vet_id):
    """Создать чат с ветеринаром клиники"""
    if request.user.user_type != 'owner':
        return HttpResponseForbidden()
    
    clinic = get_object_or_404(Clinic, id=clinic_id)
    vet = get_object_or_404(clinic.admins, id=vet_id)  # только веты этой клиники

    # Проверим, есть ли уже чат
    chat, created = Chat.objects.get_or_create(
        owner=request.user,
        vet=vet,
        clinic=clinic
    )
    return redirect('chat:chat_detail', chat_id=chat.id)