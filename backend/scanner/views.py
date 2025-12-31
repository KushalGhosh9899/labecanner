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
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)

    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({"error": "No image provided"}, status=400)

    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        image_bytes = image_file.read()
        
        prompt = """
        Analyze this product label image.
        1. Identify the 'category'.
        2. List all 'ingredients' found.

        Return ONLY a JSON object:
        {
            "category": "string or 'unknown'",
            "ingredients": ["list", "of", "strings"],
            "found": boolean
        }

        If no text or label is found, set "found" to false and return empty values.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                prompt
            ]
        )

        if not response.candidates or response.candidates[0].finish_reason == "SAFETY":
            return JsonResponse({
                "error": "CONTENT_BLOCKED",
                "message": "The image was flagged by safety filters. Please upload a clear product label."
            }, status=422)

        raw_text = response.text.strip() if response.text else ""
        
        if not raw_text:
            return JsonResponse({
                "error": "EMPTY_RESPONSE",
                "message": "The AI could not read any text from this image."
            }, status=422)

        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(raw_text)
            
            # Check the "found" flag we added to the prompt
            if data.get("found") is False or not data.get("ingredients"):
                return JsonResponse({
                    "error": "NO_INGREDIENTS_DETECTED",
                    "message": "No ingredients were found in this image. Try a closer, clearer shot."
                }, status=422)

            return JsonResponse(data, safe=False)

        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {str(e)} | Raw: {raw_text}")
            return JsonResponse({"error": "AI returned invalid format"}, status=500)

    except ClientError as e:
        if "429" in str(e):
            return JsonResponse({"error": "Rate limit exceeded. Try again in 30s."}, status=429)
        logger.error(f"Gemini Client Error: {str(e)}")
        return JsonResponse({"error": "External API error"}, status=400)

    except Exception as e:
        logger.error(f"Unexpected System Error: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)
    
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
    
@csrf_exempt
def scanner_pipeline_api(request):
    """
    Combined Endpoint: Image -> Extraction -> Toxicology Analysis
    """
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)

    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({"error": "No image provided"}, status=400)

    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        image_bytes = image_file.read()

        # --- STEP 1: EXTRACTION (Vision) ---
        extraction_prompt = """
        Analyze this product label image. Identify the 'category' and list all 'ingredients' found.
        Return ONLY a JSON object: {"category": "string", "ingredients": ["list"], "found": bool}
        """

        extraction_resp = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'), extraction_prompt]
        )

        # Basic validation for extraction
        if not extraction_resp.text:
            return JsonResponse({"error": "OCR failed: Image unreadable"}, status=422)
        
        raw_extraction = extraction_resp.text.strip()
        if raw_extraction.startswith("```json"):
            raw_extraction = raw_extraction.replace("```json", "").replace("```", "").strip()
        
        extracted_data = json.loads(raw_extraction)
        ingredients = extracted_data.get('ingredients', [])

        if not ingredients:
            return JsonResponse({"error": "No ingredients detected"}, status=422)

        # --- STEP 2: TOXICOLOGY ANALYSIS (Reasoning) ---
        analysis_resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Analyze these ingredients: {ingredients}",
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type='application/json',
                response_schema=ProductSafetyReport,
                system_instruction="""
                You are an official Regulatory Toxicologist. Use ONLY safety data from FDA, ECHA, and WHO.
                Priority: EU ECHA/CosIng database. Mark isHarmful: false if not officially flagged.
                """
            )
        )

        # Return the final safety report
        return JsonResponse(json.loads(analysis_resp.text), safe=False)

    except ClientError as e:
        if "429" in str(e):
            return JsonResponse({"error": "Rate limit reached. Try again in 30s."}, status=429)
        logger.error(f"Gemini API Error: {str(e)}")
        return JsonResponse({"error": "API Error during pipeline"}, status=400)
    except Exception as e:
        logger.error(f"Pipeline Crash: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)