from app.services.cache import cache_get, cache_set

CACHE_KEY = "events_data"

CURRENT_EVENTS = [
    {
        "name": "UFC 327: Prochazka vs Ulberg",
        "date": "Sat, Apr 11 – 9 PM ET",
        "location": "Kaseya Center, Miami, FL",
        "fights": [
            {"fighter_a": "Jiri Prochazka", "fighter_b": "Carlos Ulberg", "weight_class": "Light Heavyweight Title", "is_main_event": True},
            {"fighter_a": "Azamat Murzakanov", "fighter_b": "Paulo Costa", "weight_class": "Light Heavyweight", "is_main_event": False},
            {"fighter_a": "Curtis Blaydes", "fighter_b": "Josh Hokit", "weight_class": "Heavyweight", "is_main_event": False},
            {"fighter_a": "Dominick Reyes", "fighter_b": "Johnny Walker", "weight_class": "Light Heavyweight", "is_main_event": False},
            {"fighter_a": "Cub Swanson", "fighter_b": "Nate Landwehr", "weight_class": "Featherweight", "is_main_event": False},
            {"fighter_a": "Patricio Pitbull", "fighter_b": "Aaron Pico", "weight_class": "Featherweight", "is_main_event": False},
            {"fighter_a": "Kevin Holland", "fighter_b": "Randy Brown", "weight_class": "Welterweight", "is_main_event": False},
            {"fighter_a": "Mateusz Gamrot", "fighter_b": "Esteban Ribovics", "weight_class": "Lightweight", "is_main_event": False},
        ],
    }
]


async def fetch_events() -> list[dict]:
    return CURRENT_EVENTS
