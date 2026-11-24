import random
import json
import asyncio
from datetime import datetime

from Pure.multiAgent_version.Agent import Agent, check_ollama_model, quit_ollama
from Pure.questions.question_bank import get_chosen_question
from prompt import *


from pathlib import Path
from Pure.questions.question_bank import load_questions
from Pure.multiAgent_version.metric_collection import metrics_logger

#
# technically the thesis description at mojaPG says 'single model'
# literally everything else is about agents and not just models though
# hence a single agent version and not a single model version

EVALUATION_RUNS=2

AGENT_MODEL = "llama3.1:8b"

CONSOLE_LOGS = True
QUESTION_BANK = True

async def run_agent(agent: Agent, input: str, temperature: float = None, max_tokens: int = None):
    """Build a proper prompt for given agent and runs a chat with it"""
    prompt = agent.build_chat_prompt(input)

    if temperature is not None and max_tokens is not None:
        return await agent.ollama_chat(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
    elif temperature is not None:
        return await agent.ollama_chat(prompt=prompt, temperature=temperature)
    elif max_tokens is not None:
        return await agent.ollama_chat(prompt=prompt, max_tokens=max_tokens)
    else:
        return await agent.ollama_chat(prompt=prompt)


async def run_worker(role: str, input: str, model: str, max_tokens: int):
    if CONSOLE_LOGS:
        start = datetime.now()
        print(f"[START] {role[9:27]}... at {start.strftime('%H:%M:%S')} for model: {model}")

    agent = Agent(model=model, role=role)
    result = await run_agent(agent=agent, input=input, temperature=0.05, max_tokens=max_tokens)

    if CONSOLE_LOGS:
        end = datetime.now()
        print(f"[END] {role[9:27]}... at {start.strftime('%H:%M:%S')} (duration {(end - start).total_seconds():.2f}s)")

    try:
        data = json.loads(result)
        if CONSOLE_LOGS:
            print(f"Worker thought:\n{data.get('thought')}\n")
        return data.get("final_answer")
    except json.decoder.JSONDecodeError:
        raise RuntimeError("Calculation agent failed to produce valid JSON")


async def handle_worker(start_input: str, max_tokens: int):
    tasks = []

    role = SA_ROLE_PROMT
    chosen_model = AGENT_MODEL
    tasks.append(run_worker(role=role, input=start_input, model=chosen_model, max_tokens=max_tokens))

    results = await asyncio.gather(*tasks)

    if CONSOLE_LOGS:
        for idx, result in enumerate(results):
            print(f"single calculation ({idx + 1}): {result}")

    return results


async def handle_calculations(user_input: str, max_tokens: int):
    """Runs calculations with varying temperature"""
    start_input = f"""
    QUESTION: {user_input}
    """
    if CONSOLE_LOGS:
        print("START CALCULATIONS")

    possible_result = await handle_worker(start_input=start_input, max_tokens=max_tokens)

    return possible_result[0]


async def main():
    check_ollama_model(AGENT_MODEL)

    try:
        print("system version: SINGLE AGENT")
        if QUESTION_BANK:
            question_input = get_chosen_question('Mathematics/MMLU_math_abridged.json')
            print(f"Chosen question: {question_input}\n")
        else:
            question_input = input("> ")

        result = await handle_calculations(user_input=question_input, max_tokens=3000)

        print("\nAGENT'S RESULT: ", result)

    finally:
        quit_ollama(AGENT_MODEL)
        if CONSOLE_LOGS:
            print("\nClosed model")



def verify_answer(generated_answer, question_data):
    if not generated_answer or generated_answer == "#not_good":
        return False

    gen_ans = str(generated_answer).strip().lower()

    correct_ans = str(question_data.get("correct_answer", "")).strip().lower()

    if gen_ans == correct_ans:
        return True

    acceptable_answers = question_data.get( "acceptable_answers", [])

    for ans in acceptable_answers:
        if gen_ans == str(ans).strip().lower():
            return True

    return False


async def process_question_bank(input_file: str,output_file: str,metrics_file: str):
    check_ollama_model(AGENT_MODEL)

    metrics_data = []
    stop_metrics_event = asyncio.Event()

    logger_task = asyncio.create_task(metrics_logger(1.0,metrics_data,stop_metrics_event))

    Path(output_file).parent.mkdir(parents=True,exist_ok=True)
    Path(metrics_file).parent.mkdir(parents=True,exist_ok=True)

    try:
        questions = load_questions(input_file)

        if not questions:
            print("No questions found")
            return

        results_data = []

        print(f"Loaded {len(questions)} questions")
        print("System version: SINGLE AGENT")

        for idx, q in enumerate(questions):

            question_text = q.get("question")

            print(f"Calculating question: {idx + 1}/{len(questions)}")

            try:
                answer = await handle_calculations(user_input=question_text,max_tokens=3000)

                is_correct = verify_answer(answer,q)

                results_data.append({
                    "id": idx + 1,
                    "question": question_text,
                    "generated_answer": answer,
                    "is_correct": is_correct,
                    "expected_answers": q.get("acceptable_answers", []),
                    "timestamp": datetime.now().isoformat()
                })

                print(f"Generated answer: {answer}")
                print(f"Correct: {is_correct}")

            except Exception as e:

                print(f"Error solving question: {e}")

                results_data.append({
                    "id": idx + 1,
                    "question": question_text,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

            with open(output_file,"w",encoding="utf-8") as out_f:
                json.dump( results_data,out_f,indent=4,ensure_ascii=False)

    finally:
        stop_metrics_event.set()
        await logger_task

        with open(metrics_file,"w",encoding="utf-8") as met_f:
            json.dump(metrics_data,met_f, indent=4,ensure_ascii=False)

        quit_ollama(AGENT_MODEL)


if __name__ == "__main__":

    BASE_DIR = Path(__file__).resolve().parent

    input_bank = (BASE_DIR.parent / "questions"  / "Mathematics"  / "AQUARAT_abridged.json")

    output_results = (BASE_DIR / "Results" / "solved_results_AQUARAT_single_agent.json")
    output_metrics = ( BASE_DIR / "Results"  / "system_metrics_AQUARAT_single_agent.json")

    asyncio.run(process_question_bank(input_file=str(input_bank),output_file=str(output_results),metrics_file=str(output_metrics)))
