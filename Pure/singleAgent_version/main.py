import random
import json
import asyncio
from datetime import datetime

from Pure.multiAgent_version.Agent import Agent, check_ollama_model, quit_ollama
from Pure.questions.question_bank import get_chosen_question
from prompt import *

# technically the thesis description at mojaPG says 'single model'
# literally everything else is about agents and not just models though
# hence a single agent version and not a single model version

EVALUATION_RUNS=2

AGENT_MODEL = "llama3.1:8b"
# TODO: TEST THE MODELS TO SEE WHICH WORK BEST FOR WHICH ROLE

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
            question_input = get_chosen_question('Mathematics/MATH_abridged.json')
            print(f"Chosen question: {question_input}\n")
        else:
            question_input = input("> ")

        result = await handle_calculations(user_input=question_input, max_tokens=3000)

        print("\nAGENT'S RESULT: ", result)

    finally:
        quit_ollama(AGENT_MODEL)
        if CONSOLE_LOGS:
            print("\nClosed model")


if __name__ == "__main__":
    asyncio.run(main())