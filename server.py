import os
import time
from sys import stderr
from datetime import datetime

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

from utils import load_sparse_linrel, load_sparse_bm25, load_features_bm25
from informationretrieval import okapi_bm25


if __name__ == '__main__' :
    print "pre-loading matrices..."
    linrel_data = load_sparse_linrel()
    bm25_data = load_sparse_bm25()
    bm25_features = load_features_bm25()
    print "pre-loading done!"
DEFAULT_NUM_ARTICLES = 10
DYNAMIC_SUBSET = False
TUSK_DB = "tusk.db"


def db_uri() :
    global TUSK_DB
    return "sqlite:///%s/%s" % (os.getcwd(), TUSK_DB)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Article(db.Model) :
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    author      = db.Column(db.String(200), nullable=False)
    abstract    = db.Column(db.String(4000), nullable=False)
    venue       = db.Column(db.String(200), nullable=False)
    url         = db.Column(db.String(200), nullable=False)
    date        = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    arxivid     = db.Column(db.String(9), nullable=False, unique=True)

    def __repr__(self) :
        return '<Article %r>' % self.idx

    def json(self) :
        return {
            'id'        : self.id,
            'title'     : self.title,
            'author'    : self.author,
            'abstract'  : self.abstract,
            'venue'     : self.venue,
            'url'       : self.url,
            'date'      : self.date.strftime("%d/%m/%Y"),
            'arxivid'   : self.arxivid
        }

def get_documents(articles_npid) :
    articles_dbid = [ i + 1 for i in articles_npid ] # database is 1-indexed, numpy is 0-indexed
    id2article = dict([ (a.id, a) for a in Article.query.filter(Article.id.in_(articles_dbid)) ])
    return [ id2article[i] for i in articles_dbid ]

def get_top_articles_okapibm25(query, start, count) :
    global bm25_data, bm25_features, linrel_data, DYNAMIC_SUBSET
    return get_documents(okapi_bm25(query, 
                                    start, 
                                    count, 
                                    bm25_data, 
                                    bm25_features, 
                                    linrel_data, 
                                    use_subset=DYNAMIC_SUBSET))

@app.route('/search', methods=['POST'])
def textual_query() :
    post = request.get_json()
    print >> stderr, post
    return jsonify([ i.json() for i in get_top_articles_okapibm25(post.get('q'), post.get('start'), post.get('count')) ])

@app.route('/next', methods=['POST'])
def feedback_query() :
    post = request.get_json()
    print >> stderr, post

    for k,v in post.items() :
        if k not in ('q', 'start', 'count') :
            print >> stderr, "  [%s] %s" % (k,v)

    return jsonify([ i.json() for i in get_top_articles_okapibm25(post.get('q'), post.get('start'), post.get('count')) ])

@app.after_request
def after_request(response) :
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__' :
    app.run(debug=True)

