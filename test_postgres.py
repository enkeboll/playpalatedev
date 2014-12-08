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

def batch_insert(similars,increment):
	import math
	num_batches = int(math.floor(len(similars)/increment))
	last_chunk =  len(similars) % increment
	
	def insert_similars(similars):
		conn,cur = open_con()
		cur.executemany("""insert into artist_sim (artist1,artist2,score) 
						values (%(artist1)s,%(artist2)s,%(score)s)""",similars)
		conn.commit()
		return
	count = 0
	for i in range(num_batches):
		first = i*increment
		last  = first + increment -1
		insert_similars(similars[first:last])
		print 'Executed {0} out of {1} batches'.format(i,num_batches)
	insert_similars(similars[last+1:len(similars)-1])
	print last+1,len(similars)
	print count,last_chunk,len(similars)

#worked for 600k rows. didn't work for 3.6MM rows
def upload_artist_sim():
	import sys
	conn,cur = open_con()
	csvfile = open('artist_sim.csv','r')
	cur.copy_from(csvfile,'artist_sim',sep=',')
	conn.commit()
	return

def upload_s3_filnames():
	import boto
	AWS_ACCESS_KEY_ID = ''
	AWS_SECRET_KEY = ''
	s3 = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_KEY)
	bucket = s3.get_bucket('playpalate')

	rs = bucket.list()
	filenames = []
	for key in rs:
		filenames.append({'rovi_artist_id':key.name[:-8]})
	print filenames[0:10]
	conn,cur = open_con()
	cur.executemany("insert into downloaded_bios (rovi_artist_id) values (%(rovi_artist_id)s)",filenames)
	conn.commit()
	return

def main():
	return

if __name__ == '__main__':
	main()
	pass

