from typing import Optional, List

from langchain_community.tools import tool
from pydantic import BaseModel

class PlayerState(BaseModel):
    question: str
    selected_tools: Optional[List[str]] = None
    name: Optional[str] = None
    club: Optional[str] = None
    country: Optional[str] = None
    number: Optional[int] = None
    rating: Optional[int] = None
    goals: Optional[List[int]] = None
    minutes_played: Optional[List[int]] = None
    summary: Optional[str] = None

@tool
def fetch_player_information_tool(name: str):
    """Contains information about the football club of a player and its country"""
    data = {
        'Haaland': {
            'club': 'Manchester City',
            'country': 'Norway'
        },
        'Kane': {
            'club': 'Bayern',
            'country': 'England'
        },
        'Lautaro': {
            'club': 'Inter',
            'country': 'Argentina'
        },
        'Ronaldo': {
            'club': 'Al-Nassr',
            'country': 'Portugal'
        }
    }
    if name in data:
        print(f"Returning player information: {data[name]}")
        return data[name]
    else:
        return {
            'club': 'unknown',
            'country': 'unknown'
        }

def fetch_player_information(state: PlayerState):
    return fetch_player_information_tool.invoke({'name': state.name})

@tool
def fetch_player_jersey_number_tool(name: str):
    "Returns player jersey number"
    data = {
        'Haaland': 9,
        'Kane': 9,
        'Lautaro': 10,
        'Ronaldo': 7
    }
    if name in data:
        print(f"Returning player number: {data[name]}")
        return {'number': data[name]}
    else:
        return {'number': 0}

def fetch_player_jersey_number(state: PlayerState):
    return fetch_player_jersey_number_tool.invoke({'name': state.name})

@tool
def fetch_player_rating_tool(name: str):
    "Returns player rating in the FIFA"
    data = {
        'Haaland': 92,
        'Kane': 89,
        'Lautaro': 88,
        'Ronaldo': 90
    }
    if name in data:
        print(f"Returning rating data: {data[name]}")
        return {'rating': data[name]}
    else:
        return {'rating': 0}

def fetch_player_rating(state: PlayerState):
    return fetch_player_rating_tool.invoke({'name': state.name})