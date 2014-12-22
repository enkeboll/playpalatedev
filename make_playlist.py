from test_postgres import *

import requests
import os
import json
import time



def palate_playlist(uid,spotify_token):
	conn,cur = open_con()
	cur.execute("""with top5_compare as (
				select meta1.artist_name as artist1, meta2.artist_name as artist2,sim.score,
				  rank() OVER (PARTITION BY artist1 ORDER BY score DESC) AS rank
				from artist_sim sim
				join fb_rovi_sync meta1
				 on sim.artist1=meta1.rovi_artist_id
				join fb_rovi_sync meta2
				 on sim.artist2=meta2.rovi_artist_id
				join 
					(select rovi_artist_id from user_palate
					join fb_rovi_sync meta3
					 on user_palate.fb_artist_id = meta3.fb_artist_id
					where user_palate.fb_user_id='{}'
					limit 5) palate
				on sim.artist1= palate.rovi_artist_id


			) select * from top5_compare
			  where rank < 5
			  ;""".format(uid))
	recs = [{"artist1name":row[0],"artist2name": row[1],"score":row[2],"rank":row[3]} for row in cur.fetchall()]
	for_spotify = [row.get('artist2name') for row in recs]
	for_spotify = list(set(for_spotify))
	
	track_uris = []
	track_uris = [get_spfy_tracks(artist) for artist in for_spotify][0]

	sptfy_header = {'Authorization': 'Bearer {}'.format(spotify_token)}
	sptfy_user_response = requests.get('https://api.spotify.com/v1/me',headers=sptfy_header)
	sptfy_user_url = sptfy_user_response.json().get('href')
	init_playlist_url = sptfy_user_url + '/playlists'
	data = {'name' : 'PlayPalate {}'.format(time.strftime("%m-%d-%Y")),
		'public' : 'false'}
	playlist_url = requests.post(init_playlist_url,data=json.dumps(data),headers=sptfy_header).json().get('href')
	
	add_track_url = playlist_url + '/tracks'
	#replace tracks. need to write a different method to append
	data = {'uris' : track_uris}	
	add_tracks_response = requests.post(add_track_url,data=json.dumps(data),headers=sptfy_header)
	print 'tracks added: ',add_tracks_response.ok	
	
	return recs


def get_spfy_tracks(artist_name,track_uris=[]):
	params={"type"  : "artist",
	        "market": "US",
		"limit" : "1"}
	base_url = "https://api.spotify.com/v1/search"
	params["q"] = artist_name
	r = requests.get(base_url,params=params)

	link = r.json().get("artists",{}).get("items",[None])[0].get("href")

	top_tracks_url = link + "/top-tracks"
	r = requests.get(top_tracks_url,params={'country':'US',"limit":"2"})
	print 'top_tracks_url response:',r.content
	response = r.json()

	for item in response.get('tracks'):
		track_uris.append('spotify:track:{}'.format(item.get('id')))

	return track_uris


def main():

	return

if __name__ == '__main__':
	main()
	pass

