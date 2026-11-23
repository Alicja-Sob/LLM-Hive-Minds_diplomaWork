import json
import asyncio
from datetime import datetime
from pathlib import Path

from Pure.multiAgent_version.Agent_with_history import Agent, check_ollama_model, quit_ollama
from prompts import *
from solve_question import handle_research, handle_calculations, MODEL
from Pure.questions.question_bank import load_questions
from metric_collection import metrics_logger

def verify_answer(generated_answer, question_data):
    if not generated_answer or generated_answer == "#not_good":
        return False

    gen_ans = str(generated_answer).strip().lower()

    correct_ans = str(question_data.get("correct_answer", "")).strip().lower()
    if gen_ans == correct_ans:
        return True

    acceptable_answers = question_data.get("acceptable_answers", [])
    for ans in acceptable_answers:
        if gen_ans == str(ans).strip().lower():
            return True

    return False

async def process_question_bank(input_file: str, output_file: str, metrics_file: str):

    check_ollama_model(MODEL)
    metrics_data = []
    stop_metrics_event = asyncio.Event()
    logger_task = asyncio.create_task(metrics_logger(1.0, metrics_data, stop_metrics_event))

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_file).parent.mkdir(parents=True, exist_ok=True)

    try:
        agent_researcher = Agent(model=MODEL, role=ROLE_RESEARCHER)
        agent_evaluator = Agent(model=MODEL, role=ROLE_EVALUATOR)
        evaluators = [agent_evaluator, agent_evaluator]

        questions = load_questions(input_file)

        if not questions:
            print("No questions found")
            return

        results_data = []

        for idx, q in enumerate(questions):
            question_text = q.get('question')


            print(f"Calculating question:  {idx + 1}/{len(questions)} ---")

            try:
                research = await handle_research(agent=agent_researcher, user_input=question_text, temperature=0.15,
                                                 max_tokens=2000)
                answer = await handle_calculations( user_input=question_text,
                                                   research=research, max_tokens=3000,version=1,evaluators=evaluators,)

                is_correct = verify_answer(answer, q)

                results_data.append({
                    "id": idx + 1,
                    "question": question_text,
                    "generated_answer": answer,
                    "is_correct": is_correct,
                    "expected_answers": q.get("acceptable_answers", []), # acceptable answers contain correct answer in them
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                results_data.append({
                    "id": idx + 1,
                    "question": question_text,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

            with open(output_file, 'w', encoding='utf-8') as out_f:
                json.dump(results_data, out_f, indent=4, ensure_ascii=False)
    finally:
        stop_metrics_event.set()
        await logger_task

        with open(metrics_file, 'w', encoding='utf-8') as met_f:
            json.dump(metrics_data, met_f, indent=4, ensure_ascii=False)

        quit_ollama(MODEL)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent

    input_bank = BASE_DIR.parent / "questions" / "Mathematics" / "AQUARAT_abridged.json"

    output_results = BASE_DIR / "Results" / "solved_results_AQUARAT_multiagent.json"
    output_metrics = BASE_DIR / "Results" / "system_metrics_AQUARAT_multiagent.json"

    asyncio.run(process_question_bank(str(input_bank),str(output_results),str(output_metrics)))