import random
import json
import asyncio
from datetime import datetime
from SharedState import SharedState
from Pure.multiAgent_version.Agent_with_history import Agent, check_ollama_model, quit_ollama
from Pure.questions.question_bank import get_chosen_question
from prompts import *
from collections import Counter
EVALUATION_RUNS = 2
CALCULATION_RUNS = 3
MAX_LOOPS = 3
#different models will produce errors because my hardware is too weak
MODEL = "qwen2.5:7b"

'''
MODEL_OLD = "llama3.1:8b"
MODEL_HEAVY = "deepseek-r1:14b"
MODEL_REGULAR = "qwen2.5:7b"
MODEL_REGULAR_LIGHT = "qwen2.5:3b"
MODEL_LIGHT_ANALYTICAL = "phi4-mini"
MODEL_LIGHT_KNOWLEDGE = "gemma2:2b"
'''


CONSOLE_LOGS = True
QUESTION_BANK = True


async def run_worker_autonomous(worker_id: int, agent: Agent, start_input: str, shared_state: SharedState,
                                max_tokens: int):
    current_prompt = start_input
    have_final_answer = False

    for round_num in range(MAX_LOOPS):
        if not have_final_answer:
            agent.append_user_message(current_prompt)
            response = await agent.ollama_chat(temperature=0.1, max_tokens=max_tokens)
            agent.append_assistant_message(response)



            try:
                data = json.loads(response)
                my_answer = data.get("final_answer", "#error")
                my_thought = data.get("thought", "")
            except json.decoder.JSONDecodeError:
                my_answer = "#invalid_format"
                my_thought = "Research agent failed to produce valid JSON"


        board = await shared_state.publish_and_wait(round_num, worker_id, my_answer, my_thought)


        all_answers = [info["answer"] for info in board.values()]


        vote_counts = Counter(all_answers)
        majority_answer, majority_votes = vote_counts.most_common(1)[0]


        if majority_votes >= (CALCULATION_RUNS//2) +1 and my_answer == majority_answer and not have_final_answer:

            if CONSOLE_LOGS:
                print(f"[Worker {worker_id}] I agree with majority ({my_answer}). End of work.")
                #they now publish they old answer to shared state
                have_final_answer = True


        if majority_votes == CALCULATION_RUNS:
            return my_answer
        if round_num < MAX_LOOPS and not have_final_answer:
            if CONSOLE_LOGS:
                print(
                    f"[Worker {worker_id}]  {my_answer}, Majority: {majority_answer}. Recalculating answer.")


            other_thoughts = []
            for w_id, info in board.items():
                if w_id != worker_id:
                    other_thoughts.append(f"Worker {w_id} (Wynik: {info['answer']}): {info['thought']}")

            thoughts_text = "\n".join(other_thoughts)
            current_prompt = (
                f"Your answer ({my_answer}) is different from other agents. "
                f"The majority answer is: {majority_answer}.\n"
                f"Here is how they came up with their answers:\n{thoughts_text}\n\n"
                f"Please analyze your previous thought process step by step. Look for arithmetic or logical mistakes. Calculate again carefully. "
                f"If you found a mistake, provide the new result. If you are absolutely certain your previous result was correct, provide it again. Return ONLY a valid JSON with 'thought' and 'final_answer' keys. "
            )


    return my_answer
async def handle_research(agent: Agent, user_input, temperature: float, max_tokens: int):
    agent.clear_history()
    agent.append_user_message(user_input)
    raw_insight = await agent.ollama_chat(temperature=temperature, max_tokens=max_tokens)
    try:
        return json.dumps(json.loads(raw_insight), indent=2)
    except json.decoder.JSONDecodeError:
        raise RuntimeError("Research agent failed to produce valid JSON")


async def run_worker_initial(agent: Agent, start_input: str, max_tokens: int):
    agent.append_user_message(start_input)
    response = await agent.ollama_chat(temperature=0.05, max_tokens=max_tokens)
    agent.append_assistant_message(response)
    try:
        data = json.loads(response)
        if CONSOLE_LOGS:
            print(f"[WORKER INITIAL] thought:\n{data.get('thought')}\n")
        return data.get("final_answer")
    except json.decoder.JSONDecodeError:
        return "#invalid_format"


async def run_worker_reflexion(agent: Agent, previous_answer: str, max_tokens: int, evaluators_answers :list):
    feedback = f"The evaluator rejected the current pool of answers. Evaluators think between these answers {evaluators_answers}. Your previous answer was {previous_answer}. Please analyze your previous thought process step by step. Look for arithmetic or logical mistakes. Calculate again carefully. If you found a mistake, provide the new result. If you are absolutely certain your previous result was correct, provide it again. Return ONLY a valid JSON with 'thought' and 'final_answer' keys."
    agent.append_user_message(feedback)
    response = await agent.ollama_chat(temperature=0.1, max_tokens=max_tokens)
    agent.append_assistant_message(response)

    try:
        data = json.loads(response)
        if CONSOLE_LOGS:
            print(f"[WORKER REFLEXION] thought:\n{data.get('thought')}\n")
        return data.get("final_answer")
    except json.decoder.JSONDecodeError:
        return "#invalid_format"


async def handle_evaluation(agent: Agent, user_input: str, research: str, results: list, temperature: float,
                            max_tokens: int):
    agent.clear_history()
    new_input = f"QUESTION: {user_input}\n\nRESEARCH: {research}\n\nPOSSIBLE ANSWERS: {results}"
    agent.append_user_message(new_input)

    output = await agent.ollama_chat(temperature=temperature, max_tokens=max_tokens)

    try:
        data = json.loads(output)
        if CONSOLE_LOGS:
            print(f"[EVALUATOR] thought:\n{data.get('thought')}\n")
        return data.get("final_answer")
    except json.decoder.JSONDecodeError:
        return "#not_good"
    except KeyError:
        return "#not_good"


async def check_evaluators_consensus(evaluators, user_input, research, results, max_tokens):
    tasks = []
    for i in range(EVALUATION_RUNS):
        eval_agent = evaluators[i % len(evaluators)]
        tasks.append(
            handle_evaluation(eval_agent, user_input, research, results, random.uniform(0.03, 0.06), max_tokens))

    eval_outputs = await asyncio.gather(*tasks)

    final_answer = eval_outputs[0]
    for answer in eval_outputs:
        if CONSOLE_LOGS:
            print(f"[EVALUATOR VOTE] {answer}")
        if final_answer != answer:
            return eval_outputs
    return final_answer


async def handle_calculations( user_input: str, research: str, max_tokens: int,version :int,evaluators: list = None):
    start_input = f"QUESTION: {user_input}\n\nRESEARCH: {research}"
    if version == 1:
        print("No evaluators version")
        shared_state = SharedState(expected_workers=CALCULATION_RUNS)

        workers = []
        for i in range(CALCULATION_RUNS):
            role = ROLES_CALCULATOR[i % len(ROLES_CALCULATOR)]
            model = MODEL
            workers.append(Agent(model=model, role=role))
        tasks = [
            run_worker_autonomous(
                worker_id=i,
                agent=workers[i],
                start_input=start_input,
                shared_state=shared_state,
                max_tokens=max_tokens
            ) for i in range(CALCULATION_RUNS)
        ]


        final_results = await asyncio.gather(*tasks)
        vote_counts = Counter(final_results)
        majority_answer, majority_votes = vote_counts.most_common(1)[0]
        if majority_votes>=(CALCULATION_RUNS//2)+1:
            return majority_answer
        return "#not_good"
    else:
        print("Evaluators version")
        workers = []
        for i in range(CALCULATION_RUNS):
            role = ROLES_CALCULATOR[i % len(ROLES_CALCULATOR)]
            model = MODEL
            workers.append(Agent(model=model, role=role))

        if CONSOLE_LOGS:
            print("STARTING INITIAL CALCULATIONS:")

        tasks = [run_worker_initial(worker, start_input, max_tokens) for worker in workers]
        current_results = await asyncio.gather(*tasks)

        loop_count = 0
        while loop_count < MAX_LOOPS:
            if CONSOLE_LOGS:
                print(f"\nLOOP NO: {loop_count}:")
                print("CURRENT POSSIBLE ANSWERS:", current_results)

            consensus = await check_evaluators_consensus(evaluators, user_input, research, current_results, 1000)

            if not isinstance(consensus, list) :
                if CONSOLE_LOGS:
                    print(f"CONSENSUS REACHED: {consensus}")
                return consensus

            if CONSOLE_LOGS:
                print("ANSWERS NOT GOOD ENOUGH. INITIATING REFLEXION FOR ALL WORKERS...")

            tasks = [run_worker_reflexion(workers[i], current_results[i], max_tokens,consensus) for i in range(CALCULATION_RUNS)]
            current_results = await asyncio.gather(*tasks)
            loop_count += 1

        if CONSOLE_LOGS:
            print("MAX REFLEXION LOOPS REACHED. NO CONSENSUS.")
        return "#not_good"