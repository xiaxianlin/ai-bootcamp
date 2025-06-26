import random
from typing import TypedDict
from langgraph.graph import StateGraph, END


class AgentState(TypedDict):
    name: str
    guesses: list[int]
    target: int
    counter: int
    lower_bound: int
    upper_bound: int
    hint: str


def setup_node(state: AgentState) -> AgentState:
    """Initialize the game"""
    state["name"] = f"Welcom, {state["name"]}"
    state["guesses"] = []
    state["target"] = random.randint(1, 20)
    state["counter"] = 0
    state["lower_bound"] = 1
    state["upper_bound"] = 20

    return state


def guess_node(state: AgentState) -> AgentState:
    """Input the guess number"""
    print(f"\n请在 {state['lower_bound']} 到 {state['upper_bound']} 之间猜一个数")
    query = input("\nGuess: ").strip()

    state["guesses"].append(int(query))
    state["counter"] += 1

    return state


def hint_node(state: AgentState) -> AgentState:
    """Here we provide a hint based on the last guess and update the bounds"""
    latest_guess = state["guesses"][-1]
    target = state["target"]

    if latest_guess < target:
        state["hint"] = f"The number {latest_guess} is too low. Try higher!"

        state["lower_bound"] = max(state["lower_bound"], latest_guess + 1)
        print(f"Hint: {state['hint']}")

    elif latest_guess > target:
        state["hint"] = f"The number {latest_guess} is too high. Try lower!"

        state["upper_bound"] = min(state["upper_bound"], latest_guess - 1)
        print(f"Hint: {state['hint']}")
    else:
        state["hint"] = f"Correct! You found the number {target} in {state['counter']} attempts."
        print(f"Success! {state['hint']}")

    return state


def should_continue(state: AgentState) -> str:
    """Determine if we should continue guessing or end the game"""
    print("ENTERING LOOP", state["counter"])
    latest_guess = state["guesses"][-1]
    if latest_guess == state["target"]:
        print(f"GAME OVER: Number found!")
        return "end"
    elif state["counter"] >= 7:
        print(f"GAME OVER: Maximum attempts reached! The number was {state['target_number']}")
        return "end"
    else:
        print(f"CONTINUING: {state['counter']}/7 attempts used")
        return "continue"


graph = StateGraph(AgentState)

graph.add_node("setup_node", setup_node)
graph.add_node("guess_node", guess_node)
graph.add_node("hint_node", hint_node)

graph.add_edge("setup_node", "guess_node")
graph.add_edge("guess_node", "hint_node")
graph.add_conditional_edges(
    "hint_node",
    should_continue,
    {
        "continue": "guess_node",
        "end": END,
    },
)

graph.set_entry_point("setup_node")

app = graph.compile()

app.invoke({"name": "Tom"})
