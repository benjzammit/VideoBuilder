import google.generativeai as genai
from src.config import settings
from src.setup_vector_db import EMBEDDING_DIMENSION
import random

# Configure the client. This will only succeed if the API key is set.
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ WARNING: Gemini client could not be configured: {e}")
else:
    print("⚠️ WARNING: GEMINI_API_KEY not set. Gemini client will run in mocked mode.")

def get_text_embedding(text: str, model="models/text-embedding-004") -> list[float]:
    """
    Generates a vector embedding for a given text using the Gemini API.
    Falls back to a mocked response if the API key is not configured.

    Args:
        text: The input text to embed.
        model: The name of the embedding model to use.

    Returns:
        A list of floats representing the vector embedding, or None on error.
    """
    if not settings.GEMINI_API_KEY:
        # print(f"MOCK: Pretending to generate embedding for text: '{text[:50]}...'")
        return [random.random() for _ in range(EMBEDDING_DIMENSION)]

    try:
        print(f"Generating embedding for text: '{text[:50]}...'")
        result = genai.embed_content(model=model, content=text, task_type="RETRIEVAL_DOCUMENT")
        return result['embedding']
    except Exception as e:
        print(f"🚫 An unexpected error occurred during embedding generation: {e}")
        return None

import json

def generate_production_plan(user_prompt: str, relevant_shots: list[dict], video_transcript: str) -> dict:
    """
    Uses the Gemini API to generate a structured production plan in JSON format.

    Args:
        user_prompt: The user's creative request.
        relevant_shots: A list of the most semantically relevant shots found via vector search.
        video_transcript: The full transcript of the video for context.

    Returns:
        A dictionary representing the production plan, or None on error.
    """
    if not settings.GEMINI_API_KEY:
        print(f"MOCK: Pretending to generate production plan for prompt: '{user_prompt}'")
        # Return a simple plan using the first few relevant shots
        mock_clips = [
            {"shot_id": i, "duration": shot['end_time'] - shot['start_time']}
            for i, shot in enumerate(relevant_shots[:3])
        ]
        return {"title": "My Awesome Mocked Video", "clips": mock_clips}

    # Prepare the context for the Gemini prompt
    shots_context = "\n".join(
        f"  - shot_id: {i}, duration: {shot['end_time'] - shot['start_time']:.2f}s"
        for i, shot in enumerate(relevant_shots)
    )

    system_prompt = f"""
You are an expert AI video editor. Your task is to create a production plan in a structured JSON format based on a user's request and a list of available, semantically relevant video shots.

The user's request is: "{user_prompt}"

The full video transcript for context is: "{video_transcript}"

Here are the most relevant shots that have been pre-selected for you based on the user's request. Please create a sequence using ONLY these shots.
Available Shots:
{shots_context}

Based on the user's request, create a JSON object for the production plan. The JSON object must have a "clips" key, which is an array of objects. Each object in the array represents a clip to be included in the final video and MUST have a "shot_id" (corresponding to the index from the 'Available Shots' list above). You can also optionally include a "text_overlay" field (max 20 characters) for any text that should be added to the clip.

- Be creative in the sequence of shots.
- Do not use any shot_id that is not in the provided 'Available Shots' list.
- The output MUST be a single, valid JSON object and nothing else.

Example Output:
{{
  "title": "A short, catchy title for the video",
  "clips": [
    {{ "shot_id": 2, "text_overlay": "The Adventure Begins" }},
    {{ "shot_id": 0 }},
    {{ "shot_id": 1, "text_overlay": "A New Discovery" }}
  ]
}}
"""

    try:
        print("Generating production plan with Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        plan = json.loads(response.text)
        print("✅ Successfully generated production plan.")
        return plan
    except Exception as e:
        print(f"🚫 An unexpected error occurred during production plan generation: {e}")
        return None
