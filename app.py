import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── IBM watsonx.ai configuration ──────────────────────────────────────────────
WATSONX_API_KEY   = os.getenv("WATSONX_API_KEY",   "n8rU_kd5KAftj8wJBG6xjoBEb4D3oNQ0hPzIJ6R5qNZZ")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "ccf5dd54-f5e0-40eb-841c-4e866114e3db")
WATSONX_ENDPOINT  = os.getenv("WATSONX_ENDPOINT",   "https://us-south.ml.cloud.ibm.com")
# Fallback model list – tries each in order until one succeeds
LLM_MODELS = [
    "ibm/granite-13b-instruct-v2",
    "ibm/granite-3-8b-instruct",
    "ibm/granite-3.1-8b-instruct",
    "ibm/granite-3.2-8b-instruct",
    "meta-llama/llama-3-8b-instruct",
]

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# ── Helper: get IAM bearer token ──────────────────────────────────────────────
def get_iam_token() -> str:
    resp = requests.post(
        IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey":     WATSONX_API_KEY,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# ── Helper: call watsonx.ai text generation (auto-fallback) ──────────────────
def ask_watsonx(prompt: str) -> str:
    token = get_iam_token()
    url   = f"{WATSONX_ENDPOINT}/ml/v1/text/generation?version=2023-05-29"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
    last_error = None
    for model in LLM_MODELS:
        payload = {
            "model_id":   model,
            "project_id": WATSONX_PROJECT_ID,
            "input":      prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens":  600,
                "temperature":     0.7,
                "stop_sequences":  ["<|endoftext|>"],
            },
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 404:
                last_error = f"Model '{model}' not found, trying next..."
                continue
            resp.raise_for_status()
            return resp.json()["results"][0]["generated_text"].strip()
        except requests.exceptions.HTTPError as e:
            last_error = str(e)
            continue
    raise Exception(f"All models failed. Last error: {last_error}")


# ── Water intake baseline calculation ─────────────────────────────────────────
def calculate_baseline(weight_kg: float, activity: str, climate: str) -> float:
    """Returns baseline daily water intake in litres."""
    base = weight_kg * 0.033          # standard 33 ml / kg
    activity_map = {
        "sedentary":  0.0,
        "light":      0.3,
        "moderate":   0.6,
        "active":     0.9,
        "very_active": 1.2,
    }
    climate_map = {
        "cold":     0.0,
        "moderate": 0.2,
        "hot":      0.5,
        "very_hot": 0.8,
    }
    total = base + activity_map.get(activity, 0.0) + climate_map.get(climate, 0.0)
    return round(total, 2)


# ── Build LLM prompt ──────────────────────────────────────────────────────────
def build_prompt(data: dict, baseline: float) -> str:
    name        = data.get("name", "User")
    age         = data.get("age")
    gender      = data.get("gender", "not specified")
    weight      = data.get("weight")
    unit        = data.get("unit", "kg")
    activity    = data.get("activity", "moderate").replace("_", " ")
    climate     = data.get("climate", "moderate").replace("_", " ")
    health      = data.get("health_conditions", "none")
    goal        = data.get("goal", "general wellness")

    return f"""<|system|>
You are an expert AI Water Intake Advisor. Provide personalised, evidence-based hydration advice.
Always be encouraging, concise, and practical. Format your response clearly.
<|user|>
Please provide a personalised daily water intake plan for the following individual:

Name: {name}
Age: {age} years
Gender: {gender}
Weight: {weight} {unit}
Activity Level: {activity}
Climate/Environment: {climate}
Health Conditions / Notes: {health}
Health Goal: {goal}
Calculated Baseline Intake: {baseline} litres/day

Please include:
1. A brief personalised summary
2. Recommended daily water intake (confirm or adjust the baseline)
3. Hourly hydration schedule (waking hours)
4. 4–5 practical hydration tips tailored to their profile
5. Foods that can contribute to their hydration
6. Warning signs of dehydration to watch for

Keep the response friendly and motivating.
<|assistant|>
"""


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json(force=True)

        # Input validation
        required = ["weight", "age", "gender", "activity", "climate"]
        missing   = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        weight_kg = float(data["weight"])
        if data.get("unit") == "lbs":
            weight_kg = weight_kg * 0.453592

        baseline = calculate_baseline(weight_kg, data["activity"], data["climate"])
        prompt   = build_prompt(data, baseline)
        advice   = ask_watsonx(prompt)

        return jsonify({
            "baseline":  baseline,
            "advice":    advice,
            "weight_kg": round(weight_kg, 2),
        })

    except requests.exceptions.HTTPError as exc:
        return jsonify({"error": f"watsonx.ai API error: {exc.response.status_code} – {exc.response.text}"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
