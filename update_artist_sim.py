import nltk
import string
import os
import time

from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.stem.porter import PorterStemmer

from sklearn.metrics.pairwise import euclidean_distances,cosine_similarity

from test_postgres import *
from s3_upload import *


def make_token_dict(path):
	token_dict = {}
	for subdir, dirs, files in os.walk(path):
	    for file in files:
		file_path = subdir + os.path.sep + file
		bios = open(file_path, 'r')
		text = bios.read()
		lowers = text.lower()
		no_punctuation = lowers.translate(None, string.punctuation)
		token_dict[file] = no_punctuation
	return token_dict

def compute_sim(token_dict,new_songs):
	
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
	
    	tfidf = TfidfVectorizer(tokenizer=tokenize, stop_words='english')
	tfs = tfidf.fit_transform(token_dict.values())
	
	vocabulary = tfidf.get_feature_names()
	artistIds = [x for x,v in token_dict.iteritems()]

	cos_dist = cosine_similarity(tfs)
	
	new_song_values = [item.values()[0] for item in new_songs]

	similars = []
	for i in range(len(artistIds)):
		for j in range(len(artistIds)):
			if i != j and cos_dist[i,j]> .05 and (artistIds[i] in new_song_values or artistIds[j] in new_song_values):
				similars.append({'artist1' : artistIds[i],
					         'artist2': artistIds[j],
						 'score'   : cos_dist[i,j]})
	return similars

def get_missing_entries():
	conn,cur = open_con()
	cur.execute("""select rovi_artist_id from downloaded_bios 
			where rovi_artist_id not in (select distinct artist1
							from artist_sim)
			""")
	new_songs = [{'rovi_artist_id': row[0]} for row in cur.fetchall()]
	print len(new_songs)
	return new_songs

def insert_similars(similars):
	conn,cur = open_con()
	cur.executemany("""insert into artist_sim (artist1,artist2,score) 
					values (%(artist1)s,%(artist2)s,%(score)s)""",similars)
	conn.commit()
	return

def update_sim(new_songs):
	token_dict = get_token_dict()
	similars = compute_sim(token_dict,new_songs)
	batch_insert(similars,8000)
	return

def main():
	return

if __name__ == '__main__':
	main()
	pass
