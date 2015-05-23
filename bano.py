#!/usr/bin/env python3

from requests.auth import HTTPBasicAuth
from feedgen.feed import FeedGenerator
from configparser import ConfigParser
import requests
import os.path
import sys

##
# Entry point
#

def main():
    config = ConfigParser(interpolation=None)
    config.read('config.ini')

    default = config['DEFAULT']

    key = default['consumer_key']
    secret = default['consumer_secret']

    if 'bearer_token' not in default:
        default['bearer_token'] = get_bearer_token(key, secret)

    for section in config.sections():
        conf = config[section]
        if 'langs' in conf:
            generate_merged_language_feed(conf)
        else:
            generate_language_feed(conf)

    with open('config.ini', 'w') as configfile:
        config.write(configfile)


##
# Takes a dict contianing the config for one language and generates the atom
# feed for it
#

def generate_language_feed(conf):
    url = conf['url']

    feedgen = make_feedgenerator(conf)

    payload = {
        'q': conf['twitter_query'],
        'lang': conf['short'],
        'locale': conf['short'],
        'count': conf['num_entries'],
        'result_type': 'recent',
    }
    results = fetch_results(payload, conf)
    for result in results:
        status = format_status(result)
        add_status_to_feed(feedgen, status)

    filename = os.path.join(conf['output_dir'], '{}.atom.xml'.format(conf['short']))
    feedgen.atom_file(filename)


##
# Same as above, but for when a single feed should be made for more than one
# twitter API languages, like zh-tw and zh-cn being a single feed.
#

def generate_merged_language_feed(conf):
    url = conf['url']
    langs = conf['langs'].split(',')

    feedgen = make_feedgenerator(conf)

    for lang in langs:
        payload = {
            'q': conf['twitter_query'],
            'lang': lang,
            'locale': lang,
            'count': conf['num_entries'],
            'result_type': 'recent',
        }
        results = fetch_results(payload, conf)
        for result in results:
            status = format_status(result)
            add_status_to_feed(feedgen, status)

    filename = os.path.join(conf['output_dir'], '{}.atom.xml'.format(conf['short']))
    feedgen.atom_file(filename)


##
# Get the bearer token for the twitter API
#
# Arguments:
#   key:     twitter consumer key
#   secret:  twitter consumer secret
#

def get_bearer_token(key, secret):
    auth = HTTPBasicAuth(key, secret)

    url = 'https://api.twitter.com/oauth2/token'
    payload = { 'grant_type': 'client_credentials' }

    res = requests.post(url, data=payload, auth=auth)
    if res.status_code != 200:
        print('Getting bearer token failed:\n{}'.format(res.text))
        sys.exit(1)

    return res.json()['access_token']


##
# Fetch search results from the twitter search API
#
# Arguments:
#   payload:        Payload to send to the server
#   bearer_token:   Bearer token for authorization
#

def fetch_results(payload, conf):
    headers = {
        'Authorization': 'Bearer {}'.format(conf['bearer_token']),
    }

    res = requests.get(conf['url'], params=payload, headers=headers)
    if res.status_code != 200:
        print('Fetching search results failed:\n{}'.format(res.text))
        sys.exit(1)

    reply = res.json()
    return reply['statuses']


##
# Format a search status into a dict
#

def format_status(status):
    name = status['user']['name']
    user = status['user']['screen_name']
    title = '{name}  ::  @{user}'.format(name=name, user=user)

    date = status['created_at']

    id_str = status['id_str']
    url = 'https://twitter.com/{user}/status/{id}'.format(user=user, id=id_str)

    text = status['text']

    status = {
        'title': title,
        'date': date,
        'url': url,
        'text': text,
    }
    return status


##
# Make a FeedGenerator for a specific language
#

def make_feedgenerator(conf):
    feedgen = FeedGenerator()
    feedgen.title('Lojban twitter feed in {lang}'.format(lang=conf['long']))
    feedgen.description('Twitter Atom feed in {lang} about the constructed language Lojban'.format(lang=conf['long']))
    feedgen.language(conf['short'])
    feedgen.link(href='{}.atom.xml'.format(conf['short']))
    feedgen.id('{}.atom.xml'.format(conf['short']))
    feedgen.generator(generator='bano', version='0.0.0', uri='https://github.com/kyrias/bano')
    return feedgen


##
# Add a formatted twitter status to the feed generator
#

def add_status_to_feed(feedgenerator, status):
    entry = feedgenerator.add_entry()

    entry.title(status['title'])
    entry.pubdate(status['date'])

    entry.id(status['url'])
    entry.link(href=status['url'])

    entry.content(status['text'])


if __name__ == '__main__':
    main()
