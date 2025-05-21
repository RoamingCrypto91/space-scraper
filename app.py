from flask import Flask, request, make_response
import subprocess
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

app = Flask(__name__)
client = WebClient(token=SLACK_BOT_TOKEN)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    logger.info("🔥 HIT /slack/events route")

    try:
        data = request.get_json(force=True)
        logger.info("📨 Received payload: %s", data)

        if data.get("type") == "url_verification":
            return make_response(data["challenge"], 200, {"content_type": "text/plain"})

        if "event" in data:
            event = data["event"]

            # Only handle plain user messages
            if event.get("type") == "message" and event.get("subtype") is None and "text" in event:
                url_match = re.search(r"https:\/\/twitter\.com\/i\/spaces\/\w+", event["text"])
                if url_match:
                    space_url = url_match.group(0)
                    logger.info("🎯 Matched Twitter Space URL: %s", space_url)

                    try:
                        logger.info("🎧 Running yt-dlp...")
                        response = client.chat_postMessage(
                            channel=event["channel"],
                            thread_ts=event["ts"],
                            text=f"🛰️ Downloading the Twitter Space from <{space_url}>... sit tight!"
                        )
                        logger.info("💬 Posted download-start message to Slack")                        
                        subprocess.run([
                            "yt-dlp", "-f", "bestaudio",
                            "-o", "space_audio.%(ext)s", space_url
                        ], check=True)
                    
                        # Find the actual downloaded file (e.g., .m4a or .webm)
                        downloaded_file = next((f for f in os.listdir() if f.startswith("space_audio.")), None)
                        
                        if downloaded_file:
                            logger.info("✅ Download complete. Uploading %s to Slack...", downloaded_file)
                            client.files_upload_v2(
                                channel=event["channel"],
                                thread_ts=response["ts"],  # keep in same thread
                                file=downloaded_file,
                                title="Downloaded Twitter Space",
                                initial_comment="✅ Here’s the audio from the posted Twitter Space."
                            )
                            os.remove(downloaded_file)
                            logger.info("🚮 File %s cleaned up", downloaded_file)
                        else:
                            logger.error("❌ Could not find downloaded file to upload.")
                    
                    except SlackApiError as e:
                        logger.error("Slack error: %s", e.response["error"])
                    except Exception as e:
                        logger.error("❌ Error processing download/upload: %s", e)


        return make_response("Event received", 200)

    except Exception as e:
        logger.error("❌ Error handling request: %s", e)
        return make_response("Error", 500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
