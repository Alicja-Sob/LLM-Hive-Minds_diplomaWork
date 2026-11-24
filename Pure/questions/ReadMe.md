# Questions, benchmarks and question banks
Folder `questions` and it's subfolders contains: 
* various question banks in JSON format
* example questions in `questions.txt` file
* code for handling the questions banks in `question_bank.py` file

## Question structure in question banks

```
{
    "category": "category of given question ex. 'MATH - Algebra' or 'own math',
    "difficulty level": "'no level' or 'level x' for questions from databanks which assign such",
    "question": "The question itself",
    "correct_answer": "The expected correct answer",
    "acceptable_answers": [
      "Answers that are also technically correct (ex. because of different formating"
    ]
}
```

## JSON question banks 
* `questions_ownMath` - 12 math questions prepared by the project team
* `MATH_abridged` - 175 math questions based on the [MATH](https://github.com/hendrycks/math/) dataset from each category and each level
  * Questions are rewritten in a more natural language without LaTeX notation wherever possible. 
  * Question bank contains only 175 out of the 12500 questions (5 for each level of each of the 7 categories)
  * Questions for the abridged question bank were chosen arbitrally
* `MMLU_math_abridged` - 80 questions based on mathematics sections of the [MMLU](https://huggingface.co/datasets/cais/mmlu) dataset
  * Questions are rewritten in a more natural language without LaTeX notation wherever possible. Answer and question sections are also put into one field
  * Question bank contains 20 questions for each level/category of mathematics question subsets (abstraact algebra, college mathematics, high school mathematics, elementary mathematics)
  * Questions for the abridged question bank were chosen arbitrally
* `MMLU_history_abridged` - 20 questions based on chosen history related sections of the [MMLU](https://huggingface.co/datasets/cais/mmlu) dataset
  * Questions are rewritten in a more natural language without LaTeX notation wherever possible. Answer and question sections are also put into one field
  * Question bank contains 5 questions for each category of the chosen question subsets (High School European History, High School US History, High School World History, Prehistory)
  * Questions for the abridged question bank were chosen arbitrally
* `MMLU_medicine_abridged`- 45 questions based on chosen medicine and health related sections of the [MMLU](https://huggingface.co/datasets/cais/mmlu) dataset
  * Questions are rewritten in a more natural language without LaTeX notation wherever possible. Answer and question sections are also put into one field
  * Question bank contains 5 questions for each category of the chosen question subsets (Professional Psychology, High School Psychology, Human Aging, Virology, Professional Medicine, Nutrition, Medical Genetics, Clinical Knowledge, College Medicine)
  * Questions for the abridged question bank were chosen arbitrally
* `MMLU_mOralityAndPhilosophy_abridged`- 20 questions based on chosen morality and philosphy related sections of the [MMLU](https://huggingface.co/datasets/cais/mmlu) dataset
  * Questions are rewritten in a more natural language without LaTeX notation wherever possible. Answer and question sections are also put into one field
  * Question bank contains 5 questions for each category of the chosen question subsets (Business Ethics, Moral Disputes, Moral Scenarios, Philosophy)
  * Questions for the abridged question bank were chosen arbitrally
* `MMLU_politicsAndLaw_abridged`- 30 questions based on chosen politics and law related sections of the [MMLU](https://huggingface.co/datasets/cais/mmlu) dataset
  * Questions are rewritten in a more natural language without LaTeX notation wherever possible. Answer and question sections are also put into one field
  * Question bank contains 5 questions for each category of the chosen question subsets (High School Government and Politics, International Law, Jurisprudence, Professional Law, US Foreign Policy)
  * Questions for the abridged question bank were chosen arbitrally
* `AQUARAT_abridged` - 50 math questions based on [Aqua_Rat](https://huggingface.co/datasets/deepmind/aqua_rat) dataset
  * Questions are rewritten in a more natural language without LaTeX notation wherever possible. They contain only the question and possible answers (reasoning is not evaluated)
  * Question bank contains only 50 out of nearly 100k questions
  * Questions for the abridged question bank were chosen arbitrally