from sys import argv, exit, stderr
import datetime
import xml.sax

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from scipy.sparse import csr_matrix

from server import db, Article
from arxiv import ArxivCleaner
from utils import *


class ArticleParser(xml.sax.ContentHandler) :
    def __init__(self, db) :
        self.db = db
        self.content = None
        self.article = None
        self.count = 0

    def cleaned(self) :
        return self.content.replace('\n', ' ').strip()

    def startElement(self, name, attrs) :
        self.content = ""

        if name == 'article' :
            self.article = Article()

    def characters(self, c) :
        self.content += c

    def endElement(self, name) :
        if name == 'article' :
            if self.article :
                self.db.session.add(self.article)
                self.article = None
                self.count += 1

                if (self.count % 1000) == 0 :
                    print >> stderr, "\rread %d documents" % self.count,

        elif name == 'title'    : self.article.title    = self.cleaned()
        elif name == 'author'   : self.article.author   = self.cleaned()
        elif name == 'abstract' : self.article.abstract = self.cleaned()
        elif name == 'venue'    : self.article.venue    = self.cleaned()
        elif name == 'url'      : self.article.url      = self.cleaned()
        elif name == 'id'       : self.article.arxivid  = self.cleaned()
        elif name == 'created'  : self.article.date     = datetime.date(*[ int(i) for i in self.cleaned().split('-') ])
        else : pass

def create_bm25_matrix(articles, N) :
    v = CountVectorizer(min_df=10, max_df=0.5, stop_words=get_stop_words())

    print >> stderr, "running count transform on %d documents... " % N
    tf = v.fit_transform(build_corpus(articles))

    print >> stderr, "running OKAPI BM25 transform on %d documents... " % N
    
    # free parameters
    k1 = 1.2 # from [1.2, 2.0]
    b = 0.75

    D = tf.sum(axis=1)

    # TF
    tf_num = (tf * (k1 + 1))

    # make sure everything is CSR
    tf_tmp = csr_matrix(k1 * (1 - b + b * (D / D.mean())))

    # mask to ensure matrix is sparse
    tf_mask = tf.copy()
    tf_mask[tf_mask != 0] = 1
    tf_den = tf + tf_mask.multiply(tf_tmp)
        
    # avoid NaN in element-wise divide
    tf_num.sort_indices()
    tf_den.sort_indices()
    tf_num.data = np.divide(tf_num.data, tf_den.data)
    
    # IDF
    n = np.bincount(tf.nonzero()[1])
    idf_term = np.log((N - n + 0.5) / (n + 0.5))

    # bm25 should still be sparse
    bm25 = tf_num.multiply(csr_matrix(idf_term))

    print >> stderr, "syncing to disk..."
    features = v.get_feature_names()

    save_sparse_bm25(bm25)
    save_features_bm25(dict([ (y,x) for x,y in enumerate(features) ]))

def create_linrel_matrix(articles, N) :
    v = TfidfVectorizer(min_df=10, stop_words=get_stop_words(), dtype=np.float64, norm='l2')

    print >> stderr, "running TFIDF transform from %d documents..." % N

    arxiv = ArxivCleaner()
    m = v.fit_transform(arxiv.build_corpus(articles, stem=True))

    print >> stderr, "syncing to disk..."

    save_sparse_linrel(m)
    save_features_linrel(dict([ (y,x) for x,y in enumerate(v.get_feature_names()) ]))

def create_database(args) :
    print >> stderr, "creating db ..."
    db.create_all()

    parser = xml.sax.make_parser()
    parser.setContentHandler(ArticleParser(db))

    for xmlfile in args :
        print >> stderr, "reading %s ..." % (xmlfile)
        pre_count = Article.query.count()

        try :
            parser.parse(open(xmlfile))

        except xml.sax.SAXParseException, spe :
            print >> stderr, "ERROR:", str(spe)
            exit(1)

        print >> stderr, ""
        print >> stderr, "committing ..."
        db.session.commit()
        print >> stderr, "committed %d documents" % (Article.query.count() - pre_count)

def main() :
    if len(argv) == 1 :
        print >> stderr, "Usage: %s ARXIV.xml [ARXIV2.xml ...]\n" % argv[0]
        exit(1)

    create_database(argv[1:])

    articles = Article.query.all()
    n = len(articles)

    create_bm25_matrix(articles, n)
    #create_linrel_matrix(articles, n)

    print >> stderr, "done!"
    return 0

if __name__ == '__main__' :
    try :
        exit(main())
    except KeyboardInterrupt :
        print >> stderr, "Killed by User...\n"
        exit(1)

