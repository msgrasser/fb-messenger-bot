import os
import sys
import json

import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    process_message(sender_id, message_text)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200

def process_message(sender_id, msg_in):
    resp = requests.get("https://graph.facebook.com/v2.6/{}?access_token={}".format(sender_id, os.environ["PAGE_ACCESS_TOKEN"]))
    user_dict = json.loads(resp._content)
    log("sender_details: {}".format(user_dict))

    first_name = user_dict["first_name"]
    last_name = user_dict["last_name"]
    profile_pic = user_dict["profile_pic"]
    locale = user_dict["locale"]
    timezone = user_dict["timezone"]
    gender = user_dict["gender"]

    title = "Mr." if gender == "male" else "Ms."
    local_hour = datetime.utcnow().hour + timezone
    salutation_time = "day"
    if local_hour < 3:
        salutation_time = "evening"
    elif local_hour < 12:
        salutation_time = "morning"
    elif local_hour < 17:
        salutation_time = "afternoon"
    else:
        salutation_time = "evening"

    msg_out = ""
    if msg_in == "Hello":
        msg_out = "Good {}, {} {}! How may I assist you?".format(salutation_time, title, last_name)
    elif msg_in == "Agent 123 ripped me off":
        msg_out =  "I'm sorry to hear that, {}. It sounds like you're attempting to report a case of agent fraud against Agent 123, in which case I'll just need a few more details. Are you comfortable sharing?".format(first_name)
    elif msg_in == "Yeah":
        msg_out = "Great! First, was there any disclosure of pricing? (examples include: posters, billboards, pamphlets, and other materials that list the prices of the service - see the full regulation at http://www.example.com/agent_pricing_disclosure_law.pdf)"
    elif msg_in == "Yes":
        msg_out = "Great, thank you for the information. It sounds like the agent was in compliance with the first part of the regulation. Did you also receive a message at the time of the transaction? (e.g. via SMS, push notification, or USSD confirmation)"    
    elif msg_in == "Yep":
        msg_out = "Ok, thank you. While I'm very sorry to hear about your negative experience, it sounds like your agent was actually in compliance with existing regulation. If you are unhappy with this provider, we suggest that you look around for other providers who better suit your needs. Can I help you with anything else today?"
    elif msg_in == "Nope":
        msg_out = "Ok, thank you. Based on the information you've provided, we will need to conduct a more detailed investigation into the matter, and will reach out to you via messenger when that's complete. Can I help you with anything else today?"    
    elif msg_in == "No":
        msg_out = "Ok, thank you for contacting me! Please let me know if you need anything else. I'll be patiently waiting! ;)"    

    if msg_out:
        send_message(sender_id, msg_out)

def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
