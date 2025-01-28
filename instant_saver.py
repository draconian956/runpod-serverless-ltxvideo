from base64 import b64decode
from json import loads
from pathlib import Path
from pprint import pprint as echo

InstantOutputPathObj = Path('instant_runpod_output.json')
InstantOutputDict = (loads(InstantOutputPathObj.read_text(encoding='utf8'))).get('output', '')
VideoBytes = b64decode(InstantOutputDict.get('video_base64'))

Path(InstantOutputDict.get('file_indicator', {}).get('filename', '')).write_bytes(VideoBytes)
