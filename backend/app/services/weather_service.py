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


def _will_rain(weather_code, probability, sum_mm) -> bool:
    if weather_code in RAIN_CODES:
        return True
    if probability is not None and probability >= 40:
        return True
    if sum_mm is not None and sum_mm > 0.5:
        return True
    return False


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

    return {
        "date": date_str,
        "will_rain": _will_rain(weather_code, probability, sum_mm),
        "precipitation_probability": probability,
        "weather_code": weather_code,
    }


def get_rain_days_for_range(start_date: str, end_date: str) -> set:
    """Returns the set of "YYYY-MM-DD" dates within [start_date, end_date]
    that will/did rain - used to shade the calendar's month grid. Merges the
    forecast and archive endpoints the same way get_weather_for_date does for
    a single day; dates too far in the future for either endpoint (Open-Meteo's
    forecast horizon is limited) are just left out."""
    rain_days = set()
    covered = set()
    for url, include_probability in ((FORECAST_URL, True), (ARCHIVE_URL, False)):
        for date_str, will_rain in _try_range_endpoint(url, start_date, end_date, include_probability).items():
            if date_str in covered:
                continue
            covered.add(date_str)
            if will_rain:
                rain_days.add(date_str)
    return rain_days


def _try_range_endpoint(url: str, start_date: str, end_date: str, include_probability: bool) -> dict:
    daily_vars = "weathercode,precipitation_sum"
    if include_probability:
        daily_vars += ",precipitation_probability_max"

    params = {
        "latitude": TAICHUNG_LAT,
        "longitude": TAICHUNG_LON,
        "daily": daily_vars,
        "timezone": "Asia/Taipei",
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return {}

    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weathercode") or []
    precip_sum = daily.get("precipitation_sum") or []
    precip_prob = daily.get("precipitation_probability_max") or []

    result = {}
    for i, date_str in enumerate(dates):
        weather_code = codes[i] if i < len(codes) else None
        probability = precip_prob[i] if i < len(precip_prob) else None
        sum_mm = precip_sum[i] if i < len(precip_sum) else None
        result[date_str] = _will_rain(weather_code, probability, sum_mm)
    return result
