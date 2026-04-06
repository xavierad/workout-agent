import json
import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama


from tools import PlayerState, fetch_player_information, fetch_player_jersey_number, fetch_player_rating


# load environment variables from .env file
load_dotenv()

# get model ready
llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "llama3.1"),
    base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    temperature=0,
)


def retrieve_goals(state: PlayerState):
    name = state.name
    data = {
        'Haaland': [25, 40, 28, 33, 36],
        'Kane': [33, 37, 41, 38, 29],
        'Lautaro': [19, 25, 27, 24, 25],
        'Ronaldo': [27, 32, 28, 30, 36]
    }
    if name in data:
        return {'goals': data[name]}
    else:
        return {'goals': [0]}
    
def retrieve_minutes_played(state: PlayerState):
    name = state.name
    data = {
        'Haaland': [2108, 3102, 3156, 2617, 2758],
        'Kane': [2924, 2850, 3133, 2784, 2680],
        'Lautaro': [2445, 2498, 2519, 2773],
        'Ronaldo': [3001, 2560, 2804, 2487, 2771]
    }
    if name in data:
        return {'minutes_played': data[name]}
    else:
        return {'minutes_played': [0]}
    
def extract_name(state: PlayerState):
    question = state.question
    prompt = f"""
You are a football name extractor assistant.
Your goal is to just extract a surname of a footballer in the following question.
User question: {question}
You have to just output a string containing one word - footballer surname.
    """
    response = llm.invoke([HumanMessage(content=prompt)]).content
    print(f"Player name: ", response)
    return {'name': response}

def planner(state: PlayerState):
    question = state.question
    prompt = f"""
You are a football player summary assistant.
You have the following tools available: ['fetch_player_jersey_number', 'fetch_player_information', 'fetch_player_rating']
User question: {question}
Decide which tools are required to answer.
Return a JSON list of tool names, e.g. ['fetch_player_jersey_number', 'fetch_rating']
    """
    response = llm.invoke([HumanMessage(content=prompt)]).content
    # Strip markdown code fences that llama models commonly add
    cleaned = response.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    try:
        selected_tools = json.loads(cleaned)
        if not isinstance(selected_tools, list):
            raise ValueError('not a list')
    except Exception:
        selected_tools = []
    print(f"Selected tools: {selected_tools}")
    return {'selected_tools': selected_tools}


def write_summary(state: PlayerState):
    question = state.question
    data = {
        'name': state.name,
        'country': state.country,
        'number': state.number,
        'rating': state.rating,
        'goals': state.goals,
        'minutes_played': state.minutes_played,
    }
    prompt = f"""
You are a football reporter assistant.
Given the following data and statistics of the football player, you will have to create a markdown summary of that player.
Player data:
{json.dumps(data, indent=4)}
The markdown summary has to include the following information:

- Player full name (if only first name or last name is provided, try to guess the full name)
- Player country (also add flag emoji)
- Player number (also add the number in the emoji(-s) form)
- FIFA rating
- Total number of goals in last 3 seasons
- Average number of minutes required to score one goal
- Response to the user question: {question}
    """
    response = llm.invoke([HumanMessage(content=prompt)]).content
    return {"summary": response}

ALL_TOOLS = ['fetch_player_jersey_number', 'fetch_player_information', 'fetch_player_rating']

def route_tools(state: PlayerState):
    tools = [t for t in (state.selected_tools or []) if t in ALL_TOOLS]
    return tools if tools else ALL_TOOLS


# Nodes for the graph
graph_builder = StateGraph(PlayerState)
graph_builder.add_node('extract_name', extract_name)
graph_builder.add_node('planner', planner)
graph_builder.add_node('fetch_player_jersey_number', fetch_player_jersey_number)
graph_builder.add_node('fetch_player_information', fetch_player_information)
graph_builder.add_node('fetch_player_rating', fetch_player_rating)
graph_builder.add_node('retrieve_goals', retrieve_goals)
graph_builder.add_node('retrieve_minutes_played', retrieve_minutes_played)
graph_builder.add_node('write_summary', write_summary)

graph_builder.add_edge(START, 'extract_name')
graph_builder.add_edge('extract_name', 'planner')
graph_builder.add_conditional_edges(
    'planner',
    route_tools,
    {
        'fetch_player_jersey_number': 'fetch_player_jersey_number',
        'fetch_player_information': 'fetch_player_information',
        'fetch_player_rating': 'fetch_player_rating'
    }
)
graph_builder.add_edge('fetch_player_jersey_number', 'retrieve_goals')
graph_builder.add_edge('fetch_player_information', 'retrieve_goals')
graph_builder.add_edge('fetch_player_rating', 'retrieve_goals')
graph_builder.add_edge('retrieve_goals', 'retrieve_minutes_played')
graph_builder.add_edge('retrieve_minutes_played', 'write_summary')
graph_builder.add_edge('write_summary', END)

graph = graph_builder.compile()

result = graph.invoke({
    'question': 'Will Haaland be able to win the FIFA World Cup for Norway in 2026 based on his recent performance and stats?'
})

print(result)