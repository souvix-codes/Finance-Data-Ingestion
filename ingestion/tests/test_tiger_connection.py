from getpass import getpass
import psycopg2

password = getpass("Enter your working Tiger Cloud password: ")

print("Connecting...")

conn = psycopg2.connect(
    host="ebvag4avcn.t7h26cocnc.tsdb.cloud.timescale.com",
    port=31241,
    database="tsdb",
    user="tsdbadmin",
    password=password,
    sslmode="require"
)

print("Python connected successfully!")

conn.close()

print("Connection closed.")