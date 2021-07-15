import copy
import json
import os
import requests
import sys

from flask import Flask, request, abort
from linebot import (
	LineBotApi, WebhookHandler
)
from linebot.exceptions import (
	LineBotApiError, InvalidSignatureError
)
from linebot.models import (
	MessageEvent, TextMessage, FlexSendMessage
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
	except LineBotApiError as e:
		print(f'Got exception from LINE Messaging API: {e.message}')
		for m in e.error.details:
			print(f'{m.property}: {m.message}')
	except InvalidSignatureError:
		abort(400)

	return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
	URLs = load_urls_json_from_file()

	starting_point, end_point = parse_starting_point_and_end_point(event.message.text)

	payload = {'starting_point': starting_point, 'end_point': end_point}
	r = requests.get(f'{URLs["web_scraper"]["base"]}/{URLs["web_scraper"]["path_name"]}', params=payload)

	time_table = load_time_table_json_from_text(r.text)
	delay_url = load_delay_url_json_from_text(r.text)

	flex_message, body_contents_box, body_contents_separator = load_design_json_from_file()

	contents = copy.deepcopy(flex_message)

	contents['header']['contents'][0]['contents'][0]['text'] = starting_point
	contents['header']['contents'][2]['contents'][0]['text'] = end_point

	for i, time_table_element in enumerate(time_table):
		if i > 0:
			contents['body']['contents'].append(copy.deepcopy(body_contents_separator))

		new_body_contents_box = copy.deepcopy(body_contents_box)

		# 暫定的にアイコンは全て普通列車のものとする
		new_body_contents_box['contents'][0]['contents'][0]['url'] = URLs['icon']['local']

		if time_table_element["transfer"] == 0:
			new_body_contents_box['contents'][0]['contents'][1]['text'] = f'{time_table_element["time"][0]} → {time_table_element["time"][1]}'
		else:
			new_body_contents_box['contents'][0]['contents'][1]['text'] = f'{time_table_element["time"][0]} ⇢ {time_table_element["time"][1]}'

		contents['body']['contents'].append(copy.deepcopy(new_body_contents_box))

		if i == len(time_table)-1:
			new_body_contents_box['contents'][0]['contents'][1]['text'] = delay_url

	line_bot_api.reply_message(
		event.reply_token,
		FlexSendMessage(alt_text=f'{starting_point}から{end_point}', contents=contents)
	)

def parse_starting_point_and_end_point(text):
	# 暫定的
	starting_point, end_point = text.split('から', maxsplit=1)

	return starting_point, end_point

def load_time_table_json_from_text(text):
	time_table = json.loads(text)['time_table']

	return time_table

def load_delay_url_json_from_text(text):
	delay_url = json.loads(text)['url']

	return delay_url

def load_design_json_from_file():
	with open('./design/flex_message.json') as f:
		flex_message = json.load(f)
	with open('./design/body_contents_box.json') as f:
		body_contents_box = json.load(f)
	with open('./design/body_contents_separator.json') as f:
		body_contents_separator = json.load(f)

	return flex_message, body_contents_box, body_contents_separator

def load_urls_json_from_file():
	with open('./urls.json') as f:
		URLs = json.load(f)

	return URLs

if __name__ == '__main__':
	host = '0.0.0.0'
	port = int(os.getenv('PORT', '8000'))

	app.run(debug=True, host=host, port=port)
