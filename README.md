## Description:

TL;DR: Lets the bot answer you with a picture!

This is a different approach building on the work from the following extensions:

- https://github.com/GuizzyQC/sd_api_pictures_tag_injection.git
- https://github.com/Brawlence/SD_api_pics
- https://github.com/oobabooga/text-generation-webui

The basic idea is that we can teach the bot how to send photos so that it can send them whenever it wants.

![Screenshot 2024-05-14 at 21-17-49 Text generation web UI](https://github.com/Bryan5Alive/sd_api_pictures_natural/assets/164429111/14c3ab11-a709-41c6-bd1a-5b1b80fb8aa4)

## Installation

To install, in a command line:
- Navigate to your text-generation-webui folder
- Enter the extensions folder
- `git clone https://github.com/Bryan5Alive/grammar_sys_msg_ctx.git` (my other extension)
- `git clone https://github.com/Bryan5Alive/sd_api_pictures_natural.git` (this extension)
  
Copy the files `from sd_api_pictures_natural/grammars` to your `text-generation-webui/grammars` folder.

Enable both extensions.

## Prerequisites

Requires an instance of Automatic1111's WebUI running with an `--api` flag.

## Usage

From the "Parameters" tab in the UI find "Load grammar from file (.gbnf)" and select one of the grammars you copied from sd_api_pictures_natural/grammars (photo.gbnf or photo_simple.gbnf).

You're all set!

## Persistent settings

Create or modify the `settings.yaml` in the `text-generation-webui` root directory to override the defaults present in script.py, for example:

YAML:

```yaml
sd_api_pictures_natural-positive_prompt: ''
sd_api_pictures_natural-negative_prompt: 'worst quality, low quality'
sd_api_pictures_natural-width: 1024
sd_api_pictures_natural-height: 1024
sd_api_pictures_natural-size: 320
sd_api_pictures_natural-sampler_name: 'DPM++ SDE'
sd_api_pictures_natural-scheduler: 'karras'
sd_api_pictures_natural-steps: 6
sd_api_pictures_natural-cfg_scale: 2
sd_api_pictures_natural-restore_faces: true
sd_api_pictures_natural-translations: true
sd_api_pictures_natural-character_tags: true
```

## Troubleshooting

While this form of receiving images from bots is more natural it isn't perfect:

- Some models work better than others.
- Sometimes the bot doesn't use the format at all.
    - Try regenerating their response until they get it.
    - Try guiding the bot by saying "Send the photo" or "Try sending the photo again".
