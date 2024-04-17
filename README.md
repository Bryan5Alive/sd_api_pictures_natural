## Description:

TL;DR: Lets the bot answer you with a picture!

This is a different approach building on the work from the following extensions:

- https://github.com/GuizzyQC/sd_api_pictures_tag_injection.git
- https://github.com/Brawlence/SD_api_pics
- https://github.com/oobabooga/text-generation-webui

The basic idea is that we can teach the bot a photo format to send via text, parse that format and send it as a prompt to SD WebUI.

![Screenshot 2024-04-17 at 18-37-30 Text generation web UI](https://github.com/Bryan5Alive/sd_api_pictures_natural/assets/164429111/6e1300ab-78f7-4210-9b33-da0c81e8a7ad)

## Installation

To install, in a command line:
- Navigate to your text-generation-webui folder
- Enter the extensions folder
- `git clone https://github.com/Bryan5Alive/sd_api_pictures_natural.git`

**Optional but highly recommended.** Install my other extension https://github.com/Bryan5Alive/grammar_sys_msg_ctx which parses instructions from grammar files.

Copy the files `from sd_api_pictures_natural/grammars` to your `text-generation-webui/grammars` folder.

## Prerequisites

Requires an instance of Automatic1111's WebUI running with an `--api` flag.

## Usage option 1 (with grammar_sys_msg_ctx extension)
- Start WebUI with the `grammar_sys_msg_ctx` and `sd_api_pictures_natural` extensions.
- Configure your SD settings.
- From "Parameters" tab in WebUI, select a grammar that you previously copied to `text-generation-webui/grammars`.
- **Recommended.** Use `chat-instruct` mode.
- Tell the AI to send you a photo.

## Usage option 2 (only sd_api_pictures_natural extension)
- Start WebUI with the `sd_api_pictures_natural` extensions.
- Configure your SD settings.
- Manually set your `Custom system message` to instructions that will steer the bot towards the right xml format. See the grammar file under "grammar_sys_msg" for an example.
- Manually set your `Positive prompt template` from the extension settings. Again, see the grammar file under "sd_prompt_template" for an example.
- **Recommended.** Use `chat-instruct` mode.
- Tell the AI to send you a photo.

### Activate SD character tags

In immersive mode, to help your character maintain a better fixed image, add sd_tags_positive and sd_tags_negative to your character's json file to have Stable Diffusion tags that define their appearance automatically added to Stable Diffusion prompts whenever the extension detects the character was asked to send a picture of itself, ex:

JSON:

```json
{
  "sd_character_positive_prompt": "24 year old, asian, long blond hair, ((twintail)), blue eyes, soft skin, height 5'8, woman, <lora:shojovibe_v11:0.1>",
  "sd_character_negative_prompt": "old, elderly, child, deformed, cross-eyed"
}
```

YAML:

```yaml
sd_character_positive_prompt: 24 year old, asian, long blond hair, ((twintail)), blue eyes, soft skin, height 5'8, woman, <lora:shojovibe_v11:0.1>
sd_character_negative_prompt: old, elderly, child, deformed, cross-eyed
```

The tags can also include Stable Diffusion LORAs if you have any that are relevant.

### Activate SD translations

#### General translation patterns

Whenever the Activate SD translations box is checked, the extension will load the translations.json file when a picture is requested, and will check in both the request to the language model, as well as the response of the language model, for specific words listed in the translations.json file and will add words or tags to the Stable Diffusion prompt accordingly, ex:

JSON:

```json
{
  "pairs": [
    {
      "descriptive_word": [
        "tennis"
      ],
      "sd_positive_translation": "tennis ball, rackets, (net), <lora:povTennisPlaying_lora:0.5>",
      "sd_negative_translation": ""
    },
    {
      "descriptive_word": [
        "soccer",
        "football"
      ],
      "sd_positive_translation": "((soccer)), nets",
      "sd_negative_translation": ""
    }
  ]
}
```

The tags can also include Stable Diffusion LORAs if you have any that are relevant.

#### Character specific translation patterns

If you have translations that you only want to see added for a specific character (for instance, if a specific character has specific clothes or uniforms or physical characteristics that you only want to see triggered when specific words are used), add the translations_patterns heading in your character's JSON or YAML file. The *translations_patterns* heading works exactly the same way as the *pairs* heading does in the translations.json file.

JSON:

```json
{
  "translation_patterns": [
    {
      "descriptive_word": [
        "tennis"
      ],
      "sd_positive_translation": "cute frilly blue tennis uniform, <lora:frills:0.9>",
      "sd_negative_translation": ""
    },
    {
      "descriptive_word": [
        "basketball",
        "bball"
      ],
      "sd_positive_translation": "blue basketball uniform",
      "sd_negative_translation": "red uniform"
    }
  ]
}
```

YAML:

```yaml
translation_patterns:
  - descriptive_word:
      - tennis
    sd_positive_translation: "cute frilly blue tennis uniform, <lora:frills:0.9>"
    sd_negative_translation: ''
  - descriptive_word:
      - basketball
      - bball
    sd_positive_translation: "blue basketball uniform"
    sd_negative_translation: "red uniform"
```

Note: Character specific translation patterns stack with the general translation patterns.

### Checkpoint file Stable Diffusion tags

If the "Add checkpoint tags in prompt" option is selected, if the checkpoint you loaded matches one in the checkpoints.json file it will add the relevant tags to your prompt. The format for the checkpoints.json file is as follow:

JSON:

```json
{
  "pairs": [
    {
      "name": "toonyou_beta3.safetensors [52768d2bc4]",
      "sd_checkpoint_positive_prompt": "cartoon",
      "sd_checkpoint_negative_prompt": "photograph, realistic"
    },
    {
      "name": "analogMadness_v50.safetensors [f968fc436a]",
      "sd_checkpoint_positive_prompt": "photorealistic, realistic",
      "sd_checkpoint_negative_prompt": "cartoon, render, anime"
    }
  ]
}
```

## Persistent settings

Create or modify the `settings.yaml` in the `text-generation-webui` root directory to override the defaults present in script.py, ex:

YAML:

```yaml
sd_api_pictures_natural-width: 1024
sd_api_pictures_natural-height: 1024
sd_api_pictures_natural-sampler_name: DPM++ SDE Karras
sd_api_pictures_natural-steps: 6
sd_api_pictures_natural-cfg_scale: 2
sd_api_pictures_natural-translations: true
sd_api_pictures_natural-character_tags: true
```

## Troubleshooting

While this form of receiving images from bots is more natural it has some challenges:

- Some models work better than others. I've had the most success with **solar-10.7b-instruct-v1.0** which is also a
  great model.
- Sometimes the bot doesn't use the format at all.
    - Try regenerating their response until they get it.
    - Try guiding the bot by saying "Send the photo" or "Try sending the photo again".

In general, once they figure it out they consistently send photos correctly.

## Advanced
You can create or modify the grammar files to have additional attributes. These will be parsed from the bot's output and available to inject into the prompt template.

For example starting with:
```
photo-xml ::= "<photo detailed_visual_transcription_of_photo_contents=\"" value "\"/>"
```
And prompt template `{{detailed_visual_transcription_of_photo_contents}}`.

You could add the time of day of the photo like so:
```
photo-xml ::= "<photo time_of_day_taken=\" value "\" detailed_visual_transcription_of_photo_contents=\"" value "\"/>"
```
And prompt template `{{detailed_visual_transcription_of_photo_contents}} taken at {{time_of_day_taken}}`.

The prompt template is a Jinja2 template, so you can use additional template syntax to make more complex prompts.
