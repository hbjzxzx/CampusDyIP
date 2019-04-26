import os, json, time, datetime
import sqlite3
import cgi
import hashlib

class pserver():
    def __init__(self, datapath):
        self.datapath = datapath

        self.pathmap = {}
        self.pathmap[('GET', '/get_infos')] = self.get_infos
        self.pathmap[('GET', '/get_infos_web')] = self.get_info_web
        self.pathmap[('GET', '/put_ip_info')] = self.put_ip_info
        self.pathmap[('GET', '/put_system_info')] = self.put_system_info
        self.pathmap[('GET', '/register')] = self.register_gpu_server

    def create_database(self):
        dir_name, file_name = os.path.split(self.datapath)
        if not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        
        conn = sqlite3.connect(self.datapath)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE gpu_server_info_table
       (ID INTEGER PRIMARY KEY   AUTOINCREMENT,
       NAME TEXT    UNIQUE NOT NULL,
       UPDATE_KEY TEXT  UNIQUE NOT NULL,
       LAST_UPDATE_TIME   INT,
       IP TEXT);''')

        c.execute('''CREATE TABLE gpu_server_detail_table
       (
       NAME TEXT  ,
       RECORD_TIME  INT,
       info  TEXT
       );''')

        conn.commit()
        conn.close()

    def error(self, env, start_response, info):
        start_response('500 Internal Server Error', [ ('Content-type', 'text/plain')])
        c = info.encode(encoding='GBK', errors='strict')
        return [c]

    def __call__(self, env, start_response):
        try:
            if not os.path.isfile(self.datapath):
                self.create_database()
        except Exception as e:
            return self.error(env, start_response, str(e))
        else:
            method = env['REQUEST_METHOD']
            path = env['PATH_INFO']
            env['params'] = cgi.FieldStorage(env['wsgi.input'], environ=env)

            if (method,path) in self.pathmap:
                return self.pathmap[(method,path)](env, start_response)
            else:
                return self.error(env, start_response, "function({},{}) does not exist".format(method,path))

    def get_info_web(self, env, start_response):
        pass

    
    def get_infos(self, env, start_response):
        conn = sqlite3.connect(self.datapath)
        c = conn.cursor()
        json_dict = {}
        put_success_flag = False

        result = c.execute("SELECT name, last_update_time, ip FROM gpu_server_info_table;").fetchall()
        for index, row in enumerate(result):
            timestr = datetime.datetime.fromtimestamp(row[1]).strftime('%Y-%m-%d %H:%M:%S')
            json_dict["GPU_Server_{}".format(index)] = "ServerName:{}, last_update_time:{}, local_ip:{}".format(row[0], timestr, row[2])
        conn.close()
        start_response('200 OK', [ ('Content-type', 'application/json')])
        return [json.dumps(json_dict).encode('utf-8')]

    def put_system_info(self, env, start_response):
        conn = sqlite3.connect(self.datapath)
        c = conn.cursor()
        json_dict = {}
        put_success_flag = False

        gpu_server_name = env['params']['name'].value
        gpu_server_update_key = env['params']['update_key'].value
        info = env['params']['info'].value

        result = c.execute("SELECT name, update_key from gpu_server_info_table WHERE name=? and update_key=?;",
                            (gpu_server_name, gpu_server_update_key)).fetchall()
        
        if len(result) == 0:
            json_dict["reason"] = "name or update_key dismatch"
        else:
            c.execute("INSERT INTO gpu_server_detail_table (name, record_time, info) VALUE(?,?,?)",
                    (gpu_server_name, time.time(), info))
            put_success_flag = True
             
        start_response('200 OK', [ ('Content-type', 'application/json')])
        json_dict["result"] = put_success_flag
        conn.commit()
        conn.close()
        return [json.dumps(json_dict).encode('utf-8')]


    def put_ip_info(self, env, start_response):
        conn = sqlite3.connect(self.datapath)
        c = conn.cursor()
        json_dict = {}
        put_success_flag = False

        gpu_server_name = env['params']['name'].value
        gpu_server_update_key = env['params']['update_key'].value
        new_ip = env['params']['ip'].value

        result = c.execute("SELECT name, update_key from gpu_server_info_table WHERE name=? and update_key=?;",
                            (gpu_server_name, gpu_server_update_key)).fetchall()
        if len(result) == 0:
            json_dict["reason"] = "name or update_key dismatch"
        else:
            c.execute("UPDATE gpu_server_info_table SET last_update_time=?, ip=? where name=?" ,(int(time.time()), new_ip, gpu_server_name ) )
            put_success_flag = True
        
        start_response('200 OK', [ ('Content-type', 'application/json')])
        json_dict["result"] = put_success_flag
        conn.commit()
        conn.close()
        return [json.dumps(json_dict).encode('utf-8')]


    def register_gpu_server(self, env, start_response):
        conn = sqlite3.connect(self.datapath)
        c = conn.cursor()
        gpu_server_name = env['params']['name'].value
        json_dict = {}

        result = c.execute("SELECT name from gpu_server_info_table WHERE name=?",(gpu_server_name,)).fetchall()
        if not len(result) == 0:
           update_key = ""
           json_dict["reason"] = "exist same name gpu server" 
        else: 
            salt_text = 'this is a salt text'
            
            md = hashlib.md5()
            md.update( (gpu_server_name + salt_text).encode("utf8"))
            update_key =  md.hexdigest()
            c.execute("INSERT INTO gpu_server_info_table (NAME, UPDATE_KEY) VALUES(?,?)",(gpu_server_name, update_key))
        start_response('200 OK', [ ('Content-type', 'application/json')])
        
        json_dict["update_key"] = update_key
        conn.commit()
        conn.close()
        return [json.dumps(json_dict).encode('utf-8')]
        

