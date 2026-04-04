"""Step 2: Content synthesis via Gemini 2.5 Pro.

Takes raw research and produces structured newsletter content as JSON:
headline, sections, chart data, infographic prompt, sources, CTA.

Usage:
    uv run python tools/synthesize_content.py --input .tmp/research_raw.json
    uv run python tools/synthesize_content.py --input .tmp/research_raw.json --tone "casual" --audience "developers"
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / ".tmp" / "research_raw.json"
DEFAULT_OUTPUT = PROJECT_ROOT / ".tmp" / "newsletter_content.json"

SYSTEM_PROMPT = """You are a newsletter content editor for "AI Newsletter", a branded publication.

Your job: take raw research sources and produce a structured newsletter in JSON format.

Output ONLY valid JSON with this exact structure (no markdown fences, no explanation):
{
  "headline": "Compelling newsletter headline",
  "subtitle": "One-line subtitle that hooks the reader",
  "summary": "2-3 sentence overview of the newsletter topic",
  "sections": [
    {
      "heading": "Section title",
      "body": "2-3 paragraphs of well-written content. Use plain text, no markdown.",
      "key_stat": "A pull-quote or striking statistic from this section (or null if none)"
    }
  ],
  "chart_data": {
    "title": "Chart title",
    "type": "bar or line or pie",
    "labels": ["Label1", "Label2", "Label3"],
    "values": [10, 20, 30],
    "x_label": "X axis label",
    "y_label": "Y axis label"
  },
  "infographic_prompt": "A detailed prompt for generating a visual infographic about the topic. Describe the layout, what data/concepts to visualize, the style (modern, clean, professional), and specify colors: Primary Blue #2F94FB, Deep Blue #2367D3, Indigo #4B3FE0, Purple #8331A6 on a white background. Include text labels that should appear in the infographic.",
  "cta": {
    "text": "Call to action button text",
    "url": "https://relevant-link.com"
  },
  "sources": [
    {"title": "Source article title", "url": "https://source-url.com"}
  ]
}

Rules:
- Produce 3-4 sections with substantive, original writing that synthesizes the sources
- chart_data should contain REAL numbers from the research. If no quantitative data exists, set chart_data to null
- infographic_prompt should describe a visual that explains a key concept from the newsletter
- sources should reference the original research URLs
- cta should link to the most relevant source or a related resource
- Write for the specified tone and audience
- Do NOT use markdown formatting in body text — plain text only"""


def synthesize(research: dict, tone: str, audience: str,
               system_prompt: str | None = None) -> dict:
    """Send research to Gemini and get structured newsletter content.

    Args:
        system_prompt: Override the default SYSTEM_PROMPT (used by the
                       self-improving agent to inject Firestore-stored prompts).
    """
    client = genai.Client()
    active_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT

    # Truncate sources to avoid token overflow
    sources_text = ""
    for src in research.get("sources", []):
        md = src.get("markdown", "")
        if len(md) > 3000:
            md = md[:3000] + "\n... [truncated]"
        sources_text += f"\n\n--- SOURCE: {src.get('title', 'Untitled')} ---\nURL: {src.get('url', '')}\n{md}"

    user_prompt = f"""Topic: {research['topic']}
Tone: {tone}
Audience: {audience}

Research sources:
{sources_text}

Produce the newsletter JSON now."""

    print(f"Sending to Gemini 2.5 Pro (topic: {research['topic']})...", file=sys.stderr)

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=active_prompt,
            max_output_tokens=4096,
            temperature=0.7,
        ),
    )

    text = response.text.strip()
    # Strip markdown fences if Gemini wraps the JSON
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        content = json.loads(text)
    except json.JSONDecodeError:
        print("WARNING: First attempt returned invalid JSON, retrying...", file=sys.stderr)
        retry_response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=f"Your previous response was not valid JSON. Please output ONLY the JSON object, no markdown fences:\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                system_instruction=active_prompt,
                max_output_tokens=4096,
                temperature=0.3,
            ),
        )
        retry_text = retry_response.text.strip()
        if retry_text.startswith("```"):
            retry_text = retry_text.split("\n", 1)[1] if "\n" in retry_text else retry_text[3:]
            if retry_text.endswith("```"):
                retry_text = retry_text[:-3]
            retry_text = retry_text.strip()
        content = json.loads(retry_text)

    # Log token usage
    if hasattr(response, "usage_metadata"):
        usage = response.usage_metadata
        print(f"Tokens — input: {getattr(usage, 'prompt_token_count', '?')}, "
              f"output: {getattr(usage, 'candidates_token_count', '?')}", file=sys.stderr)

    return content


def main():
    parser = argparse.ArgumentParser(description="Synthesize newsletter content via Gemini")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Research JSON path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    parser.add_argument("--tone", default="professional but approachable", help="Editorial tone")
    parser.add_argument("--audience", default="general professionals", help="Target audience")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    research = json.loads(args.input.read_text(encoding="utf-8"))
    content = synthesize(research, args.tone, args.audience)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Output written to {args.output}", file=sys.stderr)
    print(str(args.output))


if __name__ == "__main__":
    main()
