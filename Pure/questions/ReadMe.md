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