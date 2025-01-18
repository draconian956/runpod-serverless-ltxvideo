# This is an example that uses the websockets api and the SaveImageWebsocket node to get images directly without
# them being saved to disk

import json
import mimetypes
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from time import sleep

import requests
import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)

server_address = "127.0.0.1:8189"
client_id = str(uuid.uuid4())

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

def upload_image(file_path, folder_type=None):
	FilePathObj = Path(file_path)

	with FilePathObj.open('rb') as img_file:
		file_param = {
			'image': img_file
		}
		data_param = {
			'overwrite': 1,
			'type': folder_type,
		}
		req = requests.post(f'http://{server_address}/upload/image', files=file_param, data=data_param)

	return req.json()

def get_images(ws, prompt):
	prompt_id = queue_prompt(prompt)['prompt_id']
	output_images = {}
	current_node = ""
	while True:
		out = ws.recv()
		if isinstance(out, str):
			message = json.loads(out)

			with Path('message_log.log').open('a', encoding='utf8') as f:
				f.write(json.dumps(message, indent=4))
				f.write('\r\n\r\n')

			if message['type'] == 'executing':
				data = message['data']

				if data['prompt_id'] == prompt_id:
					if data['node'] is None:
						break  # Execution is done
					else:
						current_node = data['node']
		else:
			if current_node == 'save_image_websocket_node':
				images_output = output_images.get(current_node, [])
				images_output.append(out[8:])
				output_images[current_node] = images_output

	return output_images


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

isVideoFile = mimetypes.guess_type(upload_img_resp['name'])[0].startswith('video')

if isVideoFile:
	prompt['181']['inputs']['video'] = upload_img_resp['name']
	prompt['181']['inputs']['custom_width'] = 1280
	prompt['181']['inputs']['custom_height'] = 720
else:
	prompt['106']['inputs']['image'] = upload_img_resp['name']

prompt['189']['inputs']['value'] = isVideoFile

ws = websocket.WebSocket()
ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))

# prompt_id = '729cb6e1-7eb2-4410-a844-1c827a232dda'
# history = get_history(prompt_id)

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
