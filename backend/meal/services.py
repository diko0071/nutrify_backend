from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os 
from .models import Prompts, MealItem
from .prompts import meal_item_by_description_prompt, meal_item_by_picture_prompt, meal_item_manual_prompt
from django.utils import timezone
import json
import base64
import httpx
from .models import Meal


def openai_call(human_message, system_message, user, image_url=None):
    
    llm = ChatOpenAI(model_name="gpt-4o-2024-05-13", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    chat = llm
    
    if image_url is None:
        messages = [
            SystemMessage(
        content=f'{system_message}.'
    ),
        HumanMessage(content=human_message),
            ]
        
        response = chat.invoke(messages)

        Prompts.objects.create(
            user=user,
            system_message=system_message,
            user_message=human_message,
            response=response.content
        )

        return response.content 
    
    else:
        image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
        message = HumanMessage(
            content=[
                {"type": "text", "text": system_message},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                },
            ],
        )
        response = chat.invoke([message])
        
        return response.content


class MealItemHandler:
    def __init__(self, user):
        self.user = user


    def generate_meal_item_by_description(self, description, meal_id):
        generated_meal_item_data = openai_call(description, meal_item_by_description_prompt, self.user)

        try:
            generated_meal_item_data_json = json.loads(generated_meal_item_data)
        except json.JSONDecodeError as e:
            return f'Error decoding JSON: {e}'

        meal_items = []
        for meal_item_data in generated_meal_item_data_json:
            meal_item = MealItem.objects.create(
                user=self.user,
                name=meal_item_data["name"],
                description=description,
                servings=meal_item_data["servings"],
                calories=meal_item_data["calories"],
                proteins=meal_item_data["proteins"],
                carbs=meal_item_data["carbs"],
                fats=meal_item_data["fats"],
                meal_id=meal_id
            )
            meal_items.append(meal_item)

        return meal_items

    def generate_meal_item_by_picture(self, image_url, image, meal_id):

        generated_meal_item_data = openai_call('', meal_item_by_picture_prompt, self.user, image_url=image_url)

        try:
            generated_meal_item_data_json = json.loads(generated_meal_item_data)
        except json.JSONDecodeError as e:
            return f'Error decoding JSON: {e}'

        meal_items = []
        for meal_item_data in generated_meal_item_data_json:
            meal_item = MealItem.objects.create(
                user=self.user,
                name = meal_item_data["name"],
                image = image,
                servings = meal_item_data["servings"],
                calories = meal_item_data["calories"],
                proteins = meal_item_data["proteins"],
                carbs = meal_item_data["carbs"],
                fats = meal_item_data["fats"],
                meal_id = meal_id
            )
            meal_items.append(meal_item)

        return meal_items