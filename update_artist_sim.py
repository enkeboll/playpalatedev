import nltk
import string
import os
import time

from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.stem.porter import PorterStemmer

from sklearn.externals import joblib

from sklearn.metrics.pairwise import euclidean_distances,cosine_similarity

path = '/home/devin/bio_store'

stemmer = PorterStemmer()

def stem_tokens(tokens, stemmer):
    stemmed = []
    for item in tokens:
        stemmed.append(stemmer.stem(item))
    return stemmed

def tokenize(text):
    tokens = nltk.word_tokenize(text)
    stems = stem_tokens(tokens, stemmer)
    return stems

token_dict = {}
for subdir, dirs, files in os.walk(path):
    for file in files:
        file_path = subdir + os.path.sep + file
        bios = open(file_path, 'r')
        text = bios.read()
        lowers = text.lower()
        no_punctuation = lowers.translate(None, string.punctuation)
        token_dict[file] = no_punctuation


tfidf = TfidfVectorizer(tokenizer=tokenize, stop_words='english')
tfs = tfidf.fit_transform(token_dict.values())

vocabulary = tfidf.get_feature_names()
artistIds = [x.replace('_bio.txt','') for x,v in token_dict.iteritems()]


cos_dist = cosine_similarity(tfs)

print cos_dist
print type(cos_dist)

similars = []
for i in range(len(artistIds)):
	for j in range(len(artistIds)):
		if i != j and cos_dist[i,j]> .05:
			similars.append([artistIds[i],artistIds[j],cos_dist[i,j]])

import csv
with open('artist_sim.csv','wb') as csvfile:
	writer = csv.writer(csvfile,delimiter=',')
	writer.writerows(similars)
