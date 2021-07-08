import os
import sys
import requests
import json

from flask import Flask, request, abort
from linebot import (
	LineBotApi, WebhookHandler
)
from linebot.exceptions import (
	InvalidSignatureError
)
from linebot.models import (
	MessageEvent, TextMessage, TextSendMessage
)

app = Flask(__name__)

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
	print('Specify LINE_CHANNEL_SECRET as environment variable.')
	sys.exit(1)
if channel_access_token is None:
	print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
	sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route('/callback', methods=['POST'])
def callback():
	signature = request.headers['X-Line-Signature']

	body = request.get_data(as_text=True)
	app.logger.info('Request body: ' + body)

	try:
		handler.handle(body, signature)
	except InvalidSignatureError:
		abort(400)

	return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def echo_text(event):
	message = event.message.text
	starting_point, end_point = message.split('から', 2)
	payloads = {'starting_point':starting_point, 'end_point':end_point}
	res = requests.get('https://tline-table-scraping.herokuapp.com/mock', params = payloads)
	time_table = json.loads(res.text)['time_table']
	line_bot_api.reply_message(
		event.reply_token,
		TextSendMessage(text = res.text)
	)

if __name__ == '__main__':
	host = '0.0.0.0'
	port = int(os.getenv('PORT', '8000'))

	app.run(debug=True, host=host, port=port)