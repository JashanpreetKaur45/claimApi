from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

# Azure details (REPLACE THESE!)
API_KEY = "2m72ckrU5Nkx7QQ6I8oXKPR5WGvB4X1tTaGR4uewrIGXwp6PisFJJQQJ99BEACGhslBXJ3w3AAALACOGiBRg"
ENDPOINT = "https://poc1qservices.cognitiveservices.azure.com"
MODEL_ID = "ClaimsModel_v1"
API_VERSION = "2023-07-31"

# Headers
analyze_headers = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Content-Type": "application/pdf"
}

@app.route('/upload-claim', methods=['POST'])
def upload_claim():
    # Auth check (basic token)
    token = request.headers.get("Authorization")
    if token != "Bearer mysecrettoken":
        return jsonify({"error": "Unauthorized"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # 1. Send file to Azure (POST)
    post_url = f"{ENDPOINT}/formrecognizer/documentModels/{MODEL_ID}:analyze?api-version={API_VERSION}"

    post_response = requests.post(post_url, headers=analyze_headers, data=file.read())
    if post_response.status_code != 202:
        return jsonify({"error": "Failed to submit to Azure", "details": post_response.text}), 500

    # 2. Get 'operation-location' to poll
    result_url = post_response.headers.get("operation-location")
    if not result_url:
        return jsonify({"error": "No operation-location returned"}), 500

    # 3. Poll until done (max 10 attempts)
    for attempt in range(10):
        time.sleep(2)  # wait 2 seconds
        result_response = requests.get(result_url, headers={"Ocp-Apim-Subscription-Key": API_KEY})
        result_data = result_response.json()

        status = result_data.get("status")
        if status == "succeeded":
            break
        elif status == "failed":
            return jsonify({"error": "Analysis failed"}), 500

    # 4. Extract fields from result
    fields = result_data.get("analyzeResult", {}).get("documents", [{}])[0].get("fields", {})
    extracted = {k: v.get("content") for k, v in fields.items()}

    return jsonify({"extracted_fields": extracted})

@app.route('/', methods=['GET'])
def hello():
    return "Claims API is running."

if __name__ == '__main__':
    app.run(debug=True)
