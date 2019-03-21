import json
import time
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import datetime

import folium
import matplotlib
import matplotlib as mpl
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy
import pandas as pd
import tweepy
from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from matplotlib.pyplot import figure, show
from model.city import City
from model.tweet import Tweet
from resources.color_gradient import color
from resources.credentials import *
from textblob import TextBlob

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)


def world_wide_city_sentiment():
    # first run (requires getting geo location for each city)
    # =======================================================
    # city_dict = load_cities()
    # cities = create_city_collection(city_dict)
    # write_city_data_to_file(cities)

    # subsequent runs (load geo location from file)
    # =============================================
    cities = load_city_collection()
    cities_data_frame = convert_list_to_data_frame(cities)

    while True:
        for city in cities:
            try:
                tweets = query_twitter_for_tweets(city.location)
                current_average_score = get_score(tweets)
                update_city_score(city, current_average_score)
                update_score_trend(city)
                print(city.name + ": " +
                      datetime.now().strftime("%Y-%m-%d-%H-%M") + ": " +
                      str(float(city.score_trend)))
                cities_data_frame = convert_list_to_data_frame(cities)
                update_map(cities_data_frame)
                time.sleep(60)
            except:
                print(datetime.now().strftime(
                    "%Y-%m-%d-%H-%M") + ": There was a problem fetching data from Twitter for: " + city.name)


def convert_list_to_data_frame(cities):
    names = []
    lon = []
    lat = []
    score = []
    for city in cities:
        names.append(city.name)
        lon.append(float((str(city.location).split(",")[0])))
        lat.append(float((str(city.location).split(",")[1])))
        score.append(city.score_trend)
    zippedList = list(zip(names, lon, lat, score))
    cities_data_frame = pd.DataFrame(zippedList, columns=['name', 'lon', 'lat', 'score'])
    # print(cities_data_frame)
    return cities_data_frame


# https://maps.googleapis.com/maps/api/geocode/json?address=1600+Amphitheatre+Parkway,+Mountain+View,+CA&key=YOUR_API_KEY
def fetch_geocode(city):
    try:
        data = {}
        data['address'] = city
        url_values = urllib.parse.urlencode(data)
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        full_url = url + '?' + url_values + '&key=' + apiKey
        data = urllib.request.urlopen(full_url)
        response = json.load(data)
        latitude = response['results'][0]['geometry']['location']['lat']
        longitude = response['results'][0]['geometry']['location']['lng']
        radiusInKm = 20
        geocode = str(float(latitude)) + ',' + str(float(longitude)) + ',' + str(float(radiusInKm)) + 'km'
    except:
        geocode = str(float(0.0)) + ',' + str(float(0.0)) + ',' + str(float(radiusInKm)) + 'km'
    return geocode


# initial run
def load_cities():
    with open('resources/Cities.json', 'r', encoding="utf8") as cities_from_json:
        # with open('resources/smallCities.json', 'r', encoding="utf8") as cities_from_json:
        # with open('resources/interestingCities.json', 'r', encoding="utf8") as cities_from_json:
        city_dict = json.load(cities_from_json)
    return city_dict


def create_city_collection(city_dict):
    cities = set()
    for city in city_dict:
        geo_code = fetch_geocode(city['name'])
        new_city = City(city['name'], geo_code)
        cities.add(new_city)
        # print(new_city)
    return cities


# subsequent runs
def load_city_collection():
    cities = set()

    try:
        file_object = open('resources/interestingCitiesWithGeoLocation.json', 'r', encoding="utf8")
        # file_object = open('resources/citiesWithGeoLocation.json', 'r', encoding="utf8")
        # file_object = open('resources/smallCitiesWithGeoLocation.json', 'r', encoding="utf8")
        cities_from_json = json.load(file_object)
        # print(cities_from_json)
        for city_from_json in cities_from_json:
            city = City(city_from_json['name'], city_from_json['location'])
            cities.add(city)
    except FileNotFoundError:
        print(file_object + " not found. ")
    return cities


def write_city_data_to_file(cities):
    city_list = []
    for city in cities:
        city_list.append(city.__dict__)
    try:
        file_object = open('resources/interestingCitiesWithGeoLocation.json', 'w')
        json.dump(city_list, file_object)

    except FileNotFoundError:
        print(file_object + " not found. ")


def query_twitter_for_tweets(geo_code):
    tweets = set()
    for tweet in tweepy.Cursor(api.search, q="*", geocode=geo_code, lang="en").items(50):
        # for tweet in tweepy.Cursor(api.search, q="*", count=100, geocode=geo_code, lang="en").items(100):
        tweet_id = tweet.id
        tweet_date = datetime.strptime(str(tweet.created_at)[:10], '%Y-%m-%d').strftime('%d-%m-%Y')
        tweet_text = tweet.text
        tweet_score = round(TextBlob(tweet_text).sentiment.polarity, 4)

        new_tweet = Tweet(tweet_id, tweet_date, tweet_text, tweet_score)
        tweets.add(new_tweet)

    return tweets


def get_score(tweets):
    sum = 0
    for tweet in tweets:
        sum = sum + tweet.score
    return sum / len(tweets)


def update_city_score(city, current_average_score):
    if len(city.score_list) > 4:
        city.score_list = city.score_list[1:]
    city.score_list.append(current_average_score)


def update_score_trend(city):
    try:
        length = len(city.score_list)
        cum_sum = numpy.cumsum(city.score_list, dtype=float)
        cum_sum[length:] = cum_sum[length:] - cum_sum[:-length]
        city.score_trend = cum_sum[length - 1:] / length
    except:
        city.score_trend = numpy.average(city.score_list)


def update_map(cities_data_frame):
    # Make an empty map
    m = folium.Map(location=[20, 0], tiles="Mapbox Bright", zoom_start=2)
    for i in range(0, len(cities_data_frame)):
        circle_color = get_color(cities_data_frame.iloc[i]['score'])
        radius = get_radius(abs(cities_data_frame.iloc[i]['score']))
        popup = str(cities_data_frame.iloc[i]['name']) + ' ' + str(cities_data_frame.iloc[i]['score'])
        folium.CircleMarker(
            location=[cities_data_frame.iloc[i]['lon'], cities_data_frame.iloc[i]['lat']],
            popup=popup,
            radius=radius,
            color=circle_color,
            fill=True,
            fill_color=circle_color
        ).add_to(m)

    # Save it as html
    m.save('mymap_' + datetime.now().strftime("%Y-%m-%d-%H-%M") + '.html')
    print(datetime.now().strftime("%Y-%m-%d-%H-%M") + ' *** Map generated ***')


def get_color(score):
    # if score < -0.1:
    #     # red
    #     color_val = color[0]
    # elif score > 0.1:
    #     # green
    #     color_val = color[2]
    # else:
    #     # yellow
    #     color_val = color[1]
    # return color_val
    if score < -0.9:
        color_val = color[0]
    elif score < -0.8:
        color_val = color[1]
    elif score < -0.7:
        color_val = color[2]
    elif score < -0.6:
        color_val = color[3]
    elif score < -0.5:
        color_val = color[4]
    elif score < -0.4:
        color_val = color[5]
    elif score < -0.3:
        color_val = color[6]
    elif score < -0.2:
        color_val = color[7]
    elif score < -0.1:
        color_val = color[8]
    elif score < 0.0:
        color_val = color[9]
    elif score == 0.0:
        color_val = color[10]
    elif score < 0.1:
        color_val = color[11]
    elif score < 0.2:
        color_val = color[12]
    elif score < 0.3:
        color_val = color[13]
    elif score < 0.4:
        color_val = color[14]
    elif score < 0.5:
        color_val = color[15]
    elif score < 0.6:
        color_val = color[16]
    elif score < 0.7:
        color_val = color[17]
    elif score < 0.8:
        color_val = color[18]
    elif score < 0.9:
        color_val = color[19]
    else:
        color_val = color[20]
    return color_val


def get_radius(score):
    if score < 0.12:
        radius = 10
    else:
        radius = int(score * 80)
    return radius
