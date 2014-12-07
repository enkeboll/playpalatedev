import urllib
import requests
import time
import hashlib


class roviAPIcall(object):
	api_url = 'http://api.rovicorp.com/data/v1.1'

	key = 'y4fpjsq3pnw5s6y62646ak55'
	secret = '2Yf4guB4Y8'

	def _sig(self):
		timestamp = int(time.time())
		m = hashlib.md5()
		m.update(self.key)
		m.update(self.secret)
		m.update(str(timestamp))
		return m.hexdigest()
	
	def get(self, resource, params=None):
		"""Take a dict of params, and return what we get from the api"""
		if not params:
			params = {}
		params = urllib.urlencode(params)
		sig = self._sig()
		url = "%s/%s?apikey=%s&sig=%s&%s" % (self.api_url, resource, self.key, sig, params)
		resp = requests.get(url)
		if resp.status_code != 200:
		# THROW APPROPRIATE ERROR
	        	pass
		return resp.content

def main():
	return

if __name__ == '__main__':
	main()
	pass

