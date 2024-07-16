from django.test import TestCase
import pandas as pd
import os
from ..useraccount.models import User
from .services import AdvancedMealItemHandler, openai_call

user = User.objects.get(email=os.environ.get("USER_FOR_TEST"))

def generate_mealitem_meta(question):
    model = AdvancedMealItemHandler(user)
    recipe = model.calculate_calories_by_meal_name(question, 'description')

    result = {
        "meal_name": recipe["meal_name"],
        "serving_size": recipe["servingSize"],
        "energy": recipe["total_nutrients"]["Energy"],
        "energy_atwater_general": recipe["total_nutrients"]["Energy (Atwater General Factors)"],
        "energy_atwater_specific": recipe["total_nutrients"]["Energy (Atwater Specific Factors)"],
        "protein": recipe["total_nutrients"]["Protein"],
        "carbs": recipe["total_nutrients"]["Carbohydrate, by difference"],
        "fats": recipe["total_nutrients"]["Total lipid (fat)"]
    }

    return result
 
def evalutate_answer(answer, expected_answer):
    system_message = """You MUST evaluate the answer and compare the calories, proteins, fats. 

    You will recive answer and expected answere. You MUST compare how far prediction were. It is small difference you MUST count it as right. 

    You MUST output ONLY 1 or 0 wihtout ANY additional charaters. 
    """
    human_message = f"Answer: {answer}\nExpected answer: {expected_answer}"

    result = openai_call(human_message=human_message, system_message=system_message, user=user)

    return result


def run_test():
    file_path = '/Users/dmitrykorzhov/Desktop/Root/projects/nutrify/dataset/nutrify_validation_dataset.xlsx'  
    data = pd.read_excel(file_path)  
    results = []

    for index, row in data.iterrows():
        question = f"Meal name: {row['meal_name']}, Serving size: {row['serving_size']}"
        
        answer = generate_mealitem_meta(question)
        answer = f"Meal name: {answer['meal_name']}, Serving size: {answer['serving_size']}, Calories: {answer['energy']}, Proteins: {answer['protein']}, Carbs: {answer['carbs']}, Fats: {answer['fats']}"
        
        expected_answer = f"Calories: {row['calories']}, Proteins: {row['proteins']}, Carbs: {row['carbs']}, Fats: {row['fats']}"
        
        evaluation_result = evalutate_answer(answer, expected_answer)
        
        results.append({
            'question': question,
            'answer': answer,
            'expected_answer': expected_answer,
            'evaluation_result': evaluation_result
        })
        
        print(f"Row {index} evaluation result: {evaluation_result}")

    results_df = pd.DataFrame(results)
    results_df.to_csv('test_results.csv', index=False)

if __name__ == "__main__":
    run_test()