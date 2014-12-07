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
'''
cur.execute("""CREATE TABLE fb_songs (id serial PRIMARY KEY,  
		fb_user_id integer, 
		fb_user_name varchar, 
		publish_time timestamp, 
		songs_url varchar, 
		fb_song_id int, 
		song_name varchar,
		app_name varchar);""")
conn.commit()
'''


#cur.execute("insert into fb_songs (jsondata) values (%s)",
#		    [Json(row_dict)])
#cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)",(100, "abc'def"))
#conn.commit()


#cur.execute("select * from information_schema.tables where table_schema='public'")

#print cur.fetchall()
def main():
	#conn,cur = open_con()
	#cur.execute("select fb_song_id from lu_fb_song_artist")
	#songs = cur.fetchall()
	#print songs
	return

if __name__ == '__main__':
	main()
	pass

