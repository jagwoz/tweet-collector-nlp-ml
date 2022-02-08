import requests
import json
from datetime import datetime
from datetime import timedelta

def create_url(site_id, start_date, max_results):
    url = 'https://api.twitter.com/2/users/' + str(
        site_id) + '/tweets?tweet.fields=created_at,author_id,lang,context_annotations,entities&max_results=' \
          + str(max_results) + '&start_time=' + str(start_date)
    return url

class TweetCollector:
    def __init__(self, ck, cs, at, ats, bt, sub_ids, file, delay):
        self.consumer_key = ck
        self.consumer_secret = cs
        self.access_token = at
        self.access_token_secret = ats
        self.bearer_token = bt

        self.delay = delay
        self.sub_ids = sub_ids

        self.sub_keys = list(sub_ids.keys())
        self.actual_id = 0
        start_program_datetime = (datetime.utcnow() - timedelta(seconds=self.delay)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.date_times = [start_program_datetime] * len(self.sub_ids)
        self.statuses = [True] * len(self.sub_ids)

        self.filename = file
        with open(self.filename, "r") as file:
            self.tweet_db = json.load(file)
        self.db_temp = {}

    def bearer_oauth(self, r):
        r.headers["Authorization"] = f"Bearer {self.bearer_token}"
        r.headers["User-Agent"] = "v2TweetLookupPython"
        return r

    def connect_to_endpoint(self, url):
        try:
            self.statuses[self.actual_id] = True
            response = requests.request("GET", url, auth=self.bearer_oauth)
            return response.json()
        # todo specify exceptions
        except Exception as e:
            print(e)
            print("<< Connection error >>")
            self.statuses[self.actual_id] = False

    def actual_id_change(self):
        self.actual_id = self.actual_id + 1 if self.actual_id < len(self.sub_ids) - 1 else 0

    def update(self):
        json_responses = []

        url = create_url(self.sub_keys[self.actual_id], self.date_times[self.actual_id], 10)

        new_json = self.connect_to_endpoint(url)

        if new_json != {'meta': {'result_count': 0}}:
            json_responses.append(new_json)


        try:
            for i in json_responses:
                for index, j in enumerate(i['data']):
                    if index + 1 == len(i['data']):
                        self.date_times[self.actual_id] = (datetime.strptime(j['created_at'][:-5],
                                                                             "%Y-%m-%dT%H:%M:%S") +
                                                           timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
                        urls = {}
                        try:
                            for url_id, url in enumerate(j['entities']['urls']):
                                urls[f'url{url_id + 1}'] = url['expanded_url']
                        except KeyError as e:
                            print(e)
                            pass
                        new_dict = {'tweet_id': j['id'], 'author_id': j['author_id'], 'author_name': self.sub_ids[
                            self.sub_keys[self.actual_id]], 'text': str(j['text']).replace("\n", " "),
                            'publish_date': j['created_at'], 'language': j['lang'], 'urls': urls,
                            'checked': str(False)}
                        self.tweet_db[j['id']] = new_dict
                        print(f"[collector - 1 new tweet caught] [user - {self.sub_ids[self.sub_keys[self.actual_id]]}]"
                              f" [publish time - {j['created_at'][:-5]}]")

                        with open("files/queue.txt", "a+") as file_object:
                            file_object.seek(0)
                            data = file_object.read(100)
                            if len(data) > 0:
                                file_object.write("\n")
                            file_object.write(j['id'])

                with open(self.filename, "w") as file:
                    json.dump(self.tweet_db, file)
        # todo specify exceptions
        except Exception as e:
            print(e)
            self.statuses[self.actual_id] = False

        self.actual_id_change()

    def get_dates(self, index):
        return self.date_times[index]

    def get_statuses(self, index):
        return self.statuses[index]

    def get_actual_id(self):
        return self.actual_id
