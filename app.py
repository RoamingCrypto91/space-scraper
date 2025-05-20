from flask import Flask, request, make_response
import subprocess
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import re

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

app = Flask(__name__)
client = WebClient(token=SLACK_BOT_TOKEN)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    
    # Slack verification challenge
    if data.get("type") == "url_verification":
        return make_response(data["challenge"], 200, {"content_type": "text/plain"})

    # Respond to messages
    if "event" in data:
        event = data["event"]
        if event.get("type") == "message" and "text" in event:
            url_match = re.search(r"https:\/\/twitter\.com\/i\/spaces\/\w+", event["text"])
            if url_match:
                space_url = url_match.group(0)
                try:
                    # Download audio
                    subprocess.run([
                        "yt-dlp", "-x", "--audio-format", "mp3", "-o", "space_audio.%(ext)s", space_url
                    ], check=True)

                    # Upload audio to Slack
                    client.files_upload(
                        channels=event["channel"],
                        file="space_audio.mp3",
                        title="Downloaded Twitter Space",
                        initial_comment="Here’s the audio from the posted Twitter Space."
                    )
                    os.remove("space_audio.mp3")
                except SlackApiError as e:
                    print(f"Slack error: {e.response['error']}")
                except Exception as e:
                    print(f"General error: {e}")
    return make_response("OK", 200)
