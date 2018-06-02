# This file is part of PULP.
#
# PULP is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PULP is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PULP.  If not, see <http://www.gnu.org/licenses/>.
import numpy
import scipy
import os
import string
import json
from os.path import exists
from subprocess import Popen, PIPE, STDOUT

from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

#
# saving and load this big matrix of all articles
#
def save_sparse(m, prefix) :
    numpy.save(prefix + '.data.npy',     m.data)
    numpy.save(prefix + '.indices.npy',  m.indices)
    numpy.save(prefix + '.indptr.npy',   m.indptr)
    numpy.save(prefix + '.shape.npy',    m.shape)
    print "saved %s sparse matrix" % prefix

def load_sparse(prefix) :
    return scipy.sparse.csr_matrix((numpy.load(prefix + '.data.npy'), 
                                    numpy.load(prefix + '.indices.npy'), 
                                    numpy.load(prefix + '.indptr.npy')), 
                                    shape=tuple(numpy.load(prefix + '.shape.npy')))

def exists_sparse(prefix) :
    return all([ exists(prefix + i) for i in ('.data.npy','.indices.npy','.indptr.npy','.shape.npy') ])

def save_features(m, fname) :
    with open(fname, 'w') as f :
        json.dump(m, f)
    print "saved %s features" % fname

def load_features(fname) :
    with open(fname) as f :
        return json.load(f)

linrel_prefix = os.path.join(os.getcwd(), 'linrel')
linrel_features = os.path.join(os.getcwd(), 'linrel_features.json')

bm25_prefix = os.path.join(os.getcwd(), 'bm25')
bm25_features = os.path.join(os.getcwd(), 'bm25_features.json')

def save_sparse_linrel(m) :
    save_sparse(m, linrel_prefix)

def load_sparse_linrel() :
    return load_sparse(linrel_prefix)

def save_sparse_tfidf(m) :
    save_sparse(m, tfidf_prefix)

def load_sparse_tfidf() :
    return load_sparse(tfidf_prefix)

def save_features_tfidf(m) :
    save_features(m, tfidf_features)

def load_features_tfidf() :
    return load_features(tfidf_features)

def save_features_linrel(m) :
    save_features(m, linrel_features)

def load_features_linrel() :
    return load_features(linrel_features)

def save_sparse_bm25(m) :
    save_sparse(m, bm25_prefix)

def load_sparse_bm25() :
    return load_sparse(bm25_prefix)

def save_features_bm25(m) :
    save_features(m, bm25_features)

def load_features_bm25() :
    return load_features(bm25_features)

def remove_latex(s) :
    p = Popen(['detex', '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    
    out,err = p.communicate(s)

    return out

#
# corpus related functions
#
bad_chars = set(string.digits + string.punctuation)

def build_corpus(articles) :
    stemmer = SnowballStemmer('english')
    corpus = []

    for a in articles :
        s = a.title + ' ' + a.abstract
        #s = remove_latex(s)
        s = s.lower().strip()
        s = ''.join([ i if i not in bad_chars else ' ' for i in s ])

        corpus.append(' '.join([ stemmer.stem(word) for word in s.split() ]))

    return corpus

def clean_text(s) :
    return ''.join([ i if i not in bad_chars else ' ' for i in s.lower().strip() ])

def get_stop_words() :
    try :
        return stopwords.words('english')

    except LookupError :
        from nltk import download as nltk_download
        import warnings

        # christ this is verbose...
        with warnings.catch_warnings() :
            warnings.simplefilter("ignore")
            nltk_download('stopwords')
            
    return stopwords.words('english')

