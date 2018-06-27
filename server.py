import os
import time
from sys import stderr
from datetime import datetime
import sqlite3

from flask import Flask, jsonify, request, session, escape
from flask_sqlalchemy import SQLAlchemy

from utils import load_sparse_linrel, load_sparse_bm25, load_features_bm25
from informationretrieval import okapi_bm25


if __name__ == '__main__' :
    print "pre-loading matrices..."
    linrel_data = None #load_sparse_linrel()
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
    __tablename__ = 'article'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    author      = db.Column(db.String(200), nullable=False)
    abstract    = db.Column(db.String(4000), nullable=False)
    venue       = db.Column(db.String(200), nullable=False)
    url         = db.Column(db.String(200), nullable=False)
    date        = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    arxivid     = db.Column(db.String(9), nullable=False, unique=True)

    def __repr__(self) : return '<Article %r>' % self.id

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

class User(db.Model) :
    __tablename__ = 'user'
    id          = db.Column(db.Integer, nullable=False, primary_key=True)
    name        = db.Column(db.String(200), nullable=False, unique=True)
    email       = db.Column(db.String(200), nullable=False)
    gender      = db.Column(db.String(6), nullable=False)
    age         = db.Column(db.Integer, nullable=False)
    pg_degree   = db.Column(db.String(100), nullable=False)
    ug_degree   = db.Column(db.String(100), nullable=False)
    edu_years   = db.Column(db.Integer, nullable=False)
    language    = db.Column(db.String(100), nullable=False)
    lang_years  = db.Column(db.Integer, nullable=False)
    
    sls_google  = db.Column(db.Boolean, nullable=False)
    sls_arxiv   = db.Column(db.Boolean, nullable=False)
    sls_rg      = db.Column(db.Boolean, nullable=False)
    sls_acm     = db.Column(db.Boolean, nullable=False)
    sls_other   = db.Column(db.Boolean, nullable=False)

    q1          = db.Column(db.String(30))
    q2          = db.Column(db.String(30))
    q3          = db.Column(db.String(30))
    q4          = db.Column(db.String(30))
    q5          = db.Column(db.String(30))
    q6          = db.Column(db.String(30)) 
    q7          = db.Column(db.String(30))
    q8          = db.Column(db.String(30))
    q9          = db.Column(db.String(30))
    q10         = db.Column(db.String(30))

    def __repr__(self) : return '<User %r>' % self.id

    def json(self) :
        return {
            'name'      : self.name,
            'email'     : self.email,
            'gender'    : self.gender
        }

class Experiment(db.Model) :
    __tablename__ = 'experiment'
    id          = db.Column(db.Integer, nullable=False, primary_key=True)
    search_term = db.Column(db.String(200), nullable=False)
    positive    = db.Column(db.Boolean, nullable=False)

    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user        = db.relationship('User', backref='experiments')

    q1          = db.Column(db.String(30))
    q2          = db.Column(db.String(30))
    q3          = db.Column(db.String(30))

    def __repr__(self) : 
        return '<Feedback %r>' % self.id

class Feedback(db.Model) :
    __tablename__ = 'feedback'
    id          = db.Column(db.Integer, nullable=False, primary_key=True)
    feedback    = db.Column(db.Boolean, nullable=False)

    article_id  = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    article     = db.relationship('Article', backref='feedbacks')

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'), nullable=False)
    experiment  = db.relationship('Experiment', backref='feedbacks')

    def __repr__(self) : 
        return '<Feedback %r>' % self.id


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

@app.route('/feedback', methods=['POST'])
def store_feedback() :
    post = request.get_json()
    print >> stderr, post

    if not post or [ k for k in ('q', 'name', 'type') if k not in post ] :
        return jsonify({ 'error' : 'feedback object incomplete (no query, username, search type)' }), 500

    if not post or [ k for k in ('q1', 'q2', 'q3') if k not in post ] :
        return jsonify({ 'error' : 'feedback object incomplete (mini-questionnaire incomplete)' }), 500

    experiment = Experiment()
    experiment.search_term = post.get('q')
    experiment.user = User.query.filter_by(name=post.get('name')).first()
    experiment.positive = post.get('type') == "relevant"

    db.session.add(experiment)

    for k in post :
        if k in ('q', 'name', 'type', 'q1', 'q2', 'q3') :
            continue

        print >> stderr, "  %s = %s" % (k, post.get(k))
        fb = Feedback()
        fb.article = Article.query.filter_by(arxivid=k).first()
        fb.experiment = experiment
        fb.feedback = post.get(k)

        db.session.add(fb)


    db.session.commit()

    print >> stderr, "feedback stored"
    return jsonify({}), 200

@app.route('/register', methods=['POST'])
def register_experiment() :
    post = request.get_json()
    print >> stderr, post

    if not post or [ k for k in ('name','email','gender') if k not in post ] :
        return jsonify({ 'error' : 'form incomplete' }), 500

    user = User.query.filter_by(name=post['name']).first()
    if user :
        return jsonify({ 'error' : 'user already in database (use a different username)' }), 500

    user = User()
    user.name = post.get('name')
    user.email = post.get('email') 
    user.gender = post.get('gender')
    user.age = int(post.get('age'))
    user.pg_degree = post.get('pg_degree')
    user.ug_degree = post.get('ug_degree')
    user.edu_years = post.get('edu_years')
    user.language = post.get('language')
    user.lang_years = int(post.get('lang_years'))
    user.sls_google = 'sls_google' in post
    user.sls_arxiv = 'sls_arxiv' in post
    user.sls_rg = 'sls_rg' in post
    user.sls_acm = 'sls_acm' in post
    user.sls_other = 'sls_other' in post

    try :
        db.session.add(user)
        db.session.commit()

    except sqlite3.Error, e :
        print >> stderr, str(e)
        return jsonify({ 'error' : 'database commit failed' }), 500

    return jsonify({}), 200

@app.route('/questionnaire', methods=['POST'])
def finish_experiment() :
    post = request.get_json()
    print >> stderr, post

    if not post or 'name' not in post :
        return jsonify({ 'error' : 'no specified user' }), 500

    if not post or [ k for k in ('q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10') if k not in post ] :
        return jsonify({ 'error' : 'questionnaire incomplete' }), 500

    user = User.query.filter_by(name=post['name']).first()
    if not user :
        return jsonify({ 'error' : 'user not found (searched for "%s")' % post['name'] }), 500

    #user.relevance = post.get('relevance_preference')

    user.q1 = post.get('q1')
    user.q2 = post.get('q2')
    user.q3 = post.get('q3')
    user.q4 = post.get('q4')
    user.q5 = post.get('q5')
    user.q6 = post.get('q6')
    user.q7 = post.get('q7')
    user.q8 = post.get('q8')
    user.q9 = post.get('q9')
    user.q10 = post.get('q10')

    try :
        db.session.commit()

    except sqlite3.Error, e :
        print >> stderr, str(e)
        return jsonify({ 'error' : 'database commit failed' }), 500

    return jsonify({}), 200

@app.after_request
def after_request(response) :
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__' :
    app.run(debug=True)

