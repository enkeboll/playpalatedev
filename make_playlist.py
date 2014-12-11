from test_postgres import *

uid = '10104488105352779'

def get_recs(uid):
	conn,cur = open_con()
	cur.execute("""select meta1.artist_name as artist1, meta2.artist_name as artist2,sim.score from artist_sim sim
			join fb_rovi_sync meta1
			on sim.artist1=meta1.rovi_artist_id
			join fb_rovi_sync meta2
			on sim.artist2=meta2.rovi_artist_id
			join 
				(select rovi_artist_id from user_palate
				join fb_rovi_sync meta3
				on user_palate.fb_artist_id = meta3.fb_artist_id
				where user_palate.fb_user_id='{}'
				limit 1) palate
			on sim.artist1= palate.rovi_artist_id
			order by sim.score desc
			limit 5;""".format(uid))
	recs = [{"artist1name":row[0],"artist2name": row[1],"score":row[2]} for row in cur.fetchall()]
	return recs

import requests
import os

def authorize_spotify():
	spotify_client_id = os.environ.get('SPOTIFY_CLIENT_ID')
	redirect_uri = 'https://fb-template-python-playpalate.herokuapp.com/'

	params={'client_id':spotify_client_id,
		'response_type':'code',
		'redirect_uri':redirect_uri,
		'scope': 'playlist-modify-private'}
	base_url = 'https://accounts.spotify.com/authorize/'
	r = requests.get(base_url,params=params)
	return r

def get_spfy_artist_id(artist_name,params={"type"  : "artist",
					   "market": "US",
					   "limit" : "1"}
				  ,base_url = "https://api.spotify.com/v1/search"):
	params["q"] = artist_name
	r = requests.get(base_url,params=params)
	link = r.json().get("artists",{}).get("items",[None])[0].get("href")
	
	top_tracks_url = link + "/top-tracks"
	r = requests.get(top_tracks_url,params={'country':'US',"limit":"5"})
	
	return r.json()

def other_queries():
	conn,cur = open_con()
	cur.execute("""select distinct b.artist_name,score from artist_sim a
			join fb_rovi_sync b
			on a.artist2=b.rovi_artist_id
			order by score desc
			limit 5;""".format(uid))
	recs = cur.fetchall()
	print recs[0:10]

	conn,cur = open_con()
	cur.execute("""select rovi_artist_id from user_palate c
			left join fb_rovi_sync d
			on c.fb_artist_id = d.fb_artist_id
			where c.fb_user_id='{}' limit 1;""".format(uid))
	recs = cur.fetchall()


	conn,cur = open_con()
	cur.execute("""select distinct artist2 from artist_sim
			where artist2 not in (select rovi_artist_id 
					      from fb_rovi_sync
					      where artist_name IS NOT NULL)""")
	rovi_ids = [row[0] for row in cur.fetchall()]
	print rovi_ids[0:10]
	return

def main():
	print get_spfy_artist_id("arcade fire")
	return

if __name__ == '__main__':
	main()
	pass

