import json
import re


def extract_json(text: str):
    """Best-effort parsing of a JSON array/object out of raw LLM text output,
    tolerating stray code fences or extra commentary around the JSON."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def extract_json_and_body(text: str, marker: str = "===CONTENT==="):
    """Parses a response that's a short JSON object (metadata only - title,
    tags, summary, etc.) followed by a plain-text marker line and then a
    long free-form body (e.g. Markdown content).

    Long multi-line Markdown is deliberately kept OUT of the JSON entirely:
    asking an LLM to properly \\n-escape a multi-paragraph, multi-heading
    string inside JSON is unreliable (smaller/weaker models especially tend
    to drop the line breaks, which is what causes generated wiki content to
    render as one squished, unformatted blob). Splitting on a plain-text
    marker sidesteps that failure mode completely, since the body is never
    JSON-encoded/decoded.

    Returns (data: dict, body: str). Falls back to treating the whole
    response as JSON with a "content" field if the marker isn't found, for
    robustness against a model that ignores the format.
    """
    if marker not in text:
        data = extract_json(text)
        return data, (data.get("content", "") if isinstance(data, dict) else "")

    header, body = text.split(marker, 1)
    data = extract_json(header)
    return data, body.strip()

