# This is an example that uses the websockets api and the SaveImageWebsocket node to get images directly without
# them being saved to disk

import json
import mimetypes
import re
import urllib.request
import uuid
from base64 import b64decode, b64encode
from copy import deepcopy
from pathlib import Path
from pprint import pprint as echo
from random import randint
from time import sleep

import pendulum
import requests

runpodURL = 'https://api.runpod.ai/v2/***********/run'

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

def timeMsg(msg):
	echo(f'[{pendulum.now().to_datetime_string()}] {msg}')

def queue_prompt(prompt):
	data_tpl = deepcopy(mem.runpod_input_tpl)
	data_tpl['input']['payload'] = prompt
	req = requests.post(runpodURL, json=data_tpl, headers=mem.header)

	return req.json()

def upload_image(file_path):
	FilePathObj = Path(file_path)

	data_tpl = deepcopy(mem.runpod_input_tpl)
	data_tpl['input']['api']['endpoint'] = '/upload/image'
	data_tpl['input']['filename'] = FilePathObj.name
	data_tpl['input']['b64_file_content'] = b64encode(FilePathObj.read_bytes()).decode('utf-8')
	req = requests.post(runpodURL, json=data_tpl, headers=mem.header)

	return req.json()

def PollRunPodStatus(JobID=''):
		r = requests.get(
			url=f'https://api.runpod.ai/v2/{mem.runpod_endpoint_id}/status/{JobID}',
			json={},
			headers=mem.header
		)

		return r.json()


generate_video_count = 5
video_save_folder = 'E:\\RunPodVIdeo'
# demo_file_path = 'D:\\AI YT 影片工作區\\圖轉影片候選圖\\你可能已經聽過所謂的 8020 法則，也就是 80% 的財富由 20% 的人口所掌握.png'
demo_file_path = 'D:\\AI YT 影片工作區\\影片片段\\這意味著資源的分配與掌控存在著極大的不平等，而多數人都是屬於那 80% 的窮人_1.mp4'

prompt_text = Path('api_demo_input.json').read_text(encoding='utf8')
prompt = json.loads(prompt_text)

runpod_endpoint_id_regex = re.search(
	r"/v2/([^/]+)/run", runpodURL)

mem.runpod_endpoint_id = runpod_endpoint_id_regex.group(
	1) if runpod_endpoint_id_regex else ''

# 範例輸出：
# upload_img_resp = {
# 	'name': '人們搞不明白，為什麼自己的生活會過得這麼痛苦、狼狽且無力.png',
# 	'subfolder': '',
# 	'type': 'input',
# }
upload_img_resp = upload_image(demo_file_path)

job_id = upload_img_resp['id']

file_upload_resp = None

timeMsg('正在上傳檔案...')
while file_upload_resp is None:
	polled_resp = PollRunPodStatus(job_id)
	JobState = polled_resp.get('status')

	if JobState in RunPodTerminableStatusList:
		file_upload_resp = polled_resp
		break

	timeMsg('任務尚未完成，休息 10 秒後再次檢查任務狀態...')
	sleep(10)

isVideoFile = mimetypes.guess_type(file_upload_resp['output']['name'])[0].startswith('video')

if isVideoFile:
	prompt['181']['inputs']['video'] = file_upload_resp['output']['name']
	prompt['181']['inputs']['custom_width'] = 1280
	prompt['181']['inputs']['custom_height'] = 720
else:
	prompt['106']['inputs']['image'] = file_upload_resp['output']['name']

prompt['189']['inputs']['value'] = isVideoFile

for i in range(1, generate_video_count + 1):
	prompt['37']['inputs']['noise_seed'] = randint(1, 9999999999999999)
	prompt['111']['inputs']['seed'] = randint(1, 9999999999999999)

	queued_workflow_resp = queue_prompt(prompt)
	job_id = queued_workflow_resp['id']
	video_resp = None

	timeMsg('正在產生影片...')
	while video_resp is None:
		polled_resp = PollRunPodStatus(job_id)
		JobState = polled_resp['status']

		if JobState in RunPodTerminableStatusList:
			video_resp = polled_resp
			break

		timeMsg('任務尚未完成，休息 10 秒後再次檢查任務狀態...')
		sleep(10)

	video_resp = video_resp.get('output', {})
	file_indicator = video_resp.get('file_indicator', {})
	filename = file_indicator.get('filename', '')
	video_base64 = video_resp.get('video_base64', '')
	video_bytes = b64decode(video_base64)
	Path(f'{video_save_folder}\\{filename}').write_bytes(video_bytes)

	timeMsg(f'第 {i} 部影片產生完成！')

timeMsg('全部影片皆產生完成！')
