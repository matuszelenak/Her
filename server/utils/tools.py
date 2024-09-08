import requests
import re

model = 'llama3.1:8b-instruct-q8_0'
get_ip_address_def = {
    'type': 'function',
    'function': {
        'name': 'get_ip_address',
        'description': 'Get the current IP address',
        'parameters': {
            'type': 'object',
            'properties': {},
            'required': [],
        },
    },
}

get_current_moon_phase_def = {
    'type': 'function',
    'function': {
        'name': 'get_current_moon_phase',
        'description': 'Get the current moon phase',
        'parameters': {
            'type': 'object',
            'properties': {},
            'required': [],
        },
    },
}


tool_call_regex = re.compile(r'\{"name": "\w+", "parameters": \{.*}}')


def get_ip_address():
    resp = requests.get('https://icanhazip.com')
    return resp.content.decode('utf-8').strip()
