from flask import Flask, request, jsonify
import requests
import time
import jwt

# === CONFIGURATION ===
API_KEY = "2m72ckrU5Nkx7QQ6I8oXKPR5WGvB4X1tTaGR4uewrIGXwp6PisFJJQQJ99BEACGhslBXJ3w3AAALACOGiBRg"
ENDPOINT = "https://poc1qservices.cognitiveservices.azure.com"
MODEL_ID = "ClaimsModel_v1"
API_VERSION = "2023-07-31"

TENANT_ID = "685c2c50-3c15-4dbf-bf61-e67a1274d6db"
AUDIENCE = "api://f1d94ea1-397b-46a3-bd88-89dca240547e"

ISSUER_V1 = f"https://sts.windows.net/{TENANT_ID}/"
ISSUER_V2 = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
JWKS = requests.get(JWKS_URL).json()

app = Flask(__name__)

# In-memory store for extracted claims
claims_store = []

# === AUTHENTICATION HELPERS ===

def verify_token(token):
    try:
        headers = jwt.get_unverified_header(token)
        key = next(k for k in JWKS["keys"] if k["kid"] == headers["kid"])
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

        decoded = jwt.decode(
            token,
            public_key,
            audience=AUDIENCE,
            issuer=[ISSUER_V1, ISSUER_V2],  # accept both v1 and v2 issuers
            algorithms=["RS256"]
        )
        return decoded
    except Exception as e:
        print("Auth error:", str(e))
        return None


def require_auth():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, jsonify({"error": "Missing or invalid auth header"}), 401
    token = auth_header.split(" ")[1]
    user = verify_token(token)
    if not user:
        return None, jsonify({"error": "Unauthorized"}), 401
    return user, None, None

# === ROUTES ===

@app.route('/', methods=['GET'])
def hello():
    return "✅ Claims API is running."

@app.route('/upload-claim', methods=['POST'])
def upload_claim():
    user, err_response, status = require_auth()
    if not user:
        return err_response, status

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']

    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY,
        "Content-Type": "application/pdf"
    }

    # Step 1: Send PDF to Azure
    post_url = f"{ENDPOINT}/formrecognizer/documentModels/{MODEL_ID}:analyze?api-version={API_VERSION}"
    post_response = requests.post(post_url, headers=headers, data=file.read())

    if post_response.status_code != 202:
        return jsonify({"error": "Azure submission failed", "details": post_response.text}), 500

    result_url = post_response.headers.get("operation-location")

    # Step 2: Poll result URL
    for _ in range(10):
        time.sleep(2)
        result_response = requests.get(result_url, headers={"Ocp-Apim-Subscription-Key": API_KEY})
        result_data = result_response.json()
        if result_data.get("status") == "succeeded":
            break
        elif result_data.get("status") == "failed":
            return jsonify({"error": "Document analysis failed"}), 500
    else:
        return jsonify({"error": "Azure processing timeout"}), 504

    # Step 3: Extract fields
    fields = result_data.get("analyzeResult", {}).get("documents", [{}])[0].get("fields", {})
    extracted = {k: v.get("content") for k, v in fields.items()}

    # Step 4: Save to memory
    claims_store.append({
        "user": user.get("preferred_username"),
        "claim": extracted
    })

    return jsonify({
        "message": "Claim extracted successfully",
        "extracted_fields": extracted,
        "total_claims": len(claims_store)
    })

@app.route('/claims', methods=['GET'])
def get_claims():
    user, err_response, status = require_auth()
    if not user:
        return err_response, status

    user_email = user.get("preferred_username")
    user_claims = [c for c in claims_store if c["user"] == user_email]

    return jsonify({
        "user": user_email,
        "claims": user_claims
    })

if __name__ == '__main__':
    app.run(debug=True)
