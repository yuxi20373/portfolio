"""Fetches Taichung's daily weather so the calendar can show a simple
rain / no-rain animated icon for whichever day is selected. Uses
Open-Meteo (https://open-meteo.com) - free, no API key required.

Tries the regular forecast endpoint first (it also covers a good chunk of
recent past via start_date/end_date, not just future days), and falls back
to the historical archive endpoint for older dates the forecast endpoint
doesn't have. If neither has data for that date, returns None and the
frontend just shows a neutral "no data" icon instead of guessing.
"""

import requests

TAICHUNG_LAT = 24.1477
TAICHUNG_LON = 120.6736

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# WMO weather codes that represent rain/showers/thunderstorms in some form
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


def get_weather_for_date(date_str: str):
    """Returns {"date", "will_rain", "precipitation_probability",
    "weather_code"} or None if no data is available for that date."""
    data = _try_endpoint(FORECAST_URL, date_str, include_probability=True)
    if data is None:
        data = _try_endpoint(ARCHIVE_URL, date_str, include_probability=False)
    return data


def _try_endpoint(url: str, date_str: str, include_probability: bool):
    daily_vars = "weathercode,precipitation_sum"
    if include_probability:
        daily_vars += ",precipitation_probability_max"

    params = {
        "latitude": TAICHUNG_LAT,
        "longitude": TAICHUNG_LON,
        "daily": daily_vars,
        "timezone": "Asia/Taipei",
        "start_date": date_str,
        "end_date": date_str,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None

    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    if date_str not in dates:
        return None
    idx = dates.index(date_str)

    codes = daily.get("weathercode") or []
    precip_sum = daily.get("precipitation_sum") or []
    precip_prob = daily.get("precipitation_probability_max") or []

    weather_code = codes[idx] if idx < len(codes) else None
    probability = precip_prob[idx] if idx < len(precip_prob) else None
    sum_mm = precip_sum[idx] if idx < len(precip_sum) else None

    will_rain = False
    if weather_code in RAIN_CODES:
        will_rain = True
    elif probability is not None and probability >= 40:
        will_rain = True
    elif sum_mm is not None and sum_mm > 0.5:
        will_rain = True

    return {
        "date": date_str,
        "will_rain": will_rain,
        "precipitation_probability": probability,
        "weather_code": weather_code,
    }
