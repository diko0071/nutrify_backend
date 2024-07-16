from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os 
from .models import Prompts, MealItem
from .prompts import meal_item_by_description_prompt, meal_item_by_picture_prompt, meal_item_identifiyer_prompt, meal_item_ingridients_prompt, missing_ingredient_prompt
from django.utils import timezone
import json
import base64
import httpx
from .models import Meal
from vector_store.services import VectorStoreActions

usda_api_key = os.getenv("USDA_API_KEY")

vector_action = VectorStoreActions()


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
        response = chat.invoke(message)
        
        return response.content


class MealItemHandler:
    def __init__(self, user):
        self.user = user


    def generate_meal_item_by_description(self, description, meal_id):
        generated_meal_item_data = openai_call(description, meal_item_by_description_prompt, self.user)

        try:
            generated_meal_item_data_json = json.loads(generated_meal_item_data)
        except json.JSONDecodeError as e:
            generated_meal_item_data = openai_call(f'{description}, issue: {e}. Re-generate in right format', meal_item_by_description_prompt, self.user)
            try:
                generated_meal_item_data_json = json.loads(generated_meal_item_data)
            except json.JSONDecodeError as e:
                return f'Error decoding JSON after retry: {e}'

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
            generated_meal_item_data = openai_call(f'issue: {e}. Re-generate in right format', meal_item_by_picture_prompt, self.user, image_url=image_url)
            try:
                generated_meal_item_data_json = json.loads(generated_meal_item_data)
            except json.JSONDecodeError as e:
                return f'Error decoding JSON after retry: {e}'

        meal_items = []
        for meal_item_data in generated_meal_item_data_json:
            meal_item = MealItem.objects.create(
                user=self.user,
                name=meal_item_data["name"],
                image=image,
                servings=meal_item_data["servings"],
                calories=meal_item_data["calories"],
                proteins=meal_item_data["proteins"],
                carbs=meal_item_data["carbs"],
                fats=meal_item_data["fats"],
                meal_id=meal_id
            )
            meal_items.append(meal_item)

        return meal_items
    

class AdvancedMealItemHandler:
    def __init__(self, user):
        self.user = user

    def indetify_meal(self, data, image = None):
        if image is None:
            response = openai_call(str(data), meal_item_identifiyer_prompt, self.user)
        else:
            response = openai_call('', meal_item_identifiyer_prompt, self.user, image_url=image)
            print(response)
        try:
            response_json = json.loads(response)
        
        except json.JSONDecodeError as e:
            return f'Error decoding JSON: {e}'

        return response_json

    def query_similar_meal_items(self, meal_name):
        ...

    def decompose_ingredients(self, meal_name, servings):
        response = openai_call(f'Meal name: {meal_name}, servings: {servings}', meal_item_ingridients_prompt, self.user)
        try:
            response_json = json.loads(response)
        except json.JSONDecodeError as e:
            return f'Error decoding JSON: {e}'

        return response_json
    
    def retrieve_and_convert_ingredients_meta(self, ingredient: str, desired_serving_size: float):
        import numpy as np
        import math

        ingredients_meta = {}
        default_serving_size = 100.0
        
        request_url = f'https://api.nal.usda.gov/fdc/v1/foods/search?query={ingredient}&pageSize=5&dataType=Foundation&api_key={usda_api_key}'
        response = httpx.get(request_url)
        data = response.json()

        all_foods = data.get('foods', [])
        
        if not all_foods:
            return {'missing': True, 'ingredient': ingredient, 'desired_serving_size': desired_serving_size}

        food_info = {
            'description': ingredient,
            'servingSizeUnit': 'g',
            'desiredServingSize': desired_serving_size,
            'foodCategory': 'Aggregated',
            'nutrients': [],
            'missing': False
        }

        nutrients_data = {}
        serving_sizes = []

        for food in all_foods:
            serving_sizes.append(food.get('servingSize', default_serving_size))
            for nutrient in food.get('foodNutrients', []):
                nutrient_name = nutrient['nutrientName']
                if 'value' in nutrient:
                    if nutrient_name not in nutrients_data:
                        nutrients_data[nutrient_name] = []
                    nutrients_data[nutrient_name].append(nutrient['value'])
                
        conversion_factor = desired_serving_size / default_serving_size

        for nutrient_name, values in nutrients_data.items():
            if nutrient_name in [
                'Energy (Atwater General Factors)', 
                'Energy (Atwater Specific Factors)', 
                'Protein', 
                'Carbohydrate, by difference', 
                'Total lipid (fat)'
            ]:
                if values: 
                    values = np.array(values)  
                    mean_value = np.mean(values)  
                    converted_value = mean_value * conversion_factor  
                else:
                    return {'missing': True, 'ingredient': ingredient, 'desired_serving_size': desired_serving_size}

                if not math.isnan(converted_value) and not math.isinf(converted_value):  
                    food_info['nutrients'].append({
                        'nutrientName': nutrient_name,
                        'unitName': 'g',
                        'originalValue': round(mean_value, 2),
                        'desiredValue': round(converted_value, 2)
                    })

        ingredients_meta[ingredient] = food_info

        return ingredients_meta
    
    def calculate_calories_by_meal_name(self, data, input_type):
        if input_type == 'image':
            idetified_meal = self.indetify_meal(data = '', image = data)
        else:
            idetified_meal = self.indetify_meal(data)
        
        meal_name = idetified_meal['meal_name']
        serving_size = idetified_meal['serving_size']
        ingredients = self.decompose_ingredients(meal_name, serving_size)['ingredients']

        total_nutrients = {}
        ingredients_list = []

        for ingredient in ingredients:
            ingredient_name = ingredient['ingredient']
            desired_serving_size = ingredient['servingSize']
            ingredient_meta = self.retrieve_and_convert_ingredients_meta(ingredient_name, desired_serving_size)
            
            if 'missing' in ingredient_meta and ingredient_meta['missing']:
                missing_ingredient_data = openai_call(f'Ingredient: {ingredient_name}, serving size: {desired_serving_size}', missing_ingredient_prompt, self.user)
                try:
                    missing_ingredient_data_json = json.loads(missing_ingredient_data)
                except json.JSONDecodeError as e:
                    return f'Error decoding JSON: {e}'
                
                ingredient_meta = {ingredient_name: missing_ingredient_data_json}
                ingredient_meta[ingredient_name]['missing'] = True

            for meta in ingredient_meta.values():
                ingredients_list.append({
                    'ingredient': ingredient_name,
                    'description': meta['description'],
                    'servingSizeUnit': meta['servingSizeUnit'],
                    'desiredServingSize': meta['desiredServingSize'],
                    'foodCategory': meta['foodCategory'],
                    'nutrients': meta['nutrients'],
                    'missing': meta.get('missing', False)
                })

                for nutrient in meta['nutrients']:
                    nutrient_name = nutrient['nutrientName']
                    desired_value = nutrient['desiredValue']

                    if nutrient_name not in total_nutrients:
                        total_nutrients[nutrient_name] = 0

                    total_nutrients[nutrient_name] += desired_value

        meal_summary = {
            'meal_name': meal_name,
            'servingSize': serving_size,
            'ingredients': ingredients,
            'total_nutrients': total_nutrients,
            'ingredients_details': ingredients_list
        }

        return meal_summary