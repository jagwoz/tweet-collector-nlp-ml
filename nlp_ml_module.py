import urllib
import googletrans
import requests
import json
import spacy
import pandas as pd
from kafka import KafkaProducer
from googletrans import Translator
from datetime import datetime
from datetime import timedelta
from urllib.request import urlopen
from bs4 import BeautifulSoup
from sklearn.tree import DecisionTreeClassifier


def create_url(site_id, start_date):
    end_date = (datetime.strptime(start_date[:-5], "%Y-%m-%dT%H:%M:%S") +
                timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _url = 'https://api.twitter.com/2/users/' + str(
        site_id) + '/tweets?tweet.fields=created_at,public_metrics&max_results=' + str(5) + '&start_time=' + str(
        start_date) + '&end_time=' + str(end_date)
    return _url


def bearer_oauth(r):
    r.headers[
        "Authorization"] = f"Bearer {' add bearer token '}"
    r.headers["User-Agent"] = "v2TweetLookupPython"
    return r


def connect_to_endpoint(_url):
    try:
        response = requests.request("GET", _url, auth=bearer_oauth)
        return response.json()
    # todo specify exceptions
    except Exception as exception:
        print(exception)
        print("<< Connection error >>")


def text_from_website(_url):
    to_return = ""
    html = urllib.request.urlopen(_url)
    html_parse = BeautifulSoup(html, 'html.parser')
    for para in html_parse.find_all("p"):
        to_return += para.get_text()
    return to_return


if __name__ == "__main__":

    nlp = spacy.load("en_core_web_sm")

    try:  # kafka connection
        producer = KafkaProducer(bootstrap_servers=' add ip : add port ',
                                 value_serializer=lambda param: json.dumps(param).encode('utf-8'))
    # todo specify exceptions
    except Exception as e:
        print(e)
        print("<< Application started without available kafka broker >>")

    translator = Translator()  # google translator

    vocab = {
        # "tag" : ["words", "qualifying", "for", "the", "tag"]
        "vulnerability": ["vulnerability", "susceptibility"],
        "weakness": ["weakness", "frailty", "fragility"]
    }

    index_check = 0
    index_stats = 0
    while True:
        try:
            queue = open('files/queue.txt', 'r')
            all_ids = queue.readlines()

            with open('files/tweet_db.json') as file:
                db = json.load(file)
            keys = list(db.keys())

            if index_check < len(all_ids):
                index = all_ids[index_check].replace("\n", '')
                if db[index]['checked'] == "False":
                    print("============================== nlp ==============================")  # nlp module start
                    if db[index]['language'] in googletrans.LANGUAGES:  # tweet translate
                        english_text = translator.translate(db[index]['text'], src=db[index]['language'])
                    else:
                        english_text = translator.translate(db[index]['text'])

                    corpus = english_text.text + " "  # corpus build

                    for url in db[index]['urls']:
                        print(db[index]['urls'][url])
                        try:
                            txt = text_from_website(db[index]['urls'][url])
                            try:
                                eng_txt = translator.translate(txt).text
                                corpus += eng_txt
                            except TypeError as e:
                                print(e)
                        except urllib.error.HTTPError as e:
                            print(e)

                    l = " ".join(token.lemma_.lower() for token in nlp(corpus) if
                                 token.lemma_.lower() not in nlp.Defaults.stop_words
                                 and token.is_alpha and not token.is_stop)
                    words_list = l.split()
                    print(words_list)

                    tags = []
                    for word in words_list:
                        for v in vocab:
                            if word in vocab[v]:
                                tags.append(v)

                    db[index]['text'] = english_text.text
                    db[index]['tags'] = tags
                    db[index]['checked'] = "True"
                    with open("files/tweet_db.json", "w") as file:
                        json.dump(db, file)

                    print("=================================================================")  # nlp module end

                    try:  # send json to kafka on topic 'tweets'
                        producer.send('tweets', value=db)
                    except Exception as e:
                        print(e)
                    index_check += 1
                else:
                    index_check += 1

            if index_stats < len(all_ids):
                index = all_ids[index_stats].replace("\n", '')
                keys = list(db[index].keys())
                if not keys.__contains__('public_metrics') and datetime.utcnow() - \
                        datetime.strptime(db[index]['publish_date'][:-5],
                                          "%Y-%m-%dT%H:%M:%S") > timedelta(seconds=30):
                    # seconds=30 to test, it is best to collect statistics e.g. after 20 minutes (1200 sec)
                    print("============================== ml ==============================")  # ml module start

                    json_responses = []
                    url = create_url(db[index]['author_id'], db[index]['publish_date'])
                    new_json = connect_to_endpoint(url)
                    if new_json != {'meta': {'result_count': 0}}:
                        json_responses.append(new_json)

                    try:
                        for i in json_responses:
                            for index_j, j in enumerate(i['data']):
                                if index_j == 0:
                                    db[index]['public_metrics'] = j['public_metrics']
                                    with open("files/tweet_db.json", "w") as file:
                                        json.dump(db, file)
                    # todo specify exceptions
                    except Exception as e:
                        print(e)

                    try:
                        # decision tree classifier
                        df = pd.read_csv('files/train.csv', sep=";")

                        df = df[df['user_id'] == int(db[index]['author_id'])]

                        X = df[['retweet_count', 'reply_count', 'like_count', 'quote_count']].values.tolist()
                        Y = df['hot'].values.tolist()
                        C = DecisionTreeClassifier()
                        C.fit(X, Y)

                        to_predict = [
                            [db[index]['public_metrics']['retweet_count'], db[index]['public_metrics']['reply_count'],
                             db[index]['public_metrics']['like_count'], db[index]['public_metrics']['quote_count']]]
                        hot = C.predict(to_predict)[0]
                        print(hot)

                        if hot == 1:
                            try:  # send json to kafka on topic 'hot_tweets'
                                producer.send('hot_tweets', value=db)
                            except Exception as e:
                                print(e)
                    except ValueError:
                        print("No data to classifier")

                    print("================================================================")  # ml module end
                    index_stats += 1
                else:
                    pass

        except KeyError as e:
            print(e)
        except json.decoder.JSONDecodeError as e:
            print(e)
