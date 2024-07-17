from langchain_openai import ChatOpenAI, OpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os 
from .models import Prompts, MealItem
from .prompts import meal_item_by_description_prompt, meal_item_by_picture_prompt, meal_item_identifiyer_prompt, meal_item_ingridients_prompt, missing_ingredient_prompt, usda_chooser_prompt
from django.utils import timezone
import json
import base64
import httpx
from .models import Meal
from vector_store.services import VectorStoreActions
from langchain_community.callbacks import get_openai_callback

usda_api_key = os.getenv("USDA_API_KEY")

vector_action = VectorStoreActions()


def openai_call(human_message, system_message, user, image_url=None):
    from langchain_community.callbacks import get_openai_callback

    llm = ChatOpenAI(model_name="gpt-4o-2024-05-13", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    chat = llm

    with get_openai_callback() as cb:
        if image_url is None:
            messages = [
                SystemMessage(content=f'{system_message}.'),
                HumanMessage(content=human_message),
            ]
            response = chat.invoke(messages)
        else:
            image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
            message = HumanMessage(
                content=[
                    {"type": "text", "text": system_message},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                ],
            )
            response = chat.invoke([message])

        Prompts.objects.create(
            user=user,
            system_message=system_message,
            user_message=human_message,
            response=response.content,
            cost=cb.total_cost,
            input_tokens=cb.prompt_tokens,
            output_tokens=cb.completion_tokens
        )

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

    def indetify_meal_by_description(self, data):
        response = openai_call(str(data), meal_item_identifiyer_prompt, self.user)
        try:
            response_json = json.loads(response)
        
        except json.JSONDecodeError as e:
            return f'Error decoding JSON: {e}'

        return response_json
    
    def indetify_meal_by_image(self, image):
        response = openai_call('', meal_item_identifiyer_prompt, self.user, image_url=image)
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

    def handle_usda_response(self, usda_response, ingredient):
        nutrient_names = [
            'Energy (Atwater General Factors)', 
            'Energy (Atwater Specific Factors)', 
            'Protein', 
            'Carbohydrate, by difference', 
            'Total lipid (fat)'
        ]
        
        ingredients_info = [
            {
                'description': food['description'],
                'nutrients': [
                    {
                        'nutrientName': nutrient['nutrientName'],
                        'value': nutrient['value']
                    }
                    for nutrient in food.get('foodNutrients', [])
                    if nutrient['nutrientName'] in nutrient_names
                ]
            }
            for food in usda_response.get('foods', [])
        ]
        
        chooser_response = openai_call(
            f'Initial ingredient: {ingredient}, ingredients to choose from: {json.dumps(ingredients_info)}', 
            usda_chooser_prompt, 
            self.user
        )

        try:
            chooser_response_json = json.loads(chooser_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON from usda_ingridient_chooser: {e}")
        
        if not isinstance(chooser_response_json, list):
            chooser_response_json = [chooser_response_json]
        
        chosen_descriptions = {ingredient['description'] for ingredient in chooser_response_json}
        
        filtered_ingredients = [
            food for food in usda_response.get('foods', [])
            if food['description'] in chosen_descriptions
        ]

        return filtered_ingredients
    
    def retrieve_and_convert_ingredients_meta(self, ingredient: str, desired_serving_size: float):
        import numpy as np
        import math

        ingredients_meta = {}
        default_serving_size = 100.0
        
        request_url = f'https://api.nal.usda.gov/fdc/v1/foods/search?query={ingredient}&pageSize=5&dataType=Foundation&api_key={usda_api_key}'
        response = httpx.get(request_url)
        data = response.json()

        filtered_ingredients = self.handle_usda_response(data, ingredient)
        
        if not filtered_ingredients:
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

        for food in filtered_ingredients:
            serving_sizes.append(food.get('servingSize', default_serving_size))
            for nutrient in food.get('foodNutrients', []):
                nutrient_name = nutrient['nutrientName']
                if 'value' in nutrient:
                    if nutrient_name not in nutrients_data:
                        nutrients_data[nutrient_name] = []
                    nutrients_data[nutrient_name].append(nutrient['value'])
                
        conversion_factor = desired_serving_size / default_serving_size

        required_nutrients = [
            'Energy (Atwater General Factors)', 
            'Energy (Atwater Specific Factors)', 
            'Protein', 
            'Carbohydrate, by difference', 
            'Total lipid (fat)'
        ]

        for nutrient_name, values in nutrients_data.items():
            if nutrient_name in required_nutrients:
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

        for required_nutrient in required_nutrients:
            if not any(nutrient['nutrientName'] == required_nutrient for nutrient in food_info['nutrients']):
                return {'missing': True, 'ingredient': ingredient, 'desired_serving_size': desired_serving_size}

        ingredients_meta[ingredient] = food_info

        return ingredients_meta
    
    def calculate_calories_by_meal_name(self, data, input_type, meal_id, image=None, environment=None):
        if input_type == 'image':
            identified_meals = self.indetify_meal_by_image(data)
        else:
            identified_meals = self.indetify_meal_by_description(data)
        
        meal_summaries = []
        meal_items = []

        for meal in identified_meals:
            meal_name = meal['meal_name']
            serving_size = meal['serving_size']
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

            meal_summaries.append(meal_summary)
            if input_type == 'image':
                meal_item = MealItem.objects.create(
                    user=self.user,
                    name=meal_name,
                    image=image,
                    servings=meal_summary["servingSize"],
                    calories=meal_summary["total_nutrients"]["Energy (Atwater General Factors)"],
                    proteins=meal_summary["total_nutrients"]["Protein"],
                    carbs=meal_summary["total_nutrients"]["Carbohydrate, by difference"],
                    fats=meal_summary["total_nutrients"]["Total lipid (fat)"],
                    meal_id=meal_id
                )
                meal_items.append(meal_item)
            else:
                meal_item = MealItem.objects.create(
                    user=self.user,
                    name=meal_name,
                    description=data,
                    servings=meal_summary["servingSize"],
                    calories=meal_summary["total_nutrients"]["Energy (Atwater General Factors)"],
                    proteins=meal_summary["total_nutrients"]["Protein"],
                    carbs=meal_summary["total_nutrients"]["Carbohydrate, by difference"],
                    fats=meal_summary["total_nutrients"]["Total lipid (fat)"],
                    meal_id=meal_id
                )
                meal_items.append(meal_item)
        if environment == 'production':
            print(meal_summaries)
            return meal_items
        else:
            return meal_summary
        