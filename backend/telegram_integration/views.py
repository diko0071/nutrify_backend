from django.shortcuts import render
import requests
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import json
from useraccount.models import User
from meal.models import Meal
from meal.views import MealItemSerializer
from meal.services import MealItemHandler
from dotenv import load_dotenv
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import datetime
from django.contrib.sessions.models import Session
from user_stat.models import WeightLog

load_dotenv()

telegram_bot_api_url = os.environ.get("TELEGRAM_BOT_API_URL")
telegram_app_api_url = os.environ.get("TELEGRAM_APP_API_URL")
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")


def log_weight_telegram(user, date, weight):
    date = datetime.now()
    date_only = date.strftime('%Y-%m-%d')
    weight_log = WeightLog.objects.create(user=user, timestamp=date, weight=weight)
    return f"Weight logged: {weight}kg on {date_only}"

def create_meal_item_telegram(user, date, meal_category, description=None, image=None):
    date = datetime.strptime(date, '%Y-%m-%d')
    model = MealItemHandler(user)

    try:
        meal = Meal.objects.filter(category=meal_category, user=user).latest('meal_date')
    except Meal.DoesNotExist:
        meal = Meal.objects.create(category=meal_category, user=user, meal_date=date)

    image_url = None

    try:
        if image and not description:
            if isinstance(image, str):
                try:
                    image_file_name = download_telegram_photo(image)
                    with open(image_file_name, 'rb') as image_file:
                        image = default_storage.save(image_file_name, ContentFile(image_file.read()))
                        image_url = default_storage.url(image)
                except Exception as e:
                    return {"error": f"Failed to download image from Telegram: {str(e)}"}
            else:
                image = default_storage.save(image.name, ContentFile(image.read()))
                image_url = default_storage.url(image)
    
            meal_item = model.generate_meal_item_by_picture(image_url, image, meal)
            serialized_meal_items = MealItemSerializer(meal_item, many=True)
            
            meal_details = []
            total_calories = 0
            for item in serialized_meal_items.data:
                meal_details.append(f"Meal: {item['name']}, {item['calories']} calories, {item['servings']}g")
                total_calories += item['calories']

            meal_details_str = "\n".join(meal_details)
            response_text = f"{meal_details_str}\n\nTotal: {total_calories} calories"
            return response_text
    
    except Exception as e:
        return {"error": str(e)}

    try:
        if description and not image_url:
            meal_item = model.generate_meal_item_by_description(description, meal)
            serialized_meal_items = MealItemSerializer(meal_item, many=True)
            meal_details = []
            total_calories = 0
            
            for item in serialized_meal_items.data:
                meal_details.append(f"Meal: {item['name']}, {item['calories']} calories, {item['servings']}g")
                total_calories += item['calories']

            meal_details_str = "\n".join(meal_details)
            response_text = f"{meal_details_str}\n\nTotal: {total_calories} calories"
            return response_text
        
    except Exception as e:
        return {"error": str(e)}

    return {"error": "Both picture and description cannot be provided or both are missing"}

def download_telegram_photo(file_id):
    file_info_url = f"{telegram_bot_api_url}getFile?file_id={file_id}"
    file_info_response = requests.get(file_info_url).json()

    if not file_info_response['ok']:
        raise Exception(f"Error retrieving file info: {file_info_response}")

    file_path = file_info_response['result']['file_path']
    file_url = f"https://api.telegram.org/file/bot{telegram_bot_token}/{file_path}"
    file_response = requests.get(file_url)

    if file_response.status_code != 200:
        raise Exception(f"Error downloading file: {file_response.content}")

    file_name = file_path.split('/')[-1]
    with open(file_name, 'wb') as file:
        file.write(file_response.content)

    return file_name

def set_bot_commands():
    commands = [
        {"command": "log", "description": "Log your weight"},
        {"command": "add", "description": "Add a meal"}
    ]
    response = requests.post(
        telegram_bot_api_url + "setMyCommands",
        json={"commands": commands}
    )
    if response.status_code != 200:
        print(f"Failed to set bot commands: {response.content}")
    return response.json()

def setwebhook(request):
    response = requests.post(telegram_bot_api_url + "setWebhook?url=" + telegram_app_api_url).json()
    set_bot_commands_response = set_bot_commands()
    return JsonResponse({
        "setWebhook_response": response,
        "setBotCommands_response": set_bot_commands_response
    })

def send_message(method, data):
  return requests.post(telegram_bot_api_url + method, data)

def delete_webhook(request):
    response = requests.get(telegram_bot_api_url + "deleteWebhook").json()
    return HttpResponse(f"{response}")

user_states = {}

def handle_update(update, request):
    date = update['message']['date']
    date = datetime.utcfromtimestamp(date).strftime('%Y-%m-%d')
    chat_id = update['message']['chat']['id']
    text = update['message'].get('text')

    user_state = user_states.get(chat_id, {}) 

    meal_category = user_states.get(chat_id, {}).get('meal_category')

    try:
        user = User.objects.get(telegram_user_id=chat_id)
    except User.DoesNotExist:
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': 'You are not registered.'
        })
        return HttpResponse('User not registered')

    request.user = user
    if text == '/start':
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': 'Welcome to Nutrify!'
        })

    elif text == '/log':
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': 'Please enter your weight in kg.'
        })
        user_states[chat_id] = {'awaiting_weight': True}

    elif user_states.get(chat_id, {}).get('awaiting_weight'):
        try:
            weight = float(text)
            log_message = log_weight_telegram(user, date, weight)
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': log_message,
            })
            user_states[chat_id].pop('awaiting_weight') 

        except ValueError:
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': 'Invalid weight. Please enter a valid number.'
            })

    elif text == '/add':
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': 'Choose your meal option:',
            'reply_markup': json.dumps({
                'keyboard': [[{'text': 'Breakfast'}, {'text': 'Lunch'}, {'text': 'Dinner'}, {'text': 'Snack'}]],
                'one_time_keyboard': True
            })
        })
        user_states[chat_id] = {'state': 'awaiting_meal_category'}

    elif user_state.get('state') == 'awaiting_meal_category' and text in ['Breakfast', 'Lunch', 'Dinner', 'Snack']:
        meal_category = text
        user_states[chat_id] = {'state': 'awaiting_meal_details', 'meal_category': meal_category}
        print(f"Set meal_category to {text} for chat_id {chat_id}")
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': f'Please provide a description or picture of your {text.lower()}.',
        })

    elif 'photo' in update['message']:
        if user_state.get('state') == 'awaiting_meal_details':
            meal_category = user_state.get('meal_category')
            print(f"Retrieved meal_category {meal_category} for chat_id {chat_id}")
            if meal_category:
                photo = update['message']['photo'][-1]['file_id']
                meal_item = create_meal_item_telegram(user, date, meal_category, image=photo)
                print(f"meal_item: {meal_item}")
                send_message("sendMessage", {
                    'chat_id': chat_id,
                    'text': meal_item,
                })
                user_states[chat_id] = {} 

    elif user_state.get('state') == 'awaiting_meal_details':
        description = text
        meal_category = user_state.get('meal_category')
        if meal_category:
            meal_item = create_meal_item_telegram(user, date, meal_category, description=description)
            print(f"meal_item: {meal_item}")
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': meal_item,
            })
            user_states[chat_id] = {}
        else:
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': 'Please select a meal category first.',
            })

@csrf_exempt
def telegram_bot(request):
  if request.method == 'POST':
    update = json.loads(request.body.decode('utf-8'))
    handle_update(update, request)
    return HttpResponse('ok')
  else:
    return HttpResponseBadRequest('Bad Request')

