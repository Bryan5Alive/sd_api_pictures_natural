## Description:

TL;DR: Lets the bot answer you with a picture!

This is a different approach building on the work from the following extensions:
https://github.com/GuizzyQC/sd_api_pictures_tag_injection.git
https://github.com/Brawlence/SD_api_pics
https://github.com/oobabooga/text-generation-webui

The basic idea is that we can teach the bot a photo format to send via text, parse that format and send it as a prompt
to SD WebUI.

## Installation

To install, in a command line:

- Navigate to your text-generation-webui folder
- Enter the extensions folder
- `git clone https://github.com/Bryan5Alive/sd_api_pictures_natural.git`

## Usage

Load it in the `--chat-instruct` mode with `--extension sd_api_pictures_natural`.

## Prerequisites

Requires an instance of Automatic1111's WebUI running with an `--api` flag.

Mode must be `chat-instruct` and you must provide a `Custom system message` that teaches the bot to use the photo
format:

```xml

<photo description="..."/>
```

Here is a good starting point for the instructions (refine as needed):

```
Always use this template when sending any photo: <photo description="{{photoDescription}}"/>
photoDescription must visually describe the contents of the photo.
photoDescription must be terse, non-narrative, simple and objective.
Output example (change this for each photo): <photo description="an old witch wearing black, sitting in a dark forest"/>
Output must be a valid self-closing XML element called "photo" with the attribute "description".
```

These instructions work well for the few models I've experimented with (**solar-10.7b-instruct-v1.0**), but they may
need to
be tweaked depending on the model.

The XML attributes will be mapped to the strings in your `Positive prompt template` which defaults
to `{{personName}}, {{description}}`.

### Advanced bot instructions

You are not limited to the XML format and Custom system message above. **You can instruct the bot to add any attributes
you want.** They will be parsed out and injected into the `Positive prompt template` which you can customize.

For example, you could add `personClothing` to the xml and instructions above like so:

```
Always use this template when sending any photo: <photo personName="{{personName}}" personClothing="{{personClothing}}" description="{{photoDescription}}"/>
personClothing must visually describe the clothing of the person in the photo.
```

Then you can simply change `Positive prompt template` to `{{personName}}, {{personClothing}}, {{description}}`.

This is valuable for adding weights to certain aspects of the photo.

For example, you could increase the weight of the clothing description by changing `Positive prompt template`
to `{{personName}}, ({{personClothing}}:2), {{description}}`.

Note: You can completely remove the `description` attribute and replace it with other attributes, however,
the `personName` attribute is used to trigger SD Character tags (see below) so it is required if you want to use them.

### Activate SD character tags

In immersive mode, to help your character maintain a better fixed image, add sd_tags_positive and sd_tags_negative to
your character's json file to have Stable Diffusion tags that define their appearance automatically added to Stable
Diffusion prompts whenever the extension detects the character was asked to send a picture of itself, ex:

JSON:

```json
{
  "sd_tags_positive": "24 year old, asian, long blond hair, ((twintail)), blue eyes, soft skin, height 5'8, woman, <lora:shojovibe_v11:0.1>",
  "sd_tags_negative": "old, elderly, child, deformed, cross-eyed"
}
```

YAML:

```yaml
sd_tags_positive: 24 year old, asian, long blond hair, ((twintail)), blue eyes, soft skin, height 5'8, woman, <lora:shojovibe_v11:0.1>
sd_tags_negative: old, elderly, child, deformed, cross-eyed
```

The tags can also include Stable Diffusion LORAs if you have any that are relevant.

### Activate SD translations

#### General translation patterns

Whenever the Activate SD translations box is checked, the extension will load the translations.json file when a picture
is requested, and will check in both the request to the language model, as well as the response of the language model,
for specific words listed in the translations.json file and will add words or tags to the Stable Diffusion prompt
accordingly, ex:

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

If you have translations that you only want to see added for a specific character (for instance, if a specific character
has specific clothes or uniforms or physical characteristics that you only want to see triggered when specific words are
used), add the translations_patterns heading in your character's JSON or YAML file. The *translations_patterns* heading
works exactly the same way as the *pairs* heading does in the translations.json file.

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

If the "Add checkpoint tags in prompt" option is selected, if the checkpoint you loaded matches one in the
checkpoints.json file it will add the relevant tags to your prompt. The format for the checkpoints.json file is as
follow:

JSON:

```json
{
  "pairs": [
    {
      "name": "toonyou_beta3.safetensors [52768d2bc4]",
      "positive_prompt": "cartoon",
      "negative_prompt": "photograph, realistic"
    },
    {
      "name": "analogMadness_v50.safetensors [f968fc436a]",
      "positive_prompt": "photorealistic, realistic",
      "negative_prompt": "cartoon, render, anime"
    }
  ]
}
```

### Persistent settings

Create or modify the `settings.yaml` in the `text-generation-webui` root directory to override the defaults present in
script.py, ex:

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

### Troubleshooting

While this form of receiving images from bots is more fun and natural it has some challenges:

- Some models work better than others. I've had the most success with **solar-10.7b-instruct-v1.0** which is also a
  great model.
- Sometimes the bot almost gets it. They may send malformed XML or forget attributes.
    - Try regenerating their response until they get it.
    - Try guiding the bot by saying "Use the right photo format".
- Sometimes the bot doesn't use the format at all. Again, try regenerating their response until they get it.
    - Try regenerating their response until they get it.
    - Try guiding the bot by saying "Send the photo" or "Try sending the photo again".

In general, once they figure it out they consistently send photos correctly and it's really fun.