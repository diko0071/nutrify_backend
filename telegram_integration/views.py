from django.shortcuts import render
import requests
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import json
from useraccount.models import User
from meal.models import Meal, MealItem
from meal.views import MealItemSerializer
from meal.services import MealItemHandler
from dotenv import load_dotenv
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import datetime
from django.contrib.sessions.models import Session
from user_stat.models import WeightLog, UserMetrics
load_dotenv()

telegram_bot_api_url = os.environ.get("TELEGRAM_BOT_API_URL")
telegram_app_api_url = os.environ.get("TELEGRAM_APP_API_URL")
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")


def today_meal_summary(user, date):
    try:
        meals = Meal.objects.filter(user=user, meal_date=date)
        meal_summary = {}
        total_today_calories = 0
    
        for meal in meals:
            meal_items = MealItem.objects.filter(meal_id=meal.id)
            category = meal.category
            if category not in meal_summary:
                meal_summary[category] = {
                    'items': [],
                    'total_calories': 0
                }

            for item in meal_items:
                meal_summary[category]['items'].append(f"Meal: {item.name}, {item.calories} calories, {item.servings}g")
                meal_summary[category]['total_calories'] += item.calories
                total_today_calories += item.calories

        summary_str = ""
        for category, details in meal_summary.items():
            summary_str += f"{category}\n"
            summary_str += "\n".join(details['items'])
            summary_str += f"\nTotal calories: {details['total_calories']}\n\n"

        daily_calorie_goal = UserMetrics.objects.get(user=user).daily_calorie_goal

        summary_str += f"\nTotal calories for today: {total_today_calories}\n\n"
        summary_str += f"\nDaily calories: {daily_calorie_goal}\n\n"
        summary_str += f"\nCalories remaining: {daily_calorie_goal - total_today_calories}\n\n"
        return summary_str
    except Exception as e:
        return f"An error occurred while generating the meal summary: {str(e)}"

def log_weight_telegram(user, date, weight):
    date = datetime.now()
    date_only = date.strftime('%Y-%m-%d')
    try:
        previous_weight = WeightLog.objects.filter(user=user).order_by('-timestamp').first()
        new_weight_log = WeightLog.objects.create(user=user, timestamp=date, weight=weight)
        if previous_weight:
            if new_weight_log.weight < previous_weight.weight:
                return f"Weight logged: {weight}kg on {date_only}\n\nYou have lost weight since the last log. Previous weight: {previous_weight.weight}kg"
            else:
                return f"Weight logged: {weight}kg on {date_only}\n\nYou have gained weight since the last log. Previous weight: {previous_weight.weight}kg"
        else:
            return f"Weight logged: {weight}kg on {date_only}\n\nNo previous weight data available."
    
    except Exception as e:
        print(f"Error in log_weight_telegram: {str(e)}")
        return f"An error occurred while logging the weight: {str(e)}"

def create_meal_item_telegram(user, date, meal_category, description=None, image=None):
    date = datetime.strptime(date, '%Y-%m-%d')
    
    model = MealItemHandler(user)

    try:
        meal = Meal.objects.filter(category=meal_category, user=user, meal_date=date).latest('meal_date')
    except Meal.DoesNotExist:
        meal = Meal.objects.create(category=meal_category, user=user, meal_date=date)

    image_url = None

    try:
        if image and not description:
            filename, file_content = download_telegram_photo(image)
            saved_path, image_url = save_file_to_storage(filename, file_content)

            meal_item = model.generate_meal_item_by_picture(image_url, saved_path, meal)
            serialized_meal_items = MealItemSerializer(meal_item, many=True)
            
            meal_details = []
            total_calories = 0
            for item in serialized_meal_items.data:
                meal_details.append(f"Meal: {item['name']}, {item['calories']} calories, {item['servings']}g")
                total_calories += item['calories']

            meal_details_str = "\n".join(meal_details)
            response_text = f"{meal_details_str}\n\nTotal: {total_calories} calories"
            calories_remaining = UserMetrics.objects.get(user=user).daily_calorie_goal - total_calories
            response_text += f"\n\nCalories remaining: {calories_remaining}"
            return response_text
    except Exception as e:
        return {"error": f"Error creating meal item: {str(e)}"}

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
            calories_remaining = UserMetrics.objects.get(user=user).daily_calorie_goal - total_calories
            response_text += f"\n\nCalories remaining: {calories_remaining}"
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
    print(f"Retrieved file path: {file_path}")

    if '..' in file_path or file_path.startswith('/'):
        raise Exception(f"Invalid file path detected: {file_path}")

    file_url = f"https://api.telegram.org/file/bot{telegram_bot_token}/{file_path}"
    file_response = requests.get(file_url)

    if file_response.status_code != 200:
        raise Exception(f"Error downloading file: {file_response.content}")

    filename = os.path.basename(file_path)

    if not filename or '..' in filename or filename.startswith('/'):
        raise Exception(f"Invalid file name detected: {filename}")

    return filename, file_response.content

def save_file_to_storage(filename, file_content):
    image_file = ContentFile(file_content)
    saved_path = default_storage.save(filename, image_file)
    image_url = default_storage.url(saved_path)

    return saved_path, image_url


def set_bot_commands():
    commands = [
        {"command": "log", "description": "Log your weight"},
        {"command": "add", "description": "Add a meal"},
        {"command": "meals", "description": "View today's meals"},
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

    elif text == '/meals':
        print(f"Handling /meals command for user: {user.id}")
        meal_summary = today_meal_summary(user, date)
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': meal_summary
        })
    elif text == '/log':
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': 'Please enter your weight in kg.'
        })
        user_states[chat_id] = {'awaiting_weight': True}

    elif user_states.get(chat_id, {}).get('awaiting_weight'):
        try:
            weight = float(text.replace(',', '.'))
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

