#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# This script performs a full end-to-end test of the dispatch creation workflow.
#
# v6.0: This version has all fixes:
#   1. Sends the correct login payload: {username, password, user_type}
#   2. Parses the correct token path: .token
#   3. Has robust error checking to fail immediately if login is unsuccessful.
# -----------------------------------------------------------------------------

# --- Configuration ---
LOGIN_URL="http://localhost:8080/api/v1/login"
LOGIN_USERNAME="lecturer1"
LOGIN_PASSWORD="123456" # Make sure this is your correct password

DISPATCH_URL="http://localhost:8888/dispatches/"

# --- Step 1: Log in to the User Service to get a token ---
echo "Attempting to log in as user: $LOGIN_USERNAME..."

# Create the login JSON payload
LOGIN_PAYLOAD=$(cat <<EOF
{
    "username": "$LOGIN_USERNAME",
    "password": "$LOGIN_PASSWORD",
    "user_type": "lecturer"
}
EOF
)

# Make the login request
LOGIN_RESPONSE=$(curl -s -X POST "$LOGIN_URL" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d "$LOGIN_PAYLOAD")

# Parse the token from the response using jq.
# The '-e' flag makes jq exit with an error code if the key is not found.
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -e -r .token)

# Check the exit code of the last command ($?)
# If jq failed ($? is not 0), then the login failed.
if [ $? -ne 0 ]; then
    echo "----------------------------------------"
    echo "Login FAILED. Cannot proceed to create dispatch."
    echo "This is the REAL error from the login server:"
    echo "$LOGIN_RESPONSE" | jq .
    echo "----------------------------------------"
    exit 1
fi

echo "Login successful. Token captured."
echo " "


# --- Step 2: Use the token to create a dispatch ---

TIMESTAMP=$(date +%s)
UNIQUE_SERIAL="SCRIPT-TEST-$TIMESTAMP"
UNIQUE_TITLE="Test from Script ($TIMESTAMP)"

echo "Attempting to create a new dispatch: $UNIQUE_TITLE"

# Create the dispatch JSON payload
DISPATCH_PAYLOAD=$(cat <<EOF
{
    "title": "$UNIQUE_TITLE",
    "serial_number": "$UNIQUE_SERIAL",
    "description": "This dispatch was created by an automated test script at $(date)"
}
EOF
)

# Make the create dispatch request, using the $TOKEN
CREATE_RESPONSE=$(curl -s -X POST "$DISPATCH_URL" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d "$DISPATCH_PAYLOAD")


# --- Step 3: Show the final result ---
echo "----------------------------------------"
echo "Test Complete. Response from Dispatch Service:"
echo "----------------------------------------"

# Use jq to check for an 'id' field in the response.
if echo "$CREATE_RESPONSE" | jq -e .id > /dev/null; then
    echo "SUCCESS! New dispatch created."
    echo ""
    echo "$CREATE_RESPONSE" | jq .
else
    echo "FAILURE. Could not create dispatch."
    echo ""
    echo "Server response:"
    echo "$CREATE_RESPONSE" | jq .
fi
