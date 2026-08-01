from fastapi import APIRouter

from ..services.weather_service import get_weather_for_date

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("")
def weather(date: str):
    """date: "YYYY-MM-DD". Currently hardcoded to Taichung - see
    weather_service.py if you want to make the location configurable."""
    data = get_weather_for_date(date)
    if data is None:
        return {"date": date, "will_rain": None, "precipitation_probability": None, "weather_code": None}
    return data
