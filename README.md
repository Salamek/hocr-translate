# hocr-translate

hocr-translate is simple tool written in Python used to translate hocr files to different languages using Google Translate API
it can also generate translated pretty HTML page using Bootstrap template just set -o to file with .html extension

## Install

```bash
$ git clone git@github.com:Salamek/hocr-translate.git
$ cd hocr-translate
$ pip install -r requirements.txt
```

## Usage

```bash
$ python hocr-translate.py [-h] [-a --api-key] -i -o -l

# input.hocr is in ru language, we are translationg to en
$ python hocr-translate.py input.hocr output.hocr -l en -a google_api_key

# input.hocr is in ru language, we are translationg to en and creationg pretty HTML file
$ python hocr-translate.py input.hocr output.html -l en -a google_api_key

```

