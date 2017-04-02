"""
QUERY BUILDER
Hoax Analyzer
Usage: -
Example: -

hoax_analyzer.py
TW (2017) 

"""

from multiprocessing.pool import ThreadPool
from query_builder.english.feature_extractor import extract_tag, acceptible_tags as en_acceptible_tags
from query_builder.english.preprocessor import preprocess as en_preprocess, remove_stopwords as en_remove_stopwords
from query_builder.ms_text_analytics import detect_language, LANG_ID, LANG_EN, LANG_UNKNOWN
from query_builder.sklearn_classifier import classify_json_object
from subprocess import Popen, PIPE, STDOUT
import json
import re
import string
import time
import unicodedata

query_len = 14
id_acceptible_tags = ["nnp", "nn", "cdp"]

def is_query(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii','ignore').decode("ascii", "ignore")
    text = re.sub('[^0-9a-zA-Z]+', ' ', text)
    if len(text.split(" ")) > 14:
        return False
    else:
        return True

def callback_result(result):
    async_results.append(result)

def generate_query(lang, json_tag):
    query = []

    if lang == LANG_ID:
        acceptible_tags = id_acceptible_tags
    elif lang == LANG_EN:
        acceptible_tags = en_acceptible_tags

    for tag in acceptible_tags:
        tag = tag.lower()
        pred = classify_json_object(lang, tag, json_tag)
        pred = int(pred[len(pred)-1:])
        for i in range(0, pred):
            token = json_tag[tag + str(i + 1)][tag + str(i + 1) + "_token"]
            if token not in query and token != "null" and token != "u" and token != "_url_" and token not in string.punctuation:
                query.append(token)

    return " ".join(query).replace("\"", " ")

def generate_json(text):
    tag_feature = extract_tag(text)
    json_tag = {}
    for tag in en_acceptible_tags:
        i = 1
        for val in tag_feature[tag]:
            json_tag[tag.lower() + str(i)] = {}
            json_tag[tag.lower() + str(i)][tag.lower() + str(i) + "_token"] = val.token
            json_tag[tag.lower() + str(i)][tag.lower() + str(i) + "_prob"] = val.prob
            json_tag[tag.lower() + str(i)][tag.lower() + str(i) + "_wcount"] = val.w_count
            json_tag[tag.lower() + str(i)][tag.lower() + str(i) + "_kpcount"] = val.kp_count
            json_tag[tag.lower() + str(i)][tag.lower() + str(i) + "_wseq"] = val.word_pos
            json_tag[tag.lower() + str(i)][tag.lower() + str(i) + "_sseq"] = val.sentence_pos
            i += 1
    
    return json_tag

def build_query(text):
    lang = detect_language(text)

    # English Query
    if is_query(text) and lang == LANG_EN:
        query = " ".join(en_remove_stopwords(en_preprocess(text)))

    # Indonesian Query
    elif is_query(text) and lang == LANG_ID:
        p = Popen(['java', '-jar', 'lib/HoaxAnalyzer.jar', 'preprocess', text], stdout=PIPE, stderr=STDOUT)
        result = []
        for line in p.stdout:
            arr_token = line.decode("ascii", "replace").split(" ")
            for token in arr_token:
                if token not in result and token != '_url_' and len(token) > 0:
                    result.append(token)
        query = " ".join(result)

    # English Text
    elif not is_query(text) and lang == LANG_EN:
        json_data = generate_json(text)
        query = generate_query(LANG_EN, json_data)

    # Indonesian Text
    elif not is_query(text) and lang == LANG_ID:
        p = Popen(['java', '-jar', 'lib/HoaxAnalyzer.jar', 'extract', text], stdout=PIPE, stderr=STDOUT)
        result = ""
        for line in p.stdout:
            result += line.decode("ascii", "replace") + " "
        print (result)
        json_res = json.loads(result)
        query = generate_query(LANG_ID, json_res)
    elif not is_query(text):
        query = " ".join(text.split(" ")[:14])
    else:
        query = text


    # Not supported
    data = {}
    data["language"] = lang
    data["query"] = query
    
    return json.dumps(data)