import json
import os
import requests
import sys

from flask import Flask, request

try:
    import apiai
except ImportError:
    sys.path.append(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
    )
    import apiai

app = Flask(__name__)

# Client Access Token for accessing our API AI Bot
CLIENT_ACCESS_TOKEN = 'INSERT_APIAI_CAT'
# Page Access Token for Facebook Page where the conversation can be started with the bot.
PAGE_ACCESS_TOKEN = 'INSERT_FACEBOOK_PAT'
# Token created whilst configuring Webhook subscription.
VERIFY_TOKEN = 'INSERT_TOKEN'

# An endpoint to ApiAi, an object used for making requests to a particular agent.
ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)


@app.route('/', methods=['GET'])
def print_signage():
    return "Contact: havanthao93@gmail.com."


# Handling HTTP GET when Facebook subscribes to our Webhook.
@app.route('/webhook', methods=['GET'])
def handle_verification():
    print("Handling Verification.")
    # Checking if the GET was sent by Messenger by matching the configured secret token.
    if request.args.get('hub.verify_token', '') == VERIFY_TOKEN:
        # Request.args contains the parsed contents of the query string.
        # The query string is appended to a HTTP call, containing parameters and values.     
        print("Webhook verified!")
        # Returning a random string that messenger has sent to us, for verification on their end.
        return request.args.get('hub.challenge', '')
    else:
        print("Wrong verification token!")
        return "Error, wrong validation token"


# Handling HTTP POST when Facebook sends us a payload of messages that have
# have been sent to our bot. We're responding to a Messenger callback, one of
# the events our webhook is subscribed to has fired.
@app.route('/webhook', methods=['POST'])
def handle_message():
    data = request.get_json()

    if data["object"] == "page":
        # Iterating through entries and messaging events batched and sent to us by Messenger
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):  # Checking if the messaging even contains a message field.
                    sender_id = messaging_event["sender"]["id"]  # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    send_message_staggered(sender_id, parse_natural_text(message_text))  # Sending a response to the user.

    return "ok"


# Sending a message back through Messenger.
def send_message(sender_id, message_text):
    r = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "recipient": {"id": sender_id},
            "message": {"text": message_text}
        })
    )


# Takes a string of natural language text, passes it to ApiAI, returns a 
# response generated by an ApiAI bot.
def parse_natural_text(user_text):
    # Sending a text query to our bot with text sent by the user.
    api_request = ai.text_request()
    api_request.query = user_text

    # Receiving the response.
    response = json.loads(api_request.getresponse().read().decode('utf-8'))
    response_status = response['status']['code']
    if response_status == 200:
        # Sending the textual response of the bot.
        return response['result']['fulfillment']['speech']

    else:
        return "Sorry, I couldn't understand that question"

        # NOTE:
        # At the moment, all messages sent to ApiAI cannot be differentiated,
        # they are processed as a single conversation regardless of concurrent
        # conversations. We need to perhaps peg a session id (ApiAI) to a recipient
        # id (Messenger) to fix this.

        # request.session_id = "<SESSION ID, UNIQUE FOR EACH USER>"


# Sends the message in segments delimited by a period.
def send_message_staggered(sender_id, message_text):
    sentence_delimiter = ". "
    messages = message_text.split(sentence_delimiter)

    for message in messages:
        send_message(sender_id, message)


# run server
if __name__ == "__main__":
    app.run()
