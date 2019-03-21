# from flask import Flask
from world_wide_city_sentiment import world_wide_city_sentiment
#
# app = Flask(__name__)
#
#
# @app.route('/')
def main():
    world_wide_city_sentiment()


if __name__ == '__main__':
    main()
