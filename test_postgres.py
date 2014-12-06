import os
import psycopg2
import urlparse

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

#cur.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);")
#conn.commit()

cur.execute("select * from information_schema.tables where table_schema = 'public';")
print cur.fetchall()[0]
