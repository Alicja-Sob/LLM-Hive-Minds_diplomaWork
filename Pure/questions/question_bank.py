import json
import os
from itertools import groupby

# TODO: add ability to choose which question bank (s?) to use without changing it in the code

def load_questions(full_file_name):
    try:
        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, full_file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print("[ERROR] Specified question bank was not found.")
    except json.decoder.JSONDecodeError:
        raise RuntimeError("[ERROR] Failed to decode the json file")


def choose_question(question_bank):
    while True:
        try:
            user_input = int(input("\n> "))
            if 1 <= user_input <= len(question_bank):
                selected = question_bank[user_input - 1]
                return selected
            else:
                print("[ERROR] Chosen number is out of range")
        except ValueError:
            print("[ERROR] Chosen value is not a valid number")


def display_questions(question_bank):
    print("Choose a question by typing in the corresponding number:\n")

    number = 1

    for category, cat_group in groupby(question_bank, key=lambda q: q["category"]):
        print(category.upper())
        for level, lvl_group in groupby(cat_group, key=lambda q: q["difficulty level"]):
            print(f"\t{level.upper()}")

            # Print Questions indented twice with continuous numbering
            for question in lvl_group:
                print(f"\t\t{number} - {question['question']}")
                number += 1



def get_chosen_question(full_file_name):
    chosen_question = ""
    questions = load_questions(full_file_name)

    if questions:
        display_questions(questions)
        chosen_question = choose_question(questions)["question"]

    return chosen_question
