import os, json, time, datetime, urllib.parse
import sqlite3
import cgi
import hashlib
from Gweb import gen_page
class pserver():
    def __init__(self, datapath):
        self.datapath = datapath

        self.pathmap = {}
        self.pathmap[('GET', '/get_infos')] = self.get_infos
        self.pathmap[('GET', '/get_infos_web')] = self.get_info_web
        self.pathmap[('GET', '/put_ip_info')] = self.put_ip_info
        self.pathmap[('GET', '/put_system_info')] = self.put_system_info
        self.pathmap[('GET', '/register')] = self.register_gpu_server
        
        self.pathmap[('GET', '/get_image')] = self.get_image
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
       gpu_count INT,
       cpu_count INT,
       memory_total INT,
       disk_part_count INT
       );''')

        c.execute('''CREATE TABLE gpu_detail_table (
           name TEXT,
           gpu_id TEXT,
           gpu_name TEXT,
           gpu_total_mem INT
       )
       ''')

        c.execute('''CREATE TABLE disk_detail_table (
           name TEXT,
           partial_name TEXT,
           partial_total INT
       )
       ''')

        c.execute('''CREATE TABLE disk_run_record (
           name TEXT,
           partial_id TEXT,
           record_time INT,
           used INT,
           load INT
       )
       ''')
        c.execute('''CREATE TABLE gpu_run_record (
           name TEXT,
           gpu_id TEXT,
           record_time INT,
           load INT,
           mem_load INT
       )
       ''')

        c.execute('''CREATE TABLE cpu_run_record (
           name TEXT,
           cpu_id TEXT,
           record_time INT,
           load INT
       )
       ''')

        c.execute('''CREATE TABLE mem_run_record(
           name TEXT,
           record_time INT,
           used INT,
           free INT,
           ava INT,
           load INT
       )
       ''')

        conn.commit()
        conn.close()

    def error(self, env, start_response, info):
        start_response('500 Internal Server Error', [ ('Content-type', 'text/plain')])
        c = info.encode(encoding='GBK', errors='strict')
        return [c]

    def get_image(self, env, start_response):
        
        
        f = open('./web_template/test.jpg', 'rb')
        image = f.read()
        start_response('200 OK', [ ('Content-type', 'image/jpg')])
        f.close()
        return [image]

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
        start_response('200 OK', [ ('Content-type', 'text/html')])
        a={}
        a["status"] = "success"
        a["name"] = "name"
        a["ip"] = "192.168.1.1"
        a["last_ip_update"] = "yyyy-mm-dd: hh-mm-ss"
        a["cpu_load"] = "100%"
        a["gpu_load"] = "100%"
        a["last_sys_update"] = "yyyy-mm-dd: hh-mm-ss"
        page = gen_page([a,a,a])
        return([page.encode('utf-8')])

    
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
        info = json.loads(info)

        result = c.execute("SELECT name, update_key from gpu_server_info_table WHERE name=? and update_key=?;",
                            (gpu_server_name, gpu_server_update_key)).fetchall()
        
        if len(result) == 0:
            json_dict["reason"] = "name or update_key dismatch"
        else:
            now_time = time.time()
            for i in range(info['cpu']['cpu_count']):
                c.execute("INSERT INTO cpu_run_record (name, cpu_id, record_time, load) VALUES(?,?,?,?)",
                    (gpu_server_name, i, now_time, info['cpu']['cpu_{}'.format(i)]))

            
            for i in range(info['gpu']['gpu_count']):
                gpu = info['gpu']['gpus']['gpu{}'.format(i)]
                c.execute("INSERT INTO gpu_run_record (name, gpu_id, record_time, load, mem_load) VALUES(?,?,?,?,?)",
                    (gpu_server_name, i, now_time, gpu['load'], gpu['mem_load']))
            
            for part_name, used_vec in info['disk'].items():
                c.execute("INSERT INTO disk_run_record (name, partial_id, record_time, used, load) VALUES(?,?,?,?,?)",
                    (gpu_server_name, part_name, now_time, used_vec[1], used_vec[3]))
                


            c.execute("INSERT INTO mem_run_record (name, record_time, used, free, ava, load) VALUES(?,?,?,?,?,?)",
                    (gpu_server_name, now_time, info['mem']['used'], info['mem']['free'], info['mem']['ava'], info['mem']['load']))
            
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
        info = env['params']['info'].value
        info = json.loads(info)
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
            c.execute("INSERT INTO gpu_server_detail_table(name, gpu_count, cpu_count, memory_total, disk_part_count) VALUES(?,?,?,?,?)",
                        (gpu_server_name, info['gpu']['gpu_count'], info['cpu']['cpu_count'], info['mem']['total'], len(info['disk'])))
            
            for i in range(info['gpu']['gpu_count']):
                gpu = info['gpu']['gpus']['gpu{}'.format(i)]
                c.execute("INSERT INTO gpu_detail_table (name, gpu_id, gpu_name, gpu_total_mem) VALUES(?,?,?,?)",
                            (gpu_server_name, i, gpu['name'], gpu['mem_total']))
            for partial_nam, usage_info in info['disk'].items():
                c.execute("INSERT INTO disk_detail_table (name, partial_name, partial_total) VALUES(?,?,?)",
                            (gpu_server_name, partial_nam, usage_info[0]))
                
        start_response('200 OK', [ ('Content-type', 'application/json')])
        
        json_dict["update_key"] = update_key
        conn.commit()
        conn.close()
        return [json.dumps(json_dict).encode('utf-8')]
        

