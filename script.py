from datetime import date
from pathlib import Path

import base64
import html
import io
import json
import pprint
import re
import time
import xml.etree.ElementTree as ET
import gradio as gr
import requests
import torch
import yaml
from PIL import Image
from jinja2 import Environment, BaseLoader, select_autoescape, Undefined
from modules.models import reload_model, unload_model

torch._C._jit_set_profiling_mode(False)

# Parameters which can be customized in settings.json (or settings.yaml) of WebUI
params = {
    'address': 'http://127.0.0.1:7860',
    'pause_photos': False,
    'manage_vram': False,
    'save_img': False,
    'positive_prompt': '',
    'negative_prompt': '',
    'width': 512,
    'height': 512,
    'size': 300,
    'denoising_strength': 0.61,
    'restore_faces': False,
    'enable_hr': False,
    'hr_upscaler': 'ESRGAN_4x',
    'hr_scale': '1.0',
    'seed': -1,
    'sampler_name': 'DDIM',
    'scheduler': 'automatic',
    'steps': 32,
    'cfg_scale': 7,
    'translations': False,
    'checkpoint_prompt': False,
    'character_tags': False,
    'prompt_template_positive': '',
    'prompt_template_negative': '',
    'debug': False
}

EXTENSION_PATH = 'extensions/sd_api_pictures_natural'

a1111Status = {
    'sd_checkpoint': '',
    'checkpoint_positive_prompt': '',
    'checkpoint_negative_prompt': ''
}
checkpoint_list = []

photo_summary = ''


def give_vram_priority(actor):
    global params

    if actor == 'SD':
        unload_model()
        print('Requesting Auto1111 to re-load last checkpoint used...')
        response = requests.post(url=f'{params["address"]}/sdapi/v1/reload-checkpoint', json='')
        response.raise_for_status()

    elif actor == 'LLM':
        print('Requesting Auto1111 to vacate VRAM...')
        response = requests.post(url=f'{params["address"]}/sdapi/v1/unload-checkpoint', json='')
        response.raise_for_status()
        reload_model()

    elif actor == 'set':
        print('VRAM management activated -- requesting Auto1111 to vacate VRAM...')
        response = requests.post(url=f'{params["address"]}/sdapi/v1/unload-checkpoint', json='')
        response.raise_for_status()

    elif actor == 'reset':
        print('VRAM management deactivated -- requesting Auto1111 to reload checkpoint...')
        response = requests.post(url=f'{params["address"]}/sdapi/v1/reload-checkpoint', json='')
        response.raise_for_status()

    else:
        raise RuntimeError(f'Managing VRAM: "{actor}" is not a known state!')

    response.raise_for_status()
    del response


if params['manage_vram']:
    give_vram_priority('set')


def load_character_data(character_name):
    if character_name != 'none':
        found_file = False
        folder1 = 'characters'
        folder2 = 'characters/instruction-following'
        for folder in [folder1, folder2]:
            for extension in ['yml', 'yaml', 'json']:
                filepath = Path(f'{folder}/{character_name}.{extension}')
                if filepath.exists():
                    found_file = True
                    break
            if found_file:
                break
        file_contents = open(filepath, 'r', encoding='utf-8').read()
        return json.loads(file_contents) if extension == 'json' else yaml.safe_load(file_contents)
    return {}


def get_sd_pictures(positive_prompt, negative_prompt, character_name):
    global params

    if params['manage_vram']:
        give_vram_priority('SD')

    payload = {
        'prompt': positive_prompt,
        'negative_prompt': negative_prompt,
        'seed': params['seed'],
        'sampler_name': params['sampler_name'],
        'scheduler': params['scheduler'],
        'enable_hr': params['enable_hr'],
        'hr_scale': params['hr_scale'],
        'hr_upscaler': params['hr_upscaler'],
        'denoising_strength': params['denoising_strength'],
        'steps': params['steps'],
        'cfg_scale': params['cfg_scale'],
        'width': params['width'],
        'height': params['height'],
        'restore_faces': params['restore_faces'],
        'override_settings_restore_afterwards': True
    }

    print(f'Prompting the image generator via the API on {params["address"]}...')
    response = requests.post(url=f'{params["address"]}/sdapi/v1/txt2img', json=payload)
    response.raise_for_status()
    r = response.json()

    visible_result = ''
    size = params['size']
    for img_str in r['images']:
        if params['save_img']:
            img_data = base64.b64decode(img_str)

            variadic = f'{date.today().strftime("%Y_%m_%d")}/{character_name}_{int(time.time())}'
            output_file = Path(f'{EXTENSION_PATH}/outputs/{variadic}.png')
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file.as_posix(), 'wb') as f:
                f.write(img_data)

            visible_result = visible_result + f'<img src="/file/{EXTENSION_PATH}/outputs/{variadic}.png" style="max-width: {size}px; max-height: {size}px; width: auto; height: auto; margin-top: 1em;">\n'
        else:
            image = Image.open(io.BytesIO(base64.b64decode(img_str.split(',', 1)[0])))
            image.thumbnail((params['size'], params['size']))
            buffered = io.BytesIO()
            image.save(buffered, format='JPEG')
            buffered.seek(0)
            image_bytes = buffered.getvalue()
            img_str = 'data:image/jpeg;base64,' + base64.b64encode(image_bytes).decode()
            visible_result = visible_result + f'<img src="{img_str}" style="max-width: {size}px; max-height: {size}px; width: auto; height: auto; margin-top: 1em;">\n'

    if params['manage_vram']:
        give_vram_priority('LLM')

    return visible_result


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ''


def data_from_template(template_string, photo_attributes):
    env = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(['html', 'xml']),
        undefined=SilentUndefined
    )
    env.filters['contains_any_phrase'] = contains_any_phrase
    template = env.from_string(template_string)
    return template.render(photo_attributes).strip()


def combine_strings(str1, str2):
    if str1 and str2:
        return str1 + ', ' + str2
    if str1:
        return str1
    if str2:
        return str2
    return ''


def parse_template_from_grammar(state, template_marker):
    result = ''

    if 'grammar_string' in state and state['grammar_string']:
        lines = state['grammar_string'].split('\n')
        found_marker = False
        for line in lines:
            if line.strip() == template_marker:
                found_marker = True
                continue
            if found_marker:
                if not line.startswith('#'):
                    break
                else:
                    if line[2:].strip():
                        result += line[2:].strip() + ' '

    return result


def contains_any_phrase(text, phrases):
    for phrase in phrases:
        pattern = r'\b' + phrase + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def simplify_xml(element):
    result = {**element.attrib}
    for child in element:
        result.setdefault(child.tag, []).append(simplify_xml(child))
    return result


def prompt_cleanup(value):
    value = value.strip()
    while value.endswith(','):
        value = value[:-1].strip()
    value = re.sub(r'\s+', ' ', value)
    return value


def parse_output(output_string, state):
    if params['debug']:
        print('\n\n*** output_string:\n' + html.unescape(output_string) + '\n\n')

    global photo_summary

    output_string_unescaped = html.unescape(output_string)

    character_name = state.get('character_menu', 'none')
    positive_suffix = ''
    negative_suffix = ''

    pattern = r'(?aims)<photo.*?>.*?</photo.*?>'

    result = ''
    remaining_text = output_string_unescaped
    while True:
        match = re.search(pattern, remaining_text)

        if not match or not match.group(0):
            result += html.escape(remaining_text)
            break

        start, end = match.start(0), match.end(0)

        try:
            photo_string = match.group(0)
            photo_element = ET.fromstring(photo_string)
        except:
            result += html.escape(remaining_text[:start]) + '[Error decoding image]'
            remaining_text = remaining_text[end:]
            continue

        photo_attributes = simplify_xml(photo_element)
        photo_attributes['_ext'] = {
            'positive_prompt': params['positive_prompt'],
            'negative_prompt': params['negative_prompt'],
            'photo_type': photo_element.tag
        }

        character_data = None
        if params['character_tags'] and character_name != 'none':
            character_data = load_character_data(character_name)
            photo_attributes['_ext']['character_name'] = character_name
            photo_attributes['_ext']['sd_character_positive_prompt'] = character_data.get('sd_character_positive_prompt', '')
            photo_attributes['_ext']['sd_character_negative_prompt'] = character_data.get('sd_character_negative_prompt', '')

        if params['debug']:
            pprint.pprint(photo_attributes)

        template = parse_template_from_grammar(state, '# sd_api_pictures_natural:')
        data = json.loads(data_from_template(template, photo_attributes))

        positive_prompt = data['positive_prompt'].strip()
        photo_summary = data['summary'].strip()
        negative_prompt = data['negative_prompt'].strip()

        if params['debug']:
            pprint.pprint(data)

        # If the user wants to add translations than iterate the translation patterns from translations.json and from the character data, adding them to positive_suffix and negative_suffix
        if params['translations']:
            translations_path = Path(f'{EXTENSION_PATH}/translations.json')
            if translations_path.exists():
                with translations_path.open('r', encoding='utf-8') as file:
                    translations_data = json.load(file)
            else:
                translations_data = {'pairs': []}
            if character_data:
                translations_data['pairs'] += character_data.get('translation_patterns', [])
            triggered_array = [0] * len(translations_data['pairs'])
            for i, word_pair in enumerate(translations_data['pairs']):
                if triggered_array[i] != 1:
                    is_descriptive_word_present = False
                    for descriptive_word in word_pair['descriptive_word']:
                        if descriptive_word.lower() in positive_prompt:
                            is_descriptive_word_present = True
                            break
                    if is_descriptive_word_present:
                        positive_suffix = combine_strings(positive_suffix, word_pair['sd_positive_translation'])
                        negative_suffix = combine_strings(negative_suffix, word_pair['sd_negative_translation'])
                        triggered_array[i] = 1

        # If the user wants to add additional tags based on the checkpoint they selected then add the tags to positive_suffix and negative_suffix
        if params['checkpoint_prompt']:
            positive_suffix = combine_strings(positive_suffix, a1111Status['sd_checkpoint_positive_prompt'])
            negative_suffix = combine_strings(negative_suffix, a1111Status['sd_checkpoint_negative_prompt'])

        final_positive_prompt = prompt_cleanup(html.unescape(combine_strings(positive_prompt, positive_suffix)))
        final_negative_prompt = prompt_cleanup(html.unescape(combine_strings(negative_prompt, negative_suffix)))

        if params['debug']:
            print('\n\n*** final_positive_prompt:\n' + html.unescape(final_positive_prompt) + '\n\n')
            print('\n\n*** final_negative_prompt:\n' + html.unescape(final_negative_prompt) + '\n\n')

        if sd_available():
            image = get_sd_pictures(final_positive_prompt, final_negative_prompt, character_name)
            result += html.escape(remaining_text[:start]) + image

        remaining_text = remaining_text[end:]

    return result if sd_available() else output_string


def grammar_loaded(state):
    return 'sd_api_pictures_natural:' in state['grammar_string'].split()


# Erase the lengthy XML describing the photo so that we don't fill context with it
def history_modifier(history):
    global photo_summary
    latest_reply = history['internal'][-1][1]
    pattern = r'(?ai)<photo.*?>.*?</photo.*?>'
    updated_reply = re.sub(pattern, f'<photo contents="{photo_summary}"/>', latest_reply)
    history['internal'][-1][1] = updated_reply
    return history


def output_modifier(text, state):
    if text == '':
        return '[Error decoding message]'

    return parse_output(text, state)


# This function might be called twice in a row, first by state_modifier and optionally a second time by input_modifier
def set_grammar_root(state, input_state):
    if not grammar_loaded(state):
        return

    grammar_root_pattern = r'root ::= .*'
    trigger_pattern = r'\*looks at ([^*]+)\*'

    grammar_root = 'root ::= sd-api-pictures-natural-response-message' if params['pause_photos'] else 'root ::= sd-api-pictures-natural-response-default'

    input_string = input_state['string'] if input_state['is_input'] else state['history']['visible'][-1][0]
    match = re.search(trigger_pattern, input_string)
    if match:
        subject = match.group(1).lower()
        character_name = state.get('name2', 'none').lower()
        if subject in [character_name, 'you']:
            subject = 'yourself'
        if input_state['is_input']:
            input_state['string'] = f'Send a photo of {subject} at this moment.'
        grammar_root = 'root ::= sd-api-pictures-natural-response-photo'

    state['grammar_string'] = re.sub(grammar_root_pattern, grammar_root, state['grammar_string'])


def state_modifier(state):
    input_state = {'is_input': False, 'string': ''}
    set_grammar_root(state, input_state)
    return state


def input_modifier(string, state, is_chat=False):
    input_state = {'is_input': True, 'string': string}
    set_grammar_root(state, input_state)
    return input_state['string']


def filter_address(address):
    address = address.strip()
    address = re.sub('/$', '', address)
    if not address.startswith('http'):
        address = 'http://' + address
    return address


def sd_api_address_update(address):
    global params

    msg = '✔️ SD API is found on:'
    address = filter_address(address)
    params.update({'address': address})
    try:
        response = requests.get(url=f'{params["address"]}/sdapi/v1/sd-models')
        response.raise_for_status()
    except:
        msg = '❌ No SD API endpoint on:'

    return gr.Textbox.update(label=msg)


def sd_available():
    params.get('address')
    try:
        response = requests.get(url=f'{params["address"]}/sdapi/v1/sd-models')
        response.raise_for_status()
        return True
    except:
        return False


def get_checkpoints():
    global a1111Status, checkpoint_list

    models = requests.get(url=f'{params["address"]}/sdapi/v1/sd-models')
    options = requests.get(url=f'{params["address"]}/sdapi/v1/options')
    options_json = options.json()
    a1111Status['sd_checkpoint'] = options_json['sd_model_checkpoint']
    checkpoint_list = [result['title'] for result in models.json()]
    return gr.update(choices=checkpoint_list, value=a1111Status['sd_checkpoint'])


def load_checkpoint(checkpoint):
    global a1111Status
    a1111Status['sd_checkpoint_positive_prompt'] = ''
    a1111Status['sd_checkpoint_negative_prompt'] = ''

    checkpoints_path = Path(f'{EXTENSION_PATH}/checkpoints.json')
    if checkpoints_path.exists():
        prompts = json.loads(open(Path(f'{EXTENSION_PATH}/checkpoints.json'), 'r', encoding='utf-8').read())
        for pair in prompts['pairs']:
            if pair['name'] == a1111Status['sd_checkpoint']:
                a1111Status['sd_checkpoint_positive_prompt'] = pair['positive_prompt']
                a1111Status['sd_checkpoint_negative_prompt'] = pair['negative_prompt']

    payload = {
        'sd_model_checkpoint': checkpoint
    }

    requests.post(url=f'{params["address"]}/sdapi/v1/options', json=payload)


def get_samplers():
    global params

    try:
        response = requests.get(url=f'{params["address"]}/sdapi/v1/samplers')
        response.raise_for_status()
        samplers = [x['name'] for x in response.json()]
    except:
        samplers = []

    return gr.update(choices=samplers)


def ui():
    with gr.Accordion('Parameters', open=True):
        with gr.Row():
            address = gr.Textbox(placeholder=params['address'], value=params['address'], label='Auto1111\'s WebUI address')
            with gr.Column(scale=1, min_width=300):
                pause_photos = gr.Checkbox(value=params['pause_photos'], label='Pause photos')
                manage_vram = gr.Checkbox(value=params['manage_vram'], label='Manage VRAM')
                save_img = gr.Checkbox(value=params['save_img'], label='Keep original images and use them in chat')
                translations = gr.Checkbox(value=params['translations'], label='Activate SD translations')
                character_tags = gr.Checkbox(value=params['character_tags'], label='Activate SD character tags')
                debug = gr.Checkbox(value=params['debug'], label='Debug')
        with gr.Row():
            checkpoint = gr.Dropdown(checkpoint_list, value=a1111Status['sd_checkpoint'], allow_custom_value=True, label='Checkpoint', type='value')
            checkpoint_prompt = gr.Checkbox(value=params['checkpoint_prompt'], label='Add checkpoint tags in prompt')
            update_checkpoints = gr.Button('Get list of checkpoints')

        with gr.Accordion('Generation parameters', open=False):
            prompt_template_positive = gr.Textbox(placeholder=params['prompt_template_positive'], value=params['prompt_template_positive'], label='Positive prompt template')
            prompt_template_negative = gr.Textbox(placeholder=params['prompt_template_negative'], value=params['prompt_template_negative'], label='Negative prompt template')
            positive_prompt = gr.Textbox(placeholder=params['positive_prompt'], value=params['positive_prompt'], label='Positive prompt')
            negative_prompt = gr.Textbox(placeholder=params['negative_prompt'], value=params['negative_prompt'], label='Negative prompt')
            with gr.Row():
                with gr.Column():
                    width = gr.Slider(64, 2048, value=params['width'], step=64, label='Width')
                    height = gr.Slider(64, 2048, value=params['height'], step=64, label='Height')
                with gr.Column():
                    with gr.Row():
                        sampler_name = gr.Dropdown(value=params['sampler_name'], allow_custom_value=True, label='Sampling method')
                        update_samplers = gr.Button('Get samplers')
                    steps = gr.Slider(1, 150, value=params['steps'], step=1, label='Sampling steps')
            with gr.Row():
                seed = gr.Number(label='Seed', value=params['seed'])
                cfg_scale = gr.Number(label='CFG Scale', value=params['cfg_scale'])
                with gr.Column() as hr_options:
                    restore_faces = gr.Checkbox(value=params['restore_faces'], label='Restore faces')
                    enable_hr = gr.Checkbox(value=params['enable_hr'], label='Hires. fix')
            with gr.Row(visible=params['enable_hr'], elem_classes='hires_opts') as hr_options:
                hr_scale = gr.Slider(1, 4, value=params['hr_scale'], step=0.1, label='Upscale by')
                denoising_strength = gr.Slider(0, 1, value=params['denoising_strength'], step=0.01, label='Denoising strength')
                hr_upscaler = gr.Textbox(placeholder=params['hr_upscaler'], value=params['hr_upscaler'], label='Upscaler')

    address.change(lambda x: params.update({'address': filter_address(x)}), address, None)
    pause_photos.change(lambda x: params.update({'pause_photos': x}), pause_photos, None)
    manage_vram.change(lambda x: params.update({'manage_vram': x}), manage_vram, None)
    manage_vram.change(lambda x: give_vram_priority('set' if x else 'reset'), inputs=manage_vram, outputs=None)
    save_img.change(lambda x: params.update({'save_img': x}), save_img, None)

    address.submit(fn=sd_api_address_update, inputs=address, outputs=address)
    prompt_template_positive.change(lambda x: params.update({'prompt_template_positive': x}), prompt_template_positive, None)
    prompt_template_negative.change(lambda x: params.update({'prompt_template_negative': x}), prompt_template_negative, None)
    positive_prompt.change(lambda x: params.update({'positive_prompt': x}), positive_prompt, None)
    negative_prompt.change(lambda x: params.update({'negative_prompt': x}), negative_prompt, None)
    width.change(lambda x: params.update({'width': x}), width, None)
    height.change(lambda x: params.update({'height': x}), height, None)
    hr_scale.change(lambda x: params.update({'hr_scale': x}), hr_scale, None)
    denoising_strength.change(lambda x: params.update({'denoising_strength': x}), denoising_strength, None)
    restore_faces.change(lambda x: params.update({'restore_faces': x}), restore_faces, None)
    hr_upscaler.change(lambda x: params.update({'hr_upscaler': x}), hr_upscaler, None)
    enable_hr.change(lambda x: params.update({'enable_hr': x}), enable_hr, None)
    enable_hr.change(lambda x: hr_options.update(visible=params['enable_hr']), enable_hr, hr_options)

    update_checkpoints.click(get_checkpoints, None, checkpoint)
    checkpoint.change(lambda x: a1111Status.update({'sd_checkpoint': x}), checkpoint, None)
    checkpoint.change(load_checkpoint, checkpoint, None)
    checkpoint_prompt.change(lambda x: params.update({'checkpoint_prompt': x}), checkpoint_prompt, None)

    translations.change(lambda x: params.update({'translations': x}), translations, None)
    character_tags.change(lambda x: params.update({'character_tags': x}), character_tags, None)
    debug.change(lambda x: params.update({'debug': x}), debug, None)

    update_samplers.click(get_samplers, None, sampler_name)
    sampler_name.change(lambda x: params.update({'sampler_name': x}), sampler_name, None)
    steps.change(lambda x: params.update({'steps': x}), steps, None)
    seed.change(lambda x: params.update({'seed': x}), seed, None)
    cfg_scale.change(lambda x: params.update({'cfg_scale': x}), cfg_scale, None)
