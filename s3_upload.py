import boto
import os

def s3_upload_string(string,filename):
	AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY')
	AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
	S3_BUCKET = os.environ.get('S3_BUCKET')

	try:
		s3 = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_KEY)
		bucket = s3.get_bucket('playpalate')
		k = boto.s3.key.Key(bucket)
		k.key = filename
		response = k.set_contents_from_string(string)
		s3.close()
		print 'Uploaded {}'.format(filename)
		return response 
	except Exception, e:
		print 'Failure to upload {}'.format(filename)
		print e
		return
def s3_open_conn():
	AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY')
	AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
	S3_BUCKET = os.environ.get('S3_BUCKET')

	try:
		s3 = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_KEY)
		bucket = s3.get_bucket('playpalate')
		k = boto.s3.key.Key(bucket)
		return k
	except Exception, e:
		print 'Failure to connect to s3'
		print e
		return

def main():
	#print s3_upload_string('this is a test to overwrite','test456.txt')
	return

if __name__ == '__main__':
	main()
	pass

