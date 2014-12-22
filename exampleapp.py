# -*- coding: utf-8 -*-

import base64
import os
import os.path
import urllib
import hmac
import json
import hashlib
from base64 import urlsafe_b64decode, urlsafe_b64encode
import time

import requests
from flask import Flask, request, redirect, render_template, url_for,session,jsonify
from flask_oauthlib.client import OAuth, OAuthException

from test_postgres import *
from rovi import *
from s3_upload import *
from make_playlist import *
#from update_artist_sim import *

SPOTIFY_APP_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_APP_SECRET = os.environ.get('SPOTIFY_SECRET')

FB_APP_ID = os.environ.get('FACEBOOK_APP_ID')
requests = requests.session()

app_url = 'https://graph.facebook.com/{0}'.format(FB_APP_ID)
FB_APP_NAME = json.loads(requests.get(app_url).content).get('name')
FB_APP_SECRET = os.environ.get('FACEBOOK_SECRET')


def oauth_login_url(preserve_path=True, next_url=None):
    fb_login_uri = ("https://www.facebook.com/dialog/oauth"
                    "?client_id=%s&redirect_uri=%s" %
                    (app.config['FB_APP_ID'], get_home()))

    if app.config['FBAPI_SCOPE']:
        fb_login_uri += "&scope=%s" % ",".join(app.config['FBAPI_SCOPE'])
    return fb_login_uri


def simple_dict_serialisation(params):
    return "&".join(map(lambda k: "%s=%s" % (k, params[k]), params.keys()))


def base64_url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip('=')


def fbapi_get_string(path,
    domain=u'graph', params=None, access_token=None,
    encode_func=urllib.urlencode):
    """Make an API call"""

    if not params:
        params = {}
    params[u'method'] = u'GET'
    if access_token:
        params[u'access_token'] = access_token

    for k, v in params.iteritems():
        if hasattr(v, 'encode'):
            params[k] = v.encode('utf-8')

    url = u'https://' + domain + u'.facebook.com' + path
    params_encoded = encode_func(params)
    url = url + params_encoded
    result = requests.get(url).content

    return result


def fbapi_auth(code):
    params = {'client_id': app.config['FB_APP_ID'],
              'redirect_uri': get_home(),
              'client_secret': app.config['FB_APP_SECRET'],
              'code': code}

    result = fbapi_get_string(path=u"/oauth/access_token?", params=params,
                              encode_func=simple_dict_serialisation)
    pairs = result.split("&", 1)
    result_dict = {}
    for pair in pairs:
        (key, value) = pair.split("=")
        result_dict[key] = value
    return (result_dict["access_token"], result_dict["expires"])


def fbapi_get_application_access_token(id):
    token = fbapi_get_string(
        path=u"/oauth/access_token",
        params=dict(grant_type=u'client_credentials', client_id=id,
                    client_secret=app.config['FB_APP_SECRET']),
        domain=u'graph')

    token = token.split('=')[-1]
    if not str(id) in token:
        print 'Token mismatch: %s not in %s' % (id, token)
    return token


def fql(fql, token, args=None):
    if not args:
        args = {}

    args["query"], args["format"], args["access_token"] = fql, "json", token

    url = "https://api.facebook.com/method/fql.query"

    r = requests.get(url, params=args)
    return json.loads(r.content)


def fb_call(call, args=None):
    url = "https://graph.facebook.com/{0}".format(call)
    r = requests.get(url, params=args)
    return json.loads(r.content)



app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_object('conf.Config')
app.secret_key = os.environ.get('SPOTIFY_SECRET')
oauth = OAuth(app)

#for heroku-hosted
app.config.update(dict(
	  PREFERRED_URL_SCHEME = 'https'
	  ))

spotify = oauth.remote_app(
	'spotify',
	consumer_key=SPOTIFY_APP_ID,
	consumer_secret=SPOTIFY_APP_SECRET,
	# Change the scope to match whatever it us you need
	# list of scopes can be found in the url below
	# https://developer.spotify.com/web-api/using-scopes/
	request_token_params={'scope': 'playlist-modify-public playlist-modify-private'},
	base_url='https://api.spotify.com/v1',
	request_token_url=None,
	access_token_url='https://accounts.spotify.com/api/token',
	authorize_url='https://accounts.spotify.com/authorize',
	access_token_method='POST'
  )

def get_home():
    return 'https://' + request.host + '/'



def get_token():

    if request.args.get('code', None):
        return fbapi_auth(request.args.get('code'))[0]

    cookie_key = 'fbsr_{0}'.format(FB_APP_ID)

    if cookie_key in request.cookies:

        c = request.cookies.get(cookie_key)
        encoded_data = c.split('.', 2)

        sig = encoded_data[0]
        data = json.loads(urlsafe_b64decode(str(encoded_data[1]) +
            (64-len(encoded_data[1])%64)*"="))

        if not data['algorithm'].upper() == 'HMAC-SHA256':
            raise ValueError('unknown algorithm {0}'.format(data['algorithm']))

        h = hmac.new(FB_APP_SECRET, digestmod=hashlib.sha256)
        h.update(encoded_data[1])
        expected_sig = urlsafe_b64encode(h.digest()).replace('=', '')

        if sig != expected_sig:
            raise ValueError('bad signature')

        code =  data['code']

        params = {
            'client_id': FB_APP_ID,
            'client_secret': FB_APP_SECRET,
            'redirect_uri': '',
            'code': data['code']
        }

        from urlparse import parse_qs
        r = requests.get('https://graph.facebook.com/oauth/access_token', params=params)
        token = parse_qs(r.content).get('access_token')

        return token

@app.route('/_song_data', methods=['GET','POST'])
def song_data():
    	access_token = get_token()
	if not access_token:
		return json.dumps({'message': 'No Token'})
	
	songs = fb_call('me/music.listens',args={'access_token': access_token, 'limit':100})

        if "error" in songs:
                print songs["error"]
		return json.dumps({'message':'Error'})

        moreSongsURI = songs.get("paging",{}).get("next")

        list_song_dicts = songs.get("data")

        counter = 0
	song_list = []
        for entry in list_song_dicts:

                song_info = entry.get("data",{}).get("song")


                row_dict = {"fb_user_id": entry.get("from",{}).get("id"),
			    "fb_user_name": entry.get("from",{}).get("name"),
			    "publish_time": entry.get("publish_time"),
			    "songs_url": song_info.get("url"),
			    "fb_song_id": song_info.get("id"),
			    "song_name": song_info.get("title"),
			    "app_name": entry.get("application",{}).get("name")}

                print "@[fb_songs.fb_listens] " + json.dumps(row_dict)
                song_list.append(row_dict)
                counter +=1
        
	conn,cur = open_con()
	cur.executemany("""insert into fb_songs (fb_user_id,
			fb_user_name,
			publish_time,
			songs_url,
			fb_song_id,
			song_name,
			app_name) values 
			(%(fb_user_id)s,
			%(fb_user_name)s,
			%(publish_time)s,
			%(songs_url)s,
			%(fb_song_id)s,
			%(song_name)s,
			%(app_name)s)""",song_list)
	conn.commit()
	print "retrieved",counter,"songs"       
	
	artist_list = update_artist_data(access_token)
	history     = get_agg_history(song_list)	
	
	return json.dumps({'user_palate':history})


def artist_info(song_id,access_token):
	song_info = fb_call(song_id,args={'access_token': access_token})
	if "error" in song_info:
		print song_info["error"]
		return
	artist_info = song_info.get('data',{}).get('musician',[None])[0]
	artist_name = artist_info.get('name')
	artist_id = artist_info.get('id')
	artist_url = artist_info.get('url')
	return {'fb_song_id': song_id,
		'artist_name': artist_name,
		'fb_artist_id': artist_id,
		'fb_artist_url': artist_url}


def update_artist_data(access_token):
	conn,cur = open_con()
	cur.execute("""select distinct fb_song_id from fb_songs
			where fb_song_id not in (select fb_song_id 
						from unique_songs)
			order by fb_song_id""")
	new_songs = cur.fetchall()
	
	if len(new_songs) > 0:
		new_song_data = [artist_info(song[0],access_token) for song in new_songs]
		for row in new_song_data:
			print row
		cur.executemany("""insert into unique_songs (fb_song_id,
				artist_name,
				fb_artist_id,
				fb_artist_url) values 
				(%(fb_song_id)s,
				%(artist_name)s,
				%(fb_artist_id)s,
				%(fb_artist_url)s)""",new_song_data)
		conn.commit()
	else:
		new_song_data = [None]
	return new_song_data

def get_agg_history(song_list):	
	conn,cur = open_con()
	uid = song_list[0].get('fb_user_id')
	cur.execute("delete from user_palate where fb_user_id = '{}'".format(uid))
	conn.commit()

	cur.execute("""
		     insert into user_palate (fb_user_id,artist_name,fb_artist_id,listens) (
		     select a.fb_user_id,b.artist_name,b.fb_artist_id,count(*) as listens
		     from  (select distinct fb_user_id, fb_song_id, publish_time from fb_songs 
		     	group by fb_user_id, fb_song_id,publish_time) a
		     left join unique_songs b
		     on a.fb_song_id = b.fb_song_id
		     where a.fb_user_id = '{}'
		     group by a.fb_user_id,b.artist_name,b.fb_artist_id
		     order by listens desc)""".format(uid))
	conn.commit()

	
	cur.execute("""select artist_name,fb_artist_id 
		       from user_palate 
		       where fb_user_id = '{}'
		       	and fb_artist_id not in (
				select fb_artist_id from fb_rovi_sync)""".format(uid))
	sync_update = cur.fetchall()
	
	sync_pg = [get_rovi_id(row) for row in sync_update]

	cur.executemany("""insert into fb_rovi_sync (rovi_artist_id,
			artist_name,
			fb_artist_id,
			music_genres) values 
			(%(rovi_artist_id)s,
			%(artist_name)s,
			%(fb_artist_id)s,
			%(music_genres)s)""",sync_pg)
	conn.commit()


	cur.execute("""select b.rovi_artist_id from user_palate a
			left join fb_rovi_sync b
			on a.fb_artist_id = b.fb_artist_id
			where a.fb_user_id='{}'
			  and b.rovi_artist_id not in (select distinct artist1 from artist_sim)
			  and b.rovi_artist_id not in (select rovi_artist_id from downloaded_bios);""".format(uid))
	new_artists = cur.fetchall()
	
	if len(new_artists)>0:
		new_artist_ids = [{'rovi_artist_id':get_bio(rovi_id[0])} for rovi_id in new_artists]
		cur.executemany("insert into downloaded_bios (rovi_artist_id) values (%(rovi_artist_id)s)",new_artist_ids)
		conn.commit()
		#this is a big one	
		#update_artist_sim(bio_response)
	else:
		print "Bios up to date"


	conn,cur = open_con()
	cur.execute("""select b.music_genres,a.artist_name,a.listens from user_palate a
			left join fb_rovi_sync b
			on a.fb_artist_id = b.fb_artist_id
			where a.fb_user_id='{}';""".format(uid))
	history = cur.fetchall()
	history = [{'genre':row[0],'artist':row[1],'count':row[2]} for row in history]	

	return json.dumps(history)


@app.route('/_user_palate', methods=['GET','POST'])
def user_palate():

	uid = request.args.get('uid')		
	conn,cur = open_con()
	cur.execute("""select b.music_genres,a.artist_name,a.listens from user_palate a
			left join fb_rovi_sync b
			on a.fb_artist_id = b.fb_artist_id
			where a.fb_user_id='{}' and a.listens > 10 limit 40; """.format(uid))
	history = cur.fetchall()
	history = [{'genre':row[0],'artist':row[1],'count':row[2]} for row in history]	

	return json.dumps(history)

@app.route('/_generate_playlist', methods=['GET','POST'])
def palate_playlist():

	spotify_token = request.args.get('spotify_token')		
	uid = request.args.get('uid')		
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

	response = requests.post(init_playlist_url,data=json.dumps(data),headers=sptfy_header).json()
	playlist_url = response.get('href')
	playlist_uri = response.get('uri')
	
        add_track_url = playlist_url + '/tracks'
        #replace tracks. need to write a different method to append
	data = {'uris' : track_uris[0:99]}
        add_tracks_response = requests.post(add_track_url,data=json.dumps(data),headers=sptfy_header)
        print 'tracks added: ',add_tracks_response.ok
	if not add_tracks_response.ok:
		print add_tracks_response.text


        return json.dumps({'playlist_uri':playlist_uri})


def update_artist_sim(bio_response):
	
	
	return

def RateLimited(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)
    def decorate(func):
        lastTimeCalled = [0.0]
        def rateLimitedFunction(*args,**kargs):
            elapsed = time.clock() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait>0:
                time.sleep(leftToWait)
            ret = func(*args,**kargs)
            lastTimeCalled[0] = time.clock()
            return ret
        return rateLimitedFunction
    return decorate

@RateLimited(5) # n per second
def get_bio(rovi_id,params = {'country': 'US',
			      'language': 'English',
			      'format': 'json'}):
	params['nameid']   = rovi_id

	rovicall = roviAPIcall()
        bio_json = rovicall.get("name/musicbio",params=params)
	try:
		bio_dict = json.loads(bio_json)
		bio_text = bio_dict.get("musicBio",{}).get("text")
		if bio_text:
			filename = '{}_bio.txt'.format(rovi_id)	
			print s3_upload_string(bio_text,filename)
			return rovi_id
	except:
		print bio_json

		return None

@RateLimited(5) # n per second
def get_rovi_id(fb_artist_id_tuple):
	artist       =  fb_artist_id_tuple[0]
	fb_artist_id = fb_artist_id_tuple[1]
	
	params = {}
	params['country']  = "US"
	params['language'] = "English"
	params['format']   = "json"
	params['name']   = artist

	rovicall = roviAPIcall()
	jsonobj  = rovicall.get("name/info",params=params)
	try:
		dictobj  = json.loads(jsonobj)
	except:
		dictobj = {}

	data     = dictobj.get("name",{})
	rovi_artist_id = data.get("ids",{}).get("nameId")
	try:
		music_genres = data.get("musicGenres",[{}])[0].get('name')
	except:
		music_genres = None
	sync = {"fb_artist_id": fb_artist_id,
		"artist_name": artist,
		"rovi_artist_id": rovi_artist_id,
		"music_genres": music_genres}
	return sync



@app.route('/', methods=['GET', 'POST'])
def index():

    try:
	    spotify_token = get_spotify_oauth_token()
    except:
	    spotify_token = None
    access_token = get_token()
    print spotify_token
    print access_token
    channel_url = url_for('get_channel', _external=True)
    channel_url = channel_url.replace('http:', '').replace('https:', '')


    if access_token and spotify_token:
	
	me = fb_call('me', args={'access_token': access_token})
        fb_user_id = me.get('id')
	fb_app = fb_call(FB_APP_ID, args={'access_token': access_token})
        likes = fb_call('me/likes',
                        args={'access_token': access_token, 'limit': 4})
        friends = fb_call('me/friends',
                          args={'access_token': access_token, 'limit': 4})
        photos = fb_call('me/photos',
                         args={'access_token': access_token, 'limit': 16})
        
	songs = fb_call('me/music.listens',args={'access_token': access_token, 'limit':100})


	#song_list   = song_data(songs)
	
	#artist_list = update_artist_data(access_token)
	#history     = get_agg_history(song_list)	
	#recd_song   = recs(history)
	
	#recs = palate_playlist(fb_user_id,spotify_token)

	redir = get_home() + 'close/'
        POST_TO_WALL = ("https://www.facebook.com/dialog/feed?redirect_uri=%s&"
                        "display=popup&app_id=%s" % (redir, FB_APP_ID))

        app_friends = fql(
            "SELECT uid, name, is_app_user, pic_square "
            "FROM user "
            "WHERE uid IN (SELECT uid2 FROM friend WHERE uid1 = me()) AND "
            "  is_app_user = 1", access_token)

        SEND_TO = ('https://www.facebook.com/dialog/send?'
                   'redirect_uri=%s&display=popup&app_id=%s&link=%s'
                   % (redir, FB_APP_ID, get_home()))

        url = request.url

        return render_template(
            'songs.html', app_id=FB_APP_ID, token=access_token, likes=likes,
            friends=friends, photos=photos, songs=songs, app_friends=app_friends, app=fb_app,
            me=me, POST_TO_WALL=POST_TO_WALL, SEND_TO=SEND_TO, url=url,
            channel_url=channel_url, name=FB_APP_NAME,fb_user_id=fb_user_id,spotify_token=spotify_token)
    else:
        return render_template('login.html', app_id=FB_APP_ID, token=access_token, 
			url=request.url, channel_url=channel_url, name=FB_APP_NAME)

@app.route('/channel.html', methods=['GET', 'POST'])
def get_channel():
    return render_template('channel.html')


@app.route('/privacy.html', methods=['GET', 'POST'])
def privacy():
    return render_template('privacy.html')

@app.route('/callback.html', methods=['GET', 'POST'])
def callback():
    return render_template('callback.html')




@app.route('/spotify-login')
def login():
	callback = 'https://playpalate-dev.herokuapp.com/spotify-login/authorized'
	return spotify.authorize(callback=callback)

@app.route('/spotify-login/authorized')
def spotify_authorized():
	resp = spotify.authorized_response()
	if resp is None:
		return 'Access denied: reason={0} error={1}'.format(
			request.args['error_reason'],
			request.args['error_description']
			)
	if isinstance(resp, OAuthException):
		return 'Access denied: {0}'.format(resp.message)

	session['oauth_token'] = (resp['access_token'], '')

	return  redirect('/')


@spotify.tokengetter
def get_spotify_oauth_token():
	    return session.get('oauth_token')[0]

@app.route('/close', methods=['GET', 'POST'])
def close():
    return render_template('close.html')

@app.route('/home', methods=['GET', 'POST'])
def close():
    return render_template('home.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if app.config.get('FB_APP_ID') and app.config.get('FB_APP_SECRET'):
        app.run(host='0.0.0.0', port=port)
    else:
        print 'Cannot start application without Facebook App Id and Secret set'
