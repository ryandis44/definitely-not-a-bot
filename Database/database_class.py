
import os
import time
import asyncio
import aiomysql
import dns.resolver
import mysql.connector as mariadb
from dotenv import load_dotenv
load_dotenv()


resolve = dns.resolver.query(os.getenv('REMOTE_DOMAIN'), 'A')
ip = None
for ipval in resolve:
    ip = ipval.to_text()

pool = None
async def connect_pool():
    global pool

    try:
        print("\n\nAttempting local database pool connection...")
        if os.getenv('CONNECTION') == "REMOTE": raise Exception
        pool = await aiomysql.create_pool(
                host='192.168.0.12',
                port=3306,
                connect_timeout=2,
                user=os.getenv('DATABASE_USERNAME'),
                password=os.getenv('DATABASE_PASSWORD'),
                db=os.getenv('DATABASE'),
                loop=asyncio.get_event_loop(),
                autocommit=True
        )
        print("Database pool connected locally!\n")
    except Exception as e:
        print(f"Database server not running locally, attempting database pool connection via Cloudflare...")
        try:
            pool = await aiomysql.create_pool(
                    host=ip,
                    port=3306,
                    user=os.getenv('DATABASE_USERNAME'),
                    password=os.getenv('DATABASE_PASSWORD'),
                    db=os.getenv('DATABASE'),
                    loop=asyncio.get_event_loop(),
                    autocommit=True
            )
            # conn = await pool.acquire()
            # cursor = await conn.cursor()
            print("Database pool connected via Cloudflare!\n")
        except:
            print(f"\n##### FAILED TO CONNECT TO DATABASE! #####\n{e}\n")

async def check_pool():
    global pool
    if pool is None:
        await connect_pool()
    if pool.closed:
        print(f"\n\n####### DATABASE POOL CONNECTION LOST! Attempting to reconnect... #######")
        await connect_pool()

        
class AsyncDatabase:

    def __init__(self, file):
        global pool
        self.file = file
        self.pool = pool

    def __update_vars(self):
        global pool
        self.pool = pool

    async def execute(self, exec_cmd: str):
        for attempt in range(1,6):
            try:
                async with self.pool.acquire() as conn:
                    cursor = await conn.cursor()
                    await cursor.execute(exec_cmd)
            except Exception as e:
                if attempt < 5:
                    if os.getenv('DATABASE_DEBUG') != "1": await asyncio.sleep(5)
                    await check_pool()
                    self.__update_vars()
                    continue
                else:
                    print(f"\nASYNC DATABASE ERROR! [{self.file}] Could not execute: \"{exec_cmd}\"\n{e}")
            break
        
        if exec_cmd.startswith("SELECT"):
            val = await cursor.fetchall()
            if len(val) == 1:
                if len(val[0]) == 1:
                    return val[0][0]
            return val if val != () else [] # easier migration from old synchronous code
        return
    
    def exists(self, rows):
        return rows > 0

















db = None
cur = None
conn = None


def dbclass_connect():
    global db
    global cur
    global ip

    # Prefer local database connection. Fallback to external Cloudflare
    # connection if local connection is not possible.
    load_dotenv() # Refresh values from .env file (if they changed)
    try:
        if os.getenv('CONNECTION') == "REMOTE": raise mariadb.Error
        print("\n\nAttempting local database connection...")
        db = mariadb.connect(
            user=os.getenv('DATABASE_USERNAME'),
            password=os.getenv('DATABASE_PASSWORD'),
            host='192.168.0.12',
            connect_timeout=2, # Only try for 2 seconds to connect locally.
            port=3306,
            database=os.getenv('DATABASE')
        )
        cur = db.cursor(buffered=True)
        print("Connected to database locally!\n")
    except mariadb.Error as e:
        print(f"Database server not running locally, attempting database connection via Cloudflare...")
        try:
            db = mariadb.connect(
                user=os.getenv('DATABASE_USERNAME'),
                password=os.getenv('DATABASE_PASSWORD'),
                host=ip,
                port=3306,
                database=os.getenv('DATABASE')
            )
            cur = db.cursor(buffered=True)
            print("Connected to database via Cloudflare!\n")
        except mariadb.Error as e:
            print(f"\n##### FAILED TO CONNECT TO DATABASE! #####\n{e}\n")

    db.autocommit = True
    return

dbclass_connect()

# Function for checking if the database has 1) initially connected,
# 2) is still connected, 3) has disconnected. If the database
# connection has been lost, print message and reconnect
# immediately. Run once for every message sent.
def conn_check():
    if db is None:
        dbclass_connect()
    if not db.is_connected():
        print(f"\n\n####### DATABASE CONNECTION LOST! Attempting to reconnect... #######")
        dbclass_connect()

class Database:
    def __init__(self, name):
        global db
        global cur
        self.db = db
        self.cur = cur
        self.name = name
        #print(f"Database class '{name}' loaded.")
    
    def set_global_vars(self):
        global db
        global cur
        self.db = db
        self.cur = cur
        return
    
    async def db_executor_thread(self, exec_cmd):
        return await asyncio.to_thread(self.db_executor, exec_cmd)

    def db_executor(self, exec_cmd):
        for attempt in range(1,6):
            try:
                self.cur.execute(exec_cmd)
            except mariadb.Error as e:
                if attempt < 5:
                    if os.getenv('DATABASE_DEBUG') != "1": time.sleep(5)
                    conn_check()
                    self.set_global_vars()
                    continue
                else:
                    print(f"\nDATABASE ERROR! [{self.name}] Could not execute: \"{exec_cmd}\"\n{e}")
            break

        if exec_cmd.startswith("SELECT"):
            val = self.cur.fetchall()
            if len(val) == 1:         # Database will return 1 if any information is found.
                if len(val[0]) == 1:  # However, it will error out if we try len(value[0])
                    return val[0][0]  # and there was no information found (the array is
            return val                # not created.)
        return
    
    # Return cursor itself for more advanced cursor operations:
    # fetchone(), fetchmany(#), etc
    def get_cur(self, exec_cmd):
        try:
            self.cur.execute(exec_cmd)
            return self.cur
        except mariadb.Error as e:
            print(f"db_cur error: {e}")
        
        return None
    
    def exists(self, rows):
        if rows > 0:
            return True
        else:
            return False