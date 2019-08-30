import os
import re
import json

_DIR = os.path.dirname(os.path.abspath(__file__))


def _read_setting() -> dict:
    filepath = os.path.join(_DIR, 'settings.json')

    if os.path.isfile(filepath):
        print('load settings', filepath)
        with open(filepath, 'r', encoding='utf-8') as fs:
            return parse_json(fs.read())

    return None

def parse_json(json_str):
    # 处理// ... /n 格式非json内容
    json_str1 = re.sub(re.compile('(//\s[\\s\\S]*?\n)'), '', json_str)
    # # 处理/*** ... */ 格式非json内容
    json_str2 = re.sub(re.compile('(/\*\*\*[\\s\\S]*?/)'), '', json_str1)

    # 返回json格式的数据
    return json.loads(json_str2)


configs = _read_setting()

if __name__ == '__main__':
    print(configs)
