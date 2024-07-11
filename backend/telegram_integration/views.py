from django.shortcuts import render
import requests
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import os
import json
from useraccount.models import User
from meal.views import create_meal_item

def setwebhook(request):
  response = requests.post(os.environ.get("TELEGRAM_BOT_API_URL") + "setWebhook?url=" + os.environ.get("TELEGRAM_APP_API_URL")).json()
  return HttpResponse(f"{response}")

def send_message(method, data):
  return requests.post(os.environ.get("TELEGRAM_BOT_API_URL") + method, data)

def delete_webhook(request):
    response = requests.get(os.environ.get("TELEGRAM_BOT_API_URL") + "deleteWebhook").json()
    return HttpResponse(f"{response}")

def handle_update(update, request):
    chat_id = update['message']['chat']['id']
    text = update['message']['text']

    try:
        user = User.objects.get(telegram_user_id=chat_id)
    except User.DoesNotExist:
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': 'You are not registered. Please sign up on our platform: https://walletwave.app'
        })
        return HttpResponse('User not registered')

    request.user = user

    return HttpResponse('ok')

@csrf_exempt
def telegram_bot(request):
  if request.method == 'POST':
    update = json.loads(request.body.decode('utf-8'))
    handle_update(update, request)
    return HttpResponse('ok')
  else:
    return HttpResponseBadRequest('Bad Request')
