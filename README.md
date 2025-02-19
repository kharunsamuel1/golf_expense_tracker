# Golf Booking Email Parser

This project extracts golf booking confirmation details from Gmail emails using the **Gmail API** and processes them with **OpenAI's GPT API** to extract structured data. The extracted data is saved as a CSV file.

## ⛺️ Setup Instructions

### 1️⃣ **Enable Gmail API & Set Up Credentials**
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the **Gmail API** for your project.
4. Go to **APIs & Services** > **Credentials**.
5. Click **Create Credentials** > **OAuth Client ID**.
6. Select **Desktop App** as the application type.
7. Download the `credentials.json` file and place it in the project directory.
8. Run the script once to authenticate (`token.json` will be generated automatically)

### 2️⃣ **Set Up OpenAI API**
1. Create an account on [OpenAI](https://platform.openai.com/).
2. Navigate to **API Keys** and generate a new API key.
3. Store the key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
   Alternatively, you can set it in the script as:
   ```python
   client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   ```

### 3️⃣ **Install Required Dependencies**
Run the following command to install required Python libraries:
```bash
pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client openai beautifulsoup4 pandas
```

### 4️⃣ **Run the Script**
To fetch and parse golf booking confirmation emails, execute:
```bash
python main.py
```
The extracted data will be appended to `emails.csv` in the project directory.

## 📂 File Structure
```
📁 golf-email-parser/
 ├── credentials.json      # Gmail API OAuth Credentials (Required for first-time setup)
 ├── token.json            # OAuth Token (Generated after authentication)
 ├── emails.csv            # Output file containing parsed golf bookings
 ├── main.py               # Main script
 ├── README.md             # Documentation
```

## 🛠 Troubleshooting
- **Invalid Credentials Error:** Ensure `credentials.json` is in the correct location.
- **Permission Denied (403) Error:** Check that Gmail API is enabled and the correct OAuth scopes are set.
- **GPT Response Parsing Issues:** Enable logging to inspect API responses for debugging.

📧 **Author:** Your Name  
📝 **License:** MIT  

