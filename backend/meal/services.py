from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os 
from .models import Prompts, MealItem
from .prompts import meal_item_by_description_prompt, meal_item_by_picture_prompt, meal_item_manual_prompt
from django.utils import timezone
import json


def openai_call(human_message, system_message, user):
    llm = ChatOpenAI(model_name="gpt-4o-2024-05-13", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    chat = llm
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


class MealItemHandler:
    def __init__(self, user):
        self.user = user

    def generate_meal_item_by_description(self, description):

        generated_meal_item_data = openai_call(description, meal_item_by_description_prompt, self.user)

        generated_meal_item_data_json = json.loads(generated_meal_item_data)
        
        meal_item = MealItem.objects.create(
            user=self.user,
            name = generated_meal_item_data_json["name"],
            description = description,
            serving = generated_meal_item_data_json["serving"],
            calories = generated_meal_item_data_json["calories"],
            protein = generated_meal_item_data_json["protein"],
            carbs = generated_meal_item_data_json["carbs"],
            fat = generated_meal_item_data_json["fat"],
        )

        return f"{meal_item.name} has been created"


    def generate_meal_item_by_picture(self, picture):

        generated_meal_item_data = openai_call(picture, meal_item_by_picture_prompt, self.user)

        generated_meal_item_data_json = json.loads(generated_meal_item_data)

        meal_item = MealItem.objects.create(
            user=self.user,
            name = generated_meal_item_data_json["name"],
            description = generated_meal_item_data_json["description"],
            image = picture,
            serving = generated_meal_item_data_json["serving"],
            calories = generated_meal_item_data_json["calories"],
            protein = generated_meal_item_data_json["protein"],
            carbs = generated_meal_item_data_json["carbs"],
            fat = generated_meal_item_data_json["fat"],
        )

        return f"{meal_item.name} has been created"
    
    def add_meal_item_manual(self, name, serving):
        human_message = f"Meal name: {name} \n Serving size: {serving}"
        
        generated_meal_item_data = openai_call(human_message, meal_item_manual_prompt, self.user)

        generated_meal_item_data_json = json.loads(generated_meal_item_data)

        meal_item = MealItem.objects.create(
            user=self.user,
            name=name,
            description=generated_meal_item_data_json["description"],
            serving=serving,
            calories=generated_meal_item_data_json["calories"],
            protein=generated_meal_item_data_json["protein"],
            carbs=generated_meal_item_data_json["carbs"],
            fat=generated_meal_item_data_json["fat"],
        )

        return f"{meal_item.name} has been created"