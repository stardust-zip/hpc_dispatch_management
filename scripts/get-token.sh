#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# This script logs in to your User Service (on port 8080) to get a
# fresh, valid JWT.
#
# FINAL FIX: The JSON path for the token was wrong.
# It's `.token`, not `.authorisation.token`.
# -----------------------------------------------------------------------------

# --- CONFIGURATION ---
LOGIN_USERNAME="lecturer1"
LOGIN_PASSWORD="123456"
LOGIN_URL="http://localhost:8080/api/v1/login"

# -----------------------------------------------------------------------------

echo "Attempting to log in as user: $LOGIN_USERNAME..."

RESPONSE=$(curl -s -X POST "$LOGIN_URL" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d @- <<EOF
{
    "username": "$LOGIN_USERNAME",
    "password": "$LOGIN_PASSWORD",
    "user_type": "lecturer"
}
EOF
)

#
# THE ONLY FIX IS ON THIS LINE: Changed from .authorisation.token to .token
#
TOKEN=$(echo "$RESPONSE" | jq -r .token)

# Check if we actually got a token
if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "----------------------------------------"
    echo "Login FAILED."
    echo ""
    echo "Full response from server:"
    echo "$RESPONSE"
    echo ""
    echo "This should not happen. Check the server response."
    echo "----------------------------------------"
    exit 1
else
    echo "----------------------------------------"
    echo "Login SUCCESSFUL!"
    echo "A new, valid token has been generated."
    echo ""
    echo "Your new token is:"
    echo "$TOKEN"
    echo ""
    echo "Use this token in Postman for your request to port 8888."
    echo "----------------------------------------"
fi

