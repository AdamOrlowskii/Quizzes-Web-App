import json
from typing import List

import openai

from app.settings.config import settings

CLARIN_API_KEY = settings.clarin_api_key
QUESTIONS_PER_CHUNK = settings.questions_per_chunk


def send_text_to_llm(text_chunks: List[str]) -> List[dict]:
    """
    Generuje pytania quizowe z chunków tekstu używając LLM

    Args:
        text_chunks: Lista fragmentów tekstu
        questions_per_chunk: Ile pytań na chunk (default: 3)

    Returns:
        Lista pytań: [{"Q": "...", "A": {...}, "C": "1"}, ...]
    """

    client = openai.OpenAI(
        api_key=CLARIN_API_KEY, base_url="https://services.clarin-pl.eu/api/v1/oapi/"
    )

    all_questions = []

    system_prompt = """ You are an expert at creating educational quiz questions.

RULES:
- Generate EXACTLY the requested number of multiple choice questions
- Each question must have 4 answer options (numbered 1-4)
- Only ONE answer is correct
- Questions should test understanding and key concepts
- Make questions clear and unambiguous
- Avoid trick questions
- Use the same language as in the text, if it's in polish, answer in polish

OUTPUT FORMAT (strict JSON array):
[
  {
    "Q": "Clear question text here?",
    "A": {
      "1": "First answer option",
      "2": "Second answer option", 
      "3": "Third answer option",
      "4": "Fourth answer option"
    },
    "C": "2"
  }
]

The "C" field is the correct answer number (must be "1", "2", "3", or "4").
Return ONLY the JSON array, no markdown formatting, no explanations."""

    print(f"Processing {len(text_chunks)} chunks with LLM...")

    for i, chunk in enumerate(text_chunks, 1):

        if not chunk.strip():
            continue

        print(f"Chunk {i}/{len(text_chunks)} ({len(chunk)} chars)...")

        user_prompt = f"""Generate EXACTLY {QUESTIONS_PER_CHUNK} quiz questions from the following text.

    TEXT:
{chunk}

Remember: Return ONLY the JSON array with {QUESTIONS_PER_CHUNK} questions."""

        try:
            print( "Calling GPT-4o...")
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            print(f"Received response: {len(content)} chars")
            
            print(f"Response preview: {content[:200]}...")
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            questions = json.loads(content)
            print(f"Parsed: {len(questions)} questions")
            
            if not isinstance(questions, list):
                print(f"ERROR: Expected list, got {type(questions)}\n")
                continue
            
            valid_questions = []
            for idx, q in enumerate(questions, 1):
                if all(key in q for key in ["Q", "A", "C"]):
                    if isinstance(q["A"], dict) and q["C"] in ["1", "2", "3", "4"]:
                        valid_questions.append(q)
                        print(f"Q{idx}: {q['Q'][:50]}...")
                    else:
                        print(f"Q{idx}: Invalid structure")
                else:
                    print(f"Q{idx}: Missing keys")
            
            all_questions.extend(valid_questions)
            print(f"\nCHUNK {i} COMPLETE: {len(valid_questions)} valid questions added")
            print(f"Running total: {len(all_questions)} questions\n")
            
        except json.JSONDecodeError as e:
            print(f"JSON PARSE ERROR: {e}")
            print(f"Full response:\n{content}\n")
            continue
            
        except Exception as e:
            print(f"ERROR: {e}\n")
            continue
    
    print(f"{'='*60}")
    print(f"FINAL RESULT: {len(all_questions)} questions generated")
    print(f"{'='*60}\n")
    
    return all_questions
