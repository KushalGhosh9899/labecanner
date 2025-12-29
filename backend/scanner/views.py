import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google import genai
from google.genai import types
from PIL import Image
import io
from google.genai.errors import ClientError
import logging
from .schemas import ProductSafetyReport

# Get the logger we defined in settings
logger = logging.getLogger('scanner')

@csrf_exempt
def analyze_label_api(request):
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({"error": "No image provided"}, status=400)

        try:
            # New SDK Client
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            
            # Convert uploaded file to bytes for the new SDK
            image_bytes = image_file.read()
            
            prompt = """
            Analyze this product label image.
            Return a JSON object with:
            - "category": The product type.
            - "ingredients": A clean list of all ingredient names.
            Strictly return ONLY the JSON.
            """

            # New generate_content syntax
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                    prompt
                ]
            )
            
            # Extract text and handle potential markdown blocks
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            return JsonResponse(json.loads(raw_text), safe=False)

        except ClientError as e:
            if e.code == 429 or "429" in str(e):
                logger.error(f"Gemini Quota Exceeded (Captured via ClientError): {str(e)}")
                return JsonResponse({
                    "code": "LIMIT_REACHED",
                    "message": "We are receiving too many requests. Please wait a minute and try again."
                }, status=429)
            
            logger.error(f"Gemini Client Error: {str(e)}")
            return JsonResponse({"error": "Request failed"}, status=400)

        except Exception as e:
            logger.error(f"Unexpected System Error: {str(e)}")
            return JsonResponse({"error": "Internal server error"}, status=500)
        
    return JsonResponse({"error": "POST only"}, status=405)

@csrf_exempt
def analyze_ingredients_api(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        ingredients_list = data.get('ingredients', [])

        if not ingredients_list:
            return JsonResponse({"error": "No ingredients found in request"}, status=400)

        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Analyze these ingredients: {ingredients_list}",
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type='application/json',
                response_schema=ProductSafetyReport,
                system_instruction="""
                You are an official Regulatory Toxicologist.
                STRICT REQUIREMENT: Use ONLY safety data as defined by the FDA, ECHA (EU), and WHO.
                - If an ingredient is NOT flagged by these specific bodies, mark isHarmful: false.
                - Do not include 'clean beauty' or speculative risks.
                - If multiple sources conflict, prioritize the EU ECHA/CosIng database.
                """
            )
        )

        result_data = json.loads(response.text)
        return JsonResponse(result_data, safe=False)

    except ClientError as e:
        if e.code == 429:
            logger.error(f"Quota Limit: {str(e)}")
            return JsonResponse({
                "code": "LIMIT_REACHED",
                "message": "Too many requests. Please try again in a moment."
            }, status=429)
        else:
            logger.error(f"Gemini Error: {str(e)}")
            return JsonResponse({"error": "API Client Error"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        return JsonResponse({"error": "An internal error occurred"}, status=500) 