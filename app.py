import copy
import json
import os
import requests
import sys
from typing import List, Final, Any, Tuple

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

from firebase import Firebase

app = Flask(__name__)

SCRAPING_SERVER_URL: Final[str] = os.getenv('SCRAPING_SERVER_URL', None)
CHANNEL_SECRET: Final[str] = os.getenv('LINE_CHANNEL_SECRET', None)
CHANNEL_ACCESS_TOKEN: Final[str] = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if CHANNEL_SECRET is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if CHANNEL_ACCESS_TOKEN is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

firebase = Firebase()


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
    icons = load_icons_json_from_file()
    message: List[str] = event.message.text.split()

    if message[0] == '区間登録':
        user_id: str = event.source.user_id
        commuter_pass = get_scraping_payload(message[1])
        firebase.post_user_commuter_pass(user_id=user_id,
                                         commuter_pass=commuter_pass)
        line_bot_api.reply_message(
            event.reply_token,
            messages=TextMessage(text=f'{message[1]}で登録しました！')
        )
        return

    if message[0] == '定期':
        user_id: str = event.source.user_id
        payload = firebase.get_user_commuter_pass(user_id=user_id)
        if payload == 'Not Found':
            line_bot_api.reply_message(
                event.reply_token,
                messages=TextMessage(text='まだ区間登録が済んでいません！')
            )
            return

    else:
        payload = get_scraping_payload(message[0])

    r = requests.get(f'{SCRAPING_SERVER_URL}/scraping', params=payload)

    time_table, transfer_url = load_datas_form_json(r.text)

    flex_message, body_contents_box, body_contents_separator = load_design_json_from_file()

    contents = copy.deepcopy(flex_message)

    contents['header']['contents'][0]['contents'][0]['text'] = payload['starting_point']
    contents['header']['contents'][2]['contents'][0]['text'] = payload['end_point']

    for i, time_table_element in enumerate(time_table):
        if i > 0:
            contents['body']['contents'].append(copy.deepcopy(body_contents_separator))

        new_body_contents_box = copy.deepcopy(body_contents_box)

        new_body_contents_box['contents'][0]['contents'][0]['url'] = identify_type(time_table_element["type"], icons)

        if time_table_element["transfer"] == 0:
            new_body_contents_box['contents'][0]['contents'][1][
                'text'] = f'{time_table_element["time"][0]} → {time_table_element["time"][1]}'
        else:
            new_body_contents_box['contents'][0]['contents'][1][
                'text'] = f'{time_table_element["time"][0]} ⇢ {time_table_element["time"][1]}'
        contents['body']['contents'].append(copy.deepcopy(new_body_contents_box))

    contents['footer']['contents'][0]['action']['uri'] = transfer_url

    line_bot_api.reply_message(
        event.reply_token,
        FlexSendMessage(alt_text=f'{payload["starting_point"]}から{payload["end_point"]}', contents=contents)
    )
    return


def get_scraping_payload(text: str) -> dict[str, str]:
    # 暫定的
    starting_point, end_point = text.split('から', maxsplit=1)

    return {
        'starting_point': starting_point,
        'end_point': end_point
    }


def load_datas_form_json(text: str) -> Any:
    datas = json.loads(text)

    return datas['time_table'], datas['url']


def load_design_json_from_file() -> Tuple[Any, Any, Any]:
    with open('./design/flex_message.json') as f:
        flex_message = json.load(f)
    with open('./design/body_contents_box.json') as f:
        body_contents_box = json.load(f)
    with open('./design/body_contents_separator.json') as f:
        body_contents_separator = json.load(f)

    return flex_message, body_contents_box, body_contents_separator


def load_icons_json_from_file(path: str = './icons.json') -> dict[str, str]:
    with open(path) as f:
        icons: dict[str, str] = json.load(f)
    return icons


def identify_type(train_type: str, icons: dict[str, str]) -> str:
    if train_type == "local":
        return icons['local']
    elif train_type == "rapid":
        return icons['rapid']
    else:
        return icons['regional_rapid']


if __name__ == '__main__':
    host = '0.0.0.0'
    port = int(os.getenv('PORT', '8000'))

    app.run(debug=True, host=host, port=port)
