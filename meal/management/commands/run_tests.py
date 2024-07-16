from django.core.management.base import BaseCommand
import pandas as pd
import os
from useraccount.models import User
from meal.services import AdvancedMealItemHandler, openai_call
import uuid
import csv


class Command(BaseCommand):
    help = 'Run meal tests'

    def handle(self, *args, **kwargs):
        user = User.objects.get(email=os.environ.get("USER_FOR_TEST"))

        def generate_mealitem_meta(question):
            model = AdvancedMealItemHandler(user)
            recipe = model.calculate_calories_by_meal_name(question, 'description')

            result = {
                "meal_name": recipe.get("meal_name", ""),
                "serving_size": recipe.get("servingSize", ""),
                "energy_atwater_general": recipe["total_nutrients"].get("Energy (Atwater General Factors)", ""),
                "energy_atwater_specific": recipe["total_nutrients"].get("Energy (Atwater Specific Factors)", ""),
                "protein": recipe["total_nutrients"].get("Protein", ""),
                "carbs": recipe["total_nutrients"].get("Carbohydrate, by difference", ""),
                "fats": recipe["total_nutrients"].get("Total lipid (fat)", "")
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
            file_path = os.path.join(os.path.dirname(__file__), '../../../dataset/nutrify_validation_dataset.xlsx') 
            data = pd.read_excel(file_path)  
            results_file_path = os.path.join(os.path.dirname(file_path), 'test_results.csv')

            test_run_id = str(uuid.uuid4())

            file_exists = os.path.isfile(results_file_path)

            fieldnames = [
                'test_run_id', 'question', 
                'serving_size_generated', 'serving_size_expected',
                'calories_generated_agf', 'calories_generated_asf', 'calories_expected', 
                'proteins_generated', 'proteins_expected', 
                'carbs_generated', 'carbs_expected', 
                'fats_generated', 'fats_expected', 
                'answer_generated', 'answer_expected',
                'evaluation_result'
            ]

            if not file_exists:
                with open(results_file_path, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

            for index, row in data.iterrows():
                question = f"Meal name: {row['meal_name']}, Serving size: {row['serving_size']}"
                
                answer = generate_mealitem_meta(question)
                answer_str = f"Meal name: {answer['meal_name']}, Serving size: {answer['serving_size']}, Calories: {answer['energy_atwater_specific']}, Proteins: {answer['protein']}, Carbs: {answer['carbs']}, Fats: {answer['fats']}"
                
                expected_answer = f"Calories: {row['calories']}, Proteins: {row['proteins']}, Carbs: {row['carbs']}, Fats: {row['fats']}"
                
                evaluation_result = evalutate_answer(answer_str, expected_answer)
                
                result = {
                    'test_run_id': test_run_id,
                    'question': question,
                    'serving_size_generated': answer['serving_size'],
                    'serving_size_expected': row['serving_size'],
                    'calories_generated_agf': answer['energy_atwater_general'],
                    'calories_generated_asf': answer['energy_atwater_specific'],
                    'calories_expected': row['calories'],
                    'proteins_generated': answer['protein'],
                    'proteins_expected': row['proteins'],
                    'carbs_generated': answer['carbs'],
                    'carbs_expected': row['carbs'],
                    'fats_generated': answer['fats'],
                    'fats_expected': row['fats'],
                    'answer_generated': answer_str,
                    'answer_expected': expected_answer,
                    'evaluation_result': evaluation_result
                }
                
                print(f"Row {index} evaluation result: {evaluation_result}")

                with open(results_file_path, 'a', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerow(result)
        run_test()