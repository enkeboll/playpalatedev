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
from flask import Flask, request, redirect, render_template, url_for

from test_postgres import *
from rovi import *


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


def song_data(songs):
        if "error" in songs:
                print songs["error"]
                return

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
        return song_list

def artist_info(song_id,access_token):
	song_info = fb_call(song_id,args={'access_token': access_token})
	if "error" in song_info:
		print song_info["error"]
		return
	artist_info = song_info['data']['musician'][0]
	artist_name = artist_info['name']
	artist_id = artist_info['id']
	artist_url = artist_info['url']
	return {'fb_song_id': song_id,
		'artist_name': artist_name,
		'fb_artist_id': artist_id,
		'fb_artist_url': artist_url}


def update_artist_data(song_list,access_token):
	song_ids = [entry.get('fb_song_id') for entry in song_list]
	song_ids = list(set(song_ids))

	conn,cur = open_con()
	cur.execute("select fb_song_id from unique_songs order by fb_song_id")
	cached_songs = cur.fetchall()

	new_song_data = []
	for song in song_ids:
		if song not in cached_songs:
			new_song_data.append(artist_info(song,access_token))

	cur.executemany("""insert into unique_songs (fb_song_id,
			artist_name,
			fb_artist_id,
			fb_artist_url) values 
			(%(fb_song_id)s,
			%(artist_name)s,
			%(fb_artist_id)s,
			%(fb_artist_url)s)""",new_song_data)
	conn.commit()
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
	cur.execute("select * from user_palate where fb_user_id='{}';".format(uid))
	history = cur.fetchall()
	
	cur.execute("""select artist_name,fb_artist_id 
		       from user_palate 
		       where fb_user_id = '{}'
		       	and fb_artist_id not in (
				select fb_artist_id from fb_rovi_sync)""".format(uid))
	sync_update = cur.fetchall()
	
	#need to iterate over sync update and add rate limit throttle
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

	return history

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
	print dictobj
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
    # print get_home()


    access_token = get_token()
    channel_url = url_for('get_channel', _external=True)
    channel_url = channel_url.replace('http:', '').replace('https:', '')

    if access_token:

        me = fb_call('me', args={'access_token': access_token})
        fb_app = fb_call(FB_APP_ID, args={'access_token': access_token})
        likes = fb_call('me/likes',
                        args={'access_token': access_token, 'limit': 4})
        friends = fb_call('me/friends',
                          args={'access_token': access_token, 'limit': 4})
        photos = fb_call('me/photos',
                         args={'access_token': access_token, 'limit': 16})
        
	songs = fb_call('me/music.listens',args={'access_token': access_token, 'limit':100})
        
	song_list   = song_data(songs)
	
	artist_list = update_artist_data(song_list,access_token)
	history     = get_agg_history(song_list)	
	#recd_song   = recs(history)

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
            'index.html', app_id=FB_APP_ID, token=access_token, likes=likes,
            friends=friends, photos=photos, songs=songs, app_friends=app_friends, app=fb_app,
            me=me, POST_TO_WALL=POST_TO_WALL, SEND_TO=SEND_TO, url=url,
            channel_url=channel_url, name=FB_APP_NAME)
    else:
        return render_template('login.html', app_id=FB_APP_ID, token=access_token, url=request.url, channel_url=channel_url, name=FB_APP_NAME)

@app.route('/channel.html', methods=['GET', 'POST'])
def get_channel():
    return render_template('channel.html')


@app.route('/privacy.html', methods=['GET', 'POST'])
def privacy():
    return render_template('privacy.html')

@app.route('/close/', methods=['GET', 'POST'])
def close():
    return render_template('close.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if app.config.get('FB_APP_ID') and app.config.get('FB_APP_SECRET'):
        app.run(host='0.0.0.0', port=port)
    else:
        print 'Cannot start application without Facebook App Id and Secret set'
