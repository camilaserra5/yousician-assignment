from flask import Flask, request
from flask_pymongo import PyMongo
import json, math

app = Flask(__name__)

app.config["MONGO_DBNAME"] = "yousician_db"
app.config['MONGO_URI'] = 'mongodb://localhost:27016/yousician_db'

mongo = PyMongo(app)

@app.route("/load-data")
def load_data():
    songs_column =  mongo.db.songs
    songs_column.drop()
    data_to_load = open('songs.json')
    songs_column =  mongo.db.songs
    songs_column.insert_many(json.load(data_to_load))
    data_to_load.close()
    return "Initial data loaded correctly!"

def is_number(value):
    if (value is None):
        return True
    try:
        val = int(value)
        if val >= 0:
            return True
        else:
            return False
    except ValueError:
        return False

@app.route('/songs', methods=['GET'])
def get_songs():
    page_number = request.args.get('page_number')
    n_per_page = request.args.get('n_per_page')
    songs_column = mongo.db.songs

    res = {}
    if (not is_number(page_number) or not is_number(n_per_page)):
        res["error"] = "The page number and the number per page should be numberic"
        return jsonify(res)

    res["songs"] = []
    if (page_number is not None and n_per_page is not None):
        total_pages = math.ceil(songs_column.count_documents({})/int(n_per_page))
        if (int(page_number) > total_pages):
            res["error"] = "The page number exceeds the total number of pages. Total pages: " + str(total_pages)
            return jsonify(res)
        res["page"] = page_number + "/" + str(total_pages)
        skip = (int(page_number)-1)*int(n_per_page)
        song_results = songs_column.find().skip(skip).limit(int(n_per_page))
    else:
        song_results = songs_column.find()


    for song in song_results:
        res["songs"].append({
			'artist': song['artist'],
			'title': song['title'],
			'difficulty': song['difficulty'],
			'level': song['level'],
			'released': song['released']
			})
    return jsonify(res)


@app.route('/songs/avg_difficulty', methods=['GET'])
def get_avg_difficulty():
    level = request.args.get('level')
    res = {}

    if (not is_number(level)):
        res["error"] = "Level should be a number"
        return jsonify(res)

    songs_column = mongo.db.songs
    if (level is None):
        group = [{"$group": {"_id": "_id", "avg_difficulty": {"$avg": "$difficulty"}}}]
        avg_per_level = list(songs_column.aggregate(group))
        res["avg_difficulty"] = avg_per_level[0]["avg_difficulty"];
    else:
        group = [{"$group": {"_id": "$level", "avg_difficulty": {"$avg": "$difficulty"}}}]
        avg_per_level = list(songs_column.aggregate(group))
        res["level"] = level
        res["avg_difficulty"] = 0;
        for document in avg_per_level:
            if (document["_id"] == int(level)):
                res["avg_difficulty"] = document["avg_difficulty"]
                break;

    return jsonify(res)

@app.route('/songs/search', methods=['GET'])
def search_songs():
    message = request.args.get('message')
    res = {}

    if (message is None):
        res["error"] = "message is mandatory"
        return jsonify(res)

    songs_column = mongo.db.songs
    results = songs_column.find({'$or': [
            {'artist': {'$regex': message, '$options': 'i'}},
            {'title': {'$regex': message, '$options': 'i'}}
        ]})

    songs = []
    for song in results:
        songs.append({
			'artist': song['artist'],
			'title': song['title'],
			'difficulty': song['difficulty'],
			'level': song['level'],
			'released': song['released']
			})

    if (len(songs) == 0):
      res["error"] = "No songs matched your search"
      return jsonify(res)

    res["results"] = len(songs)
    res["songs"] = songs
    return jsonify(res)

@app.route('/songs/rating', methods=['POST'])
def add_rating():
    song_id = request.values.get('song_id')
    rating = request.values.get('rating')
    res = {}

    if (song_id is None or rating is None):
        res["error"] = "song_id and rating are mandatory"
        return jsonify(res)

    if (not is_number(song_id) or not is_number(rating)):
        res["error"] = "The song id and rating should be numberic"
        return jsonify(res)

    r = range(1, 5)
    if (int(rating) not in r):
        res["error"] = "Rating should be between 1 and 5"
        return jsonify(res)

    songs_column = mongo.db.songs
    if (not songs_column.find_one({"song_id": song_id})):
        res["error"] = "The song id " + song_id + " does not exist"
        return jsonify(res)
    else:
        ratings = songs_column.find_one({"song_id": song_id})["ratings"]
        songs_column.find_one_and_update({"song_id": song_id}, {"$set": {"ratings": ratings + [rating]}})

    res["message"] = "The rating " + rating + " was added correctly to song " + song_id
    return jsonify(res)

def to_int(n):
    return int(n)

@app.route('/songs/avg_rating', methods=['GET'])
def avg_rating():
    song_id = request.args.get('song_id')
    res = {}

    if (song_id is None):
        res["error"] = "song_id is mandatory"
        return jsonify(res)

    if (not is_number(song_id)):
        res["error"] = "The song id should be numberic"
        return jsonify(res)

    songs_column = mongo.db.songs
    if (not songs_column.find_one({"song_id": song_id})):
        res["error"] = "The song id " + song_id + " does not exist"
        return jsonify(res)

    song = songs_column.find_one({"song_id": song_id})
    ratings = list(map(int, song["ratings"]))
    if (len(ratings) == 0):
        res["error"] = "There are no ratings for song id " + song_id
        return jsonify(res)

    res["avg"] = sum(ratings) / len(ratings)
    res["min"] = min(ratings, default="0")
    res["max"] = max(ratings, default="0")
    return jsonify(res)
