import argparse
import os
import termcolor
import json
import xml.etree.ElementTree as ElementTree
from googleapiclient.discovery import build
import pycountry


class HocrTranslate(object):
    ifile = None
    ofile = None
    lang_to = None
    google_translate = None
    dictionary_name = 'dictionary.json'
    dictionary = {}
    dictionary_hits = 0
    google_requests = 0

    def __init__(self, ifile, ofile, lang_to, api_key=None):
        """
        Constructor
        :param ifile:
        :param ofile:
        :param lang_to:
        :param api_key:
        """
        if not os.path.isfile(ifile):
            raise IOError('Input file {} not found!'.format(ifile))

        if os.path.dirname(ofile) and not os.path.exists(os.path.dirname(ofile)):
            raise IOError('Output path {} is invalid!'.format(ofile))

        if len(lang_to) != 2:
            raise Exception('lang_to can be only 2 chracters long!')

        if not api_key:
            print(termcolor.colored('Google translate ApiKey was not set', 'red'))

        if os.path.isfile(self.dictionary_name):
            self.load_dictionary()

        self.ifile = ifile
        self.ofile = ofile
        self.lang_to = lang_to
        if api_key:
            self.google_translate = build('translate', 'v2', developerKey=api_key)

        self.process()
        self.show_stats()
        self.save_dictionary()

    @staticmethod
    def iso639_3_code_to_iso639_1_code(hocr_lang):
        """
        Trasfer iso639_3_code language code to iso639_1_code language code
        :param hocr_lang:
        :return:
        """
        found = pycountry.languages.get(iso639_3_code=hocr_lang)
        if not found:
            raise Exception('iso639_3_code {} not found'.format(hocr_lang))

        return found.iso639_1_code

    def show_stats(self):
        print(termcolor.colored('Local dictionary hits: {}'.format(self.dictionary_hits), 'green'))
        print(termcolor.colored('Google translate requests: {}'.format(self.google_requests), 'yellow'))

        if not self.dictionary_hits and not self.google_requests:
            print(termcolor.colored('Nothing was translated, something went wrong! is your Google translate API key set ?', 'red'))

    def load_dictionary(self):
        with open(self.dictionary_name) as data_file:
            self.dictionary = json.load(data_file)

    def save_dictionary(self):
        with open(self.dictionary_name, 'w') as outfile:
            json.dump(self.dictionary, outfile)

    @staticmethod
    def is_number(word):
        """
        Checks if word is number
        :param word:
        :return:
        """
        try:
            float(word.replace(',', '.'))
            return True
        except ValueError:
            return False

    @staticmethod
    def is_special_character(word):
        """
        Checks if word is special character
        :param word:
        :return:
        """
        return word in ['.', ',', '-', '/', '*', '+', '!', '@', '~', '#', '$', '%', '^', '&', '(', ')', '_', '[', ']', '{', '}', '"', '\'', ';', ':', '<', '>', '?']

    @staticmethod
    def is_translatable(word):
        """
        Checks if word is translatable
        :param word:
        :return:
        """
        if not "".join(word.split()):
            return False

        if HocrTranslate.is_number(word):
            return False

        if HocrTranslate.is_number("".join(word.split())):
            return False

        if HocrTranslate.is_special_character(word):
            return False

        if HocrTranslate.is_special_character("".join(word.split())):
            return False

        return True

    def translate_google(self, in_lan, out_lang, text):
        """
        Calls google translate service to translate text
        :param in_lan:
        :param out_lang:
        :param text:
        :return:
        """
        result = self.google_translate.translations().list(
            source=in_lan,
            target=out_lang,
            q=[text]
        ).execute()

        translated = result['translations'][0]['translatedText']

        if in_lan not in self.dictionary:
            self.dictionary[in_lan] = {}

        if out_lang not in self.dictionary[in_lan]:
            self.dictionary[in_lan][out_lang] = {}

        self.dictionary[in_lan][out_lang][text] = translated
        self.google_requests += 1
        if self.google_requests % 20 == 0:
            print(termcolor.colored('Saving 20 google requests into dictionary', 'blue'))
            self.save_dictionary()
        return translated

    def translate(self, word, lang_from=None):
        """
        Translates string by using dictionary or google translate
        :param word:
        :param lang_from:
        :return:
        """
        if not word:
            return ''

        if not HocrTranslate.is_translatable(word):
            return word

        if lang_from and lang_from in self.dictionary and self.lang_to in self.dictionary[lang_from] and word in self.dictionary[lang_from][self.lang_to]:
            self.dictionary_hits += 1
            return self.dictionary[lang_from][self.lang_to][word]

        if not self.google_translate:
            return word

        return self.translate_google(lang_from, self.lang_to, word)

    @staticmethod
    def parse_hocr_title(title):
        """
        Parses hocr title infof
        :param title:
        :return:
        """
        data = {}
        items = title.split(';')
        for item in items:
            key, value = item.strip().split(None, 1)
            data[key] = value

        return data

    def process(self):
        ElementTree.register_namespace('', "http://www.w3.org/1999/xhtml")
        xmldoc = ElementTree.parse(self.ifile)
        root = xmldoc.getroot()
        for page in root.findall('./{http://www.w3.org/1999/xhtml}body/{http://www.w3.org/1999/xhtml}div[@class="ocr_page"]'):
            for ocr_area in page.findall('./{http://www.w3.org/1999/xhtml}div[@class="ocr_carea"]'):
                for paragraph in ocr_area.findall('./{http://www.w3.org/1999/xhtml}p[@class="ocr_par"]'):
                    for line in paragraph.findall('./{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]'):
                        for word in line.findall('./{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]'):
                            word.text = self.translate(word.text, HocrTranslate.iso639_3_code_to_iso639_1_code(word.get('lang')))

        if '.hocr' in self.ofile:
            xmldoc.write(self.ofile, encoding='utf-8', xml_declaration=True, method='xml')
        elif '.html' in self.ofile:
            html = ''
            for page in root.findall('./{http://www.w3.org/1999/xhtml}body/{http://www.w3.org/1999/xhtml}div[@class="ocr_page"]'):
                page_info = HocrTranslate.parse_hocr_title(page.get('title'))
                html += '<div class="page">'
                for ocr_area in page.findall('./{http://www.w3.org/1999/xhtml}div[@class="ocr_carea"]'):
                    html += '<div class="ocr_area">'
                    for paragraph in ocr_area.findall('./{http://www.w3.org/1999/xhtml}p[@class="ocr_par"]'):
                        html += '<p class="ocr_par">'
                        for line in paragraph.findall('./{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]'):
                            line_info = HocrTranslate.parse_hocr_title(line.get('title'))
                            html += '<span class="ocr_line" style="font-size:{}px">'.format(float(line_info['x_size']) / 1.5)
                            for word in line.findall('./{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]'):
                                html += '<span class="ocrx_word">'
                                html += self.translate(word.text, HocrTranslate.iso639_3_code_to_iso639_1_code(word.get('lang')))
                                html += '</span>'
                            html += '</span><br>'
                        html += '</p>'
                    html += '</div>'
                html += '<div class="page-number text-center"><strong>-{}-</strong></div>'.format(page_info['ppageno'])
                html += '</div>'

            with open('template.html') as t:
                to_save = t.read().replace('{%LANG%}', self.lang_to).replace('{%CONTENT%}', html)
                with open(self.ofile, 'w') as outfile:
                    outfile.write(to_save)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate hOCR files from one language to another.')
    parser.add_argument('ifile', metavar='-i', help='Input file to translate')
    parser.add_argument('ofile', metavar='-o', help='Output file to store translated result')
    parser.add_argument('lang', metavar='-l', help='Output language')
    parser.add_argument('-a', metavar='--api-key', help='Google translate API key', dest='api_key')

    args = parser.parse_args()

    HocrTranslate(args.ifile, args.ofile, args.lang, args.api_key)