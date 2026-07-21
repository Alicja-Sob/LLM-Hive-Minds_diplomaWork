import random
import json
import asyncio
from datetime import datetime

from Pure.Agent import Agent, check_ollama_model, quit_ollama
from questions.question_bank import get_chosen_question
from prompts import *

EVALUATION_RUNS=2
CALCULATION_RUNS = 3

MODEL_OLD = "llama3.1:8b"
MODEL_HEAVY = "deepseek-r1:14b"
MODEL_REGULAR = "qwen2.5:7b"
MODEL_REGULAR_LIGHT = "qwen2.5:3b"
MODEL_LIGHT_ANALYTICAL = "phi4-mini"
MODEL_LIGHT_KNOWLEDGE = "gemma2:2b"

# TODO: TEST THESE MODELS TO SEE WHICH WORK BEST FOR WHICH ROLE
# CALCULATOR_MODELS = [MODEL_LIGHT_KNOWLEDGE, MODEL_LIGHT_ANALYTICAL, MODEL_LIGHT_KNOWLEDGE]
CALCULATOR_MODELS = [MODEL_REGULAR, MODEL_LIGHT_ANALYTICAL, MODEL_REGULAR_LIGHT]
EVALUATOR_MODELS = [MODEL_REGULAR, MODEL_REGULAR_LIGHT]
USED_MODELS = set(CALCULATOR_MODELS + EVALUATOR_MODELS)

CONSOLE_LOGS = True
QUESTION_BANK = False

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


async def handle_research(agent: Agent, user_input, temperature: float, max_tokens: int):
    """Gathers insight from researcher and injects it into user's query"""
    raw_insight = await run_agent(agent=agent, input=user_input, temperature=temperature, max_tokens=max_tokens)

    try:
        return json.dumps(json.loads(raw_insight), indent=2)
    except json.decoder.JSONDecodeError:
        raise RuntimeError("Research agent failed to produce valid JSON")
    finally:
        quit_ollama(agent.model)


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


async def handle_worker(start_input: str, max_tokens: int, number_of_runs: int = 1):
    tasks = []
    for i in range(number_of_runs):
        idx = random.randint(0, len(ROLES_CALCULATOR) - 1)
        role = ROLES_CALCULATOR[idx]
        # if the models are the same for two calculators then we have a bottleneck and they're done sequentially anyway
        chosen_model = CALCULATOR_MODELS[i] if i < 3 else random.choice(CALCULATOR_MODELS)
        tasks.append(run_worker(role=role, input=start_input, model=chosen_model, max_tokens=max_tokens))

    results = await asyncio.gather(*tasks)
    #results = []  # it should be gather but this lessens the chances of a timeout for now and makes it actually possible to test
    #for t in tasks:
    #    results.append(await t)

    if CONSOLE_LOGS:
        for idx, result in enumerate(results):
            print(f"single calculation ({idx + 1}): {result}")

    #quit_ollama(model)
    return results


async def handle_calculations(evaluator: Agent, user_input: str, research: str, max_tokens: int):
    """Runs calculations with varying temperature"""
    possible_results = ""
    output_evaluation = ""
    start_input = f"""
    QUESTION: {user_input}

    RESEARCH: {research}
    """
    if CONSOLE_LOGS:
        print("START CALCULATIONS")

    results_list = await handle_worker(start_input=start_input, max_tokens=max_tokens, number_of_runs=CALCULATION_RUNS)
    possible_results = results_list

    count_runs = 0
    while count_runs < CALCULATION_RUNS * 3:
        if CONSOLE_LOGS:
            print("POSSIBLE ANSWERS: \n", "\n".join(f"- {r}" for r in possible_results))
        tasks = []
        for i in range(EVALUATION_RUNS):
            tasks.append(handle_evaluation(agent=Agent(model=EVALUATOR_MODELS[i%len(EVALUATOR_MODELS)], role=ROLE_EVALUATOR),
                                           user_input=user_input, research=research,
                                           results=possible_results, temperature=random.uniform(0.03, 0.06), max_tokens=1000))
        output_evaluation = await asyncio.gather(*tasks)
        output_evaluation = await handle_answer(output_evaluation)

        if CONSOLE_LOGS:
            print("evaluation: ", output_evaluation)

        if output_evaluation != "#not_good":
            break
        elif CONSOLE_LOGS:
            print(f"Answers not good enough")

        full_input = f"""{start_input}

        POSSIBLE ANSWERS: {results_list}"""
        new_results = await handle_worker(start_input=full_input, max_tokens=max_tokens, number_of_runs=1)

        possible_results += new_results
        count_runs += 1

    if count_runs >= CALCULATION_RUNS * 3:
        raise Exception("Could not find reliable answer")

    quit_ollama(evaluator.model)
    return output_evaluation


async def handle_answer(output_evaluation:str):
    final_answer = output_evaluation[0]
    i=1
    for answer in output_evaluation:
        if CONSOLE_LOGS:
            print(f"Answer from evaluator {i}: {answer}")
        if final_answer != answer:
            return "#not_good"
        i+=1
    return final_answer


async def handle_evaluation(agent: Agent, user_input, research: str, results: str, temperature: float, max_tokens: int):
    """Adds possible results to user's query and evaluates them"""
    new_input = f"""
    QUESTION: {user_input}

    RESEARCH: {research}

    POSSIBLE ANSWERS: {results}
    """

    output = await run_agent(agent=agent, input=new_input, temperature=temperature, max_tokens=max_tokens)

    try:
        return json.loads(output).get("final_answer")
    except json.decoder.JSONDecodeError:
        raise RuntimeError("Calculation agent failed to produce valid JSON")
    except KeyError:
        raise RuntimeError("Evaluation JSON missing 'final_answer' key")


async def main():
    for model in USED_MODELS:
        check_ollama_model(model)

    try:
        agent_researcher = Agent(model=MODEL_LIGHT_ANALYTICAL, role=ROLE_RESEARCHER)
        agent_evaluator = Agent(model=MODEL_REGULAR, role=ROLE_EVALUATOR)
        if QUESTION_BANK:
            question_input = get_chosen_question()
            print(f"Chosen question: {question_input}\n")
        else:
            question_input = input("> ")

        research = await handle_research(agent=agent_researcher, user_input=question_input, temperature=0.15,
                                         max_tokens=2000)
        if CONSOLE_LOGS:
            print(research)

        results = await handle_calculations(evaluator=agent_evaluator, user_input=question_input,
                                            research=research, max_tokens=3000)

        print("AGENT EVALUATION: ", results)

    finally:
        for model in USED_MODELS:
            quit_ollama(model)
        if CONSOLE_LOGS:
            print("\nClosed all models")


if __name__ == "__main__":
    asyncio.run(main())