import os
import psycopg2
import urlparse

def open_con():
	urlparse.uses_netloc.append("postgres")

	#url = urlparse.urlparse(os.environ["DATABASE_URL"])
	url = urlparse.urlparse('postgres://eevlzykkoizrya:3UV5kdzaj--jt21n3SFAdJbK1V@ec2-54-197-250-52.compute-1.amazonaws.com:5432/d5ermaa5dagmvt')

	conn = psycopg2.connect(
	    database=url.path[1:],
	    user=url.username,
	    password=url.password,
	    host=url.hostname,
	    port=url.port
	)

	cur = conn.cursor()
	return conn,cur

def batch_insert(doc_sim):
	import math
	num_batches = int(math.floor(len(doc_sim)/100))
	last_chunk =  num_batches % 100
	
	def chunk(doc_sim):
		conn,cur = open_con()
		
		cur.executemany("""insert into artist_sim (artist1,
				artist2,
				score) values 
				(%(artist1)s,
				%(artist2)s,
				%(score)s)""",doc_sim)
		
		conn.commit()
	count = 0
	for i in range(num_batches):
		first = i*100
		last  = first + 99 
		count += len(doc_sim[first:last])
		print first,last
	print count,last_chunk,len(doc_sim),len(doc_sim[first:last])

#worked for 600k rows. didn't work for 3.6MM rows
def upload_artist_sim():
	import sys
	conn,cur = open_con()
	csvfile = open('artist_sim.csv','r')
	cur.copy_from(csvfile,'artist_sim',sep=',')
	conn.commit()	

def main():
	

	return

if __name__ == '__main__':
	main()
	pass

