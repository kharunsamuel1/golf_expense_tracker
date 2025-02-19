import json
import os
import base64
import re
import pandas as pd

import openai
from bs4 import BeautifulSoup

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 🔹 OAuth 2.0 Scope (Read-Only Gmail Access)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
openai_key = "sk-1234567890abcdef1234567890abcdef" # Replace with your OpenAI API key
client = openai.OpenAI(api_key=openai_key)

def authenticate_gmail():
    """Authenticate and return Gmail API service"""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)




def parse_email_body_with_gpt(body):
    """Parse email body using OpenAI GPT-3.5 to extract details."""

    prompt=f"""
    Determine if this is a golf confirmation email and extract the following details in the specified types
    Only consider golf confirmations with complete tee time details, not reminders and other emails
    If the body is empty or it's strictly not a golf confirmation - return 0 for is_confirmation and empty fields for the others:
    
    - Course Fees (number)
    - Convenience Fees if any (number)
    - Course Name (string)
    - Date (mm/dd/yy string)
    - Is this a cancellation email vs confirmation (0/1)
    - How much of the price is still due at course? (number)
    - How much of the price was paid online? (number)
    - Number of players (number)

    Email body:
    {body}

    Provide the details as **valid JSON output**, ensuring:
    - No additional formatting, explanations, or extra text.
    - The JSON starts with '{{' and ends with '}}'.
    - The keys are always enclosed in double quotes.
    - The values are properly formatted for JSON.
    - Any boolean values are represented as 0 or 1.

    JSON format:
    {{
        \"is_golf_confirmation\": 1,
        \"course_fees\": \"42.50\",
        \"convenience_fees\": \"2.50\",
        \"course_name\": \"Blue Water Golf Course\",
        \"date\": \"05/10/24\",
        \"is_cancellation\": 0,
        \"due_at_course\":  \"42.50\",
        \"paid_online\": \"2.50\",
        \"number_of_players\": 2
    }}
    
    Return only this JSON object with no extra text/quotations/formatting.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )
    try:
        origret = response.choices[0].message.content.strip()
        ret = re.sub(r'^["\']+|["\']+$', '', origret).strip()
        ret = re.sub(r'\bjson', '', ret).strip()

        ret = json.loads(ret)
    except Exception as e:
        print("Error parsing GPT response for following string")
        print(origret)
        return None

    return ret

def get_golf_emails(service):
    before_date = "2024/08/28"
    query = f'golf confirmation before:{before_date}'
    results = service.users().messages().list(userId="me", q=query, labelIds=["INBOX"], maxResults=20).execute()

    # 🔍 Debugging: Print raw API response
    print("\n🔍 API Response:\n", results)

    messages = results.get("messages", [])
    if not messages:
        print("⚠️ No emails found!")
        return []

    print(f"✅ Found {len(messages)} emails.")

    def get_body_from_parts(payload):
        """Extract the body from the email payload, handling both text/plain and text/html parts."""
        if payload["mimeType"] == "text/plain":
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            return body

        elif payload["mimeType"] == "text/html":
            html_content = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract structured table values and keep them formatted
            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    columns = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]

            text_content = soup.get_text("\n")  # Preserve new lines
            return text_content

        elif "parts" in payload:
            extracted_parts = []
            for part in payload["parts"]:
                result = get_body_from_parts(part)
                if result:
                    extracted_parts.append(result)
            return "\n".join(extracted_parts)  # Combine all extracted parts

        return ""

    email_data = []
    for msg in messages:
        msg_id = msg["id"]
        msg_data = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        subject = next((header["value"] for header in msg_data["payload"]["headers"] if header["name"] == "Subject"),
                       "No Subject")
        email_date = next((header["value"] for header in msg_data["payload"]["headers"] if header["name"] == "Date"),
                        "No Date")

        # Extract the body of the email
        body = get_body_from_parts(msg_data["payload"])
        parsed_details = parse_email_body_with_gpt(body)
        try:
            if not parsed_details:
                continue
            if not bool(parsed_details["is_golf_confirmation"]) or int(parsed_details["course_fees"]) == 0:
                print("skipping email " + str(parsed_details) + " " + subject)
                continue


            email_data.append({
                "course_name": parsed_details.get("course_name", ""),
                "course_fees": parsed_details.get("course_fees", ""),
                "convenience_fees": parsed_details.get("convenience_fees", ""),
                "date": parsed_details.get("date", ""),
                "is_golf_confirmation": bool(parsed_details.get("is_golf_confirmation", 0)),
                "is_cancellation": bool(parsed_details.get("is_cancellation", 0)),
                "due_at_course": parsed_details.get("due_at_course", ""),
                "paid_online": parsed_details.get("paid_online", ""),
                "number_of_players": int(parsed_details.get("number_of_players", 0))
            })
        except Exception as e:
            print("skipping email with exception" + str(parsed_details) + " " + subject)

    df = pd.json_normalize(email_data)
    df.set_index(['course_name', 'date'], inplace=True)
    return df

def main():
    """Main function to fetch last 30 emails"""
    gmail_service = authenticate_gmail()
    df = get_golf_emails(gmail_service)
    if not df.empty:
        df.to_csv("emails.csv", mode='a', header=False)  # Save DataFrame as CSV
        print("✅ Emails saved emails.csv")


if __name__ == "__main__":
    main()