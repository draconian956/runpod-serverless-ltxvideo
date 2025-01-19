# This is an example that uses the websockets api and the SaveImageWebsocket node to get images directly without
# them being saved to disk

import json
import mimetypes
import urllib.parse
import urllib.request
import uuid
from base64 import b64decode, b64encode
from pathlib import Path
from pprint import pprint as echo
from time import sleep

import requests
import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)

runpodURL = ''

server_address = "127.0.0.1:8189"
client_id = str(uuid.uuid4())

RunPodTerminableStatusList = ['COMPLETED', 'FAILED', 'CANCELLED', 'TIMED_OUT']


class Memory:
	def __init__(self):
		self.runpod_endpoint_id = None
		self.header = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.41',
			'authorization': Path('.runpod_api_key').read_text(encoding='utf-8'),
		}
		self.runpod_input_tpl = {
			'input': {
				'api': {
					'method': 'POST',
					'endpoint': '/prompt'
				},
			}
		}


mem = Memory()

def queue_prompt(prompt):
	p = {"prompt": prompt, "client_id": client_id}
	data = json.dumps(p).encode('utf-8')
	req = urllib.request.Request(f'http://{server_address}/prompt', data=data)
	return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
	data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
	url_values = urllib.parse.urlencode(data)
	with urllib.request.urlopen(f'http://{server_address}/view?{url_values}') as response:
		return response.read()

def get_history(prompt_id):
	with urllib.request.urlopen(f'http://{server_address}/history/{prompt_id}') as response:
		return json.loads(response.read())

def upload_image(file_path):
	FilePathObj = Path(file_path)

	data_tpl = mem.runpod_input_tpl
	data_tpl['input']['api']['endpoint'] = '/upload/image'
	data_tpl['input']['filename'] = FilePathObj.name
	data_tpl['input']['b64_file_content'] = b64encode(FilePathObj.read_bytes()).decode('utf-8')
	req = requests.post(runpodURL, json=data_tpl, headers=mem.header)

	return req.json()

def PollRunPodStatus(JobID=''):
		r = requests.get(
			url=f'https://api.runpod.ai/v2/{mem.runpod_endpoint_id}/status/',
			json={},
			headers=mem.header
		)

		# logging.debug('PollRunPodStatus ::: r.text')
		# logging.debug(r.text)
		# logging.debug('PollRunPodStatus ::: r.json()')
		# logging.debug(r.json())

		return r.json()


demo_file_path = 'D:\\AI YT 影片工作區\\圖轉影片候選圖\\為什麼只有極少數的人能過上好生活並且自己不是那少數人裡的其中之一.png'
prompt_text = Path('api_demo_input.json').read_text(encoding='utf8')

prompt = json.loads(prompt_text)

# 範例輸出：
# upload_img_resp = {
# 	'name': '人們搞不明白，為什麼自己的生活會過得這麼痛苦、狼狽且無力.png',
# 	'subfolder': '',
# 	'type': 'input',
# }
upload_img_resp = upload_image(demo_file_path)

mem.runpod_endpoint_id = upload_img_resp['id']
file_upload_resp = None

while file_upload_resp is None:
	polled_resp = PollRunPodStatus()
	JobState = polled_resp['status']

	if JobState in RunPodTerminableStatusList:
		file_upload_resp = polled_resp
		break

	echo('任務尚未完成，休息 1 秒後再次檢查任務狀態...')
	sleep(1)

isVideoFile = mimetypes.guess_type(file_upload_resp['name'])[0].startswith('video')

if isVideoFile:
	prompt['181']['inputs']['video'] = upload_img_resp['name']
	prompt['181']['inputs']['custom_width'] = 1280
	prompt['181']['inputs']['custom_height'] = 720
else:
	prompt['106']['inputs']['image'] = upload_img_resp['name']

prompt['189']['inputs']['value'] = isVideoFile

queued_workflow = queue_prompt(prompt)
prompt_id = queued_workflow['prompt_id']
history = get_history(prompt_id)

while prompt_id not in history:
	history = get_history(prompt_id)
	sleep(1)

file_indicator = history.get(prompt_id, {}).get('outputs', {}).get('60', {}).get('gifs', [])[0]

image = get_image(
	filename=file_indicator['filename'],
	subfolder=file_indicator['subfolder'],
	folder_type=file_indicator['type']
)
Path(file_indicator.get('filename')).write_bytes(image)
ws.close()
