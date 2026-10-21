import random
import json
import asyncio
from datetime import datetime

from Pure.multiAgent_version.Agent_with_history import Agent, check_ollama_model, quit_ollama
from Pure.questions.question_bank import get_chosen_question
from new_prompt import *

EVALUATION_RUNS = 2
CALCULATION_RUNS = 3
MAX_REFLEXION_LOOPS = 3
#different models will produce errors because my hardware is too weak
MODEL_OLD = "qwen2.5:7b"
MODEL_HEAVY = "qwen2.5:7b"
MODEL_REGULAR = "qwen2.5:7b"
MODEL_REGULAR_LIGHT = "qwen2.5:7b"
MODEL_LIGHT_ANALYTICAL = "qwen2.5:7b"
MODEL_LIGHT_KNOWLEDGE = "qwen2.5:7b"
'''
MODEL_OLD = "llama3.1:8b"
MODEL_HEAVY = "deepseek-r1:14b"
MODEL_REGULAR = "qwen2.5:7b"
MODEL_REGULAR_LIGHT = "qwen2.5:3b"
MODEL_LIGHT_ANALYTICAL = "phi4-mini"
MODEL_LIGHT_KNOWLEDGE = "gemma2:2b"
'''
CALCULATOR_MODELS = [MODEL_REGULAR, MODEL_LIGHT_ANALYTICAL, MODEL_REGULAR_LIGHT]
EVALUATOR_MODELS = [MODEL_REGULAR, MODEL_REGULAR_LIGHT]
USED_MODELS = set(CALCULATOR_MODELS + EVALUATOR_MODELS)

CONSOLE_LOGS = True
QUESTION_BANK = True


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


async def handle_calculations(evaluators: list, user_input: str, research: str, max_tokens: int):
    start_input = f"QUESTION: {user_input}\n\nRESEARCH: {research}"

    workers = []
    for i in range(CALCULATION_RUNS):
        role = ROLES_CALCULATOR[i % len(ROLES_CALCULATOR)]
        model = CALCULATOR_MODELS[i % len(CALCULATOR_MODELS)]
        workers.append(Agent(model=model, role=role))

    if CONSOLE_LOGS:
        print("STARTING INITIAL CALCULATIONS:")

    tasks = [run_worker_initial(worker, start_input, max_tokens) for worker in workers]
    current_results = await asyncio.gather(*tasks)

    loop_count = 0
    while loop_count < MAX_REFLEXION_LOOPS:
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