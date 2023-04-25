import time
from flask import Flask, request, jsonify
from sender import Sender
import requests
import json
import time
import pandas as pd
import os
import re
from datetime import datetime


class Receiver:

    def __init__(self, params):

        self.params = params

        self.sender_initializer()

        self.df = pd.DataFrame(
            columns=['prompt', 'url', 'filename', 'is_downloaded'])

    def sender_initializer(self):

        with open(self.params, "r") as json_file:
            params = json.load(json_file)

        self.channelid = params['channelid']
        self.authorization = params['authorization']
        self.headers = {'authorization': self.authorization}

    def retrieve_messages(self):
        r = requests.get(
            f'https://discord.com/api/v10/channels/{self.channelid}/messages?limit={100}', headers=self.headers)
        jsonn = json.loads(r.text)
        return jsonn

    def collecting_results(self):
        message_list = self.retrieve_messages()
        self.awaiting_list = pd.DataFrame(columns=['prompt', 'status'])
        for message in message_list:

            if (message['author']['username'] == 'Midjourney Bot') and ('**' in message['content']):

                if len(message['attachments']) > 0:

                    if (message['attachments'][0]['filename'][-4:] == '.png') or ('(Open on website for full quality)' in message['content']):
                        id = message['id']
                        prompt = message['content'].split(
                            '**')[1].split(' --')[0]
                        url = message['attachments'][0]['url']
                        filename = message['attachments'][0]['filename']
                        if id not in self.df.index:
                            self.df.loc[id] = [prompt, url, filename, 0]

                    else:
                        id = message['id']
                        prompt = message['content'].split(
                            '**')[1].split(' --')[0]
                        if ('(fast)' in message['content']) or ('(relaxed)' in message['content']):
                            try:
                                status = re.findall(
                                    "(\w*%)", message['content'])[0]
                            except:
                                status = 'unknown status'
                        self.awaiting_list.loc[id] = [prompt, status]

                else:
                    id = message['id']
                    prompt = message['content'].split('**')[1].split(' --')[0]
                    if '(Waiting to start)' in message['content']:
                        status = 'Waiting to start'
                    self.awaiting_list.loc[id] = [prompt, status]

    def outputer(self):
        if len(self.awaiting_list) > 0:
            print(datetime.now().strftime("%H:%M:%S"))
            print('prompts in progress:')
            print(self.awaiting_list)
            print('=========================================')

        waiting_for_download = [
            self.df.loc[i].prompt for i in self.df.index if self.df.loc[i].is_downloaded == 0]
        if len(waiting_for_download) > 0:
            print(datetime.now().strftime("%H:%M:%S"))
            print('waiting for download prompts: ', waiting_for_download)
            print('=========================================')

    def downloading_results(self):
        processed_prompts = []
        for i in self.df.index:
            if self.df.loc[i].is_downloaded == 0:
                response = requests.get(self.df.loc[i].url)
                with open(os.path.join('/Users/shengxinyuan/Documents/github/Midjourney_api', self.df.loc[i].filename), "wb") as req:
                    req.write(response.content)
                self.df.loc[i, 'is_downloaded'] = 1
                processed_prompts.append(self.df.loc[i].prompt)
        if len(processed_prompts) > 0:
            print(datetime.now().strftime("%H:%M:%S"))
            print('processed prompts: ', processed_prompts)
            print('=========================================')

    def main(self):
        while True:
            self.collecting_results()
            self.outputer()
            self.downloading_results()
            time.sleep(5)




# 创建 Flask 应用
app = Flask(__name__)


# 创建一个 API 路由，接受 POST 请求，用户通过关键词参数发送请求
@app.route('/api/send_and_receive', methods=['POST'])
def send_and_receive():
    

    # 从请求中获取关键词参数
    data = request.get_json()
    prompt = data.get('prompt')
    # prompt = prompt.replace('_', ' ')
    # prompt = " ".join(prompt.split())
    # prompt = re.sub(r'[^a-zA-Z0-9\s]+', '', prompt)
    # prompt = prompt.lower()

    sender = Sender(params)
    sender.send(prompt)

    # 使用 Receiver 类接收图片 URL
    receiver = Receiver(params)
    receiver.collecting_results()

    # 记录当前已检测到的图片数量
    initial_image_count = len(receiver.df.index)

    # 等待新图片出现
    max_wait_time = 600  # 最大等待时间，单位为秒
    wait_time = 0
    latest_image_url = ''

    while wait_time < max_wait_time:
        receiver.collecting_results()
        current_image_count = len(receiver.df.index)

        if current_image_count > initial_image_count:
            # 发现新图片，并且关键词一样，跳出循环
            latest_image_id = receiver.df.index[-1]
            latest_image_url = receiver.df.loc[latest_image_id].url
            latest_image_prompt = receiver.df.loc[latest_image_id].prompt
            if prompt == latest_image_prompt:
                break

        # 等待一段时间
        time.sleep(1)
        wait_time += 1

    

    request_in_progress = False

    # 将最新图片的URL作为响应返回
    return jsonify({'latest_image_url': latest_image_url})

if __name__ == "__main__":

    # 指定参数，这里修改为您提供的路径
    params = '/Users/shengxinyuan/Documents/github/Midjourney_api/sender_params.json'

    # 启动 Flask 应用
    app.run(debug=True, host='0.0.0.0', port=5001)
