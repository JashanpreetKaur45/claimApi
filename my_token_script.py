from msal import PublicClientApplication

app = PublicClientApplication(
    client_id="f1d94ea1-397b-46a3-bd88-89dca240547e",
    authority="https://login.microsoftonline.com/685c2c50-3c15-4dbf-bf61-e67a1274d6db",  # your tenant ID
)

result = app.acquire_token_interactive(
    scopes=["api://f1d94ea1-397b-46a3-bd88-89dca240547e/access_as_user"]
)

if "access_token" in result:
    print("Access token acquired successfully!")
    print(result["access_token"])
else:
    print("Failed to acquire token.")
    print(result.get("error"))
    print(result.get("error_description"))
