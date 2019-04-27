#! /usr/local/anaconda3/bin/python

import util.gputil.GPUtil as GPUtil
import psutil
import sqlite3, os, urllib, json, subprocess, sched, time
from subprocess import Popen, PIPE
from functools import reduce

class Reporter():
    def __init__(self, name, dbname, server_url):
        self.name = name
        self.dbname = dbname
        self.host = server_url
        self.update_key = ""

        if not os.path.isfile(dbname):
            conn = sqlite3.connect(dbname)
            c = conn.cursor()
            c.execute('''CREATE TABLE local_data(
                NAME TEXT UNIQUE NOT NULL,
                UPDATE_KEY TEXT UNIQUE);''')
            conn.commit()
            conn.close()
        
        conn = sqlite3.connect(dbname)
        c = conn.cursor()
        
        result = c.execute(''' SELECT NAME FROM local_data WHERE NAME=?;''', name).fetchall()
        if len(result) == 0:
            c.execute(''' INSERT INTO local_data (name) VALUES(?);''', (name,))
            conn.commit()
            conn.close()
            self.register()
        else:
            result = c.execute(''' SELECT update_key FROM local_data WHERE NAME=?;''', name).fetchall()[0]
            if not result:
                self.register()
            else:
                self.update_key = result

    def start_report(self, timer, interval):
        self.put_ip_info()
        self.put_system_info()
        timer.enter(interval, 0, self.start_report, (timer, interval) )
    def register(self):
        register_url = "http://{}/register?name={}".format(self.host, self.name)
        response = urllib.request.urlopen(register_url)
        dic = json.loads(response.readlines()[0])
        if dic["update_key"]:
            conn = sqlite3.connect(self.dbname)
            c = conn.cursor()
            c.execute(''' UPDATE local_data SET update_key=? WHERE name=?;''', (dic["update_key"], self.name))

            self.update_key = dic["update_key"]
        else:
            self.update_key = ""
            print("Error while register:{}".format(dic))
            
    def put_ip_info(self):
        local_ip =  Reporter.getIP_ByIfconfig()
        put_url = "http://{}/put_ip_info?name={}&update_key={}&ip={}".format(self.host, self.name, self.update_key, local_ip)
        response = urllib.request.urlopen(put_url)
        dic = json.loads(response.readlines()[0])

        if not dic["result"]:
            print("put ip error: {}".format(dic["reason"]))
            print("try reregister with name:{}".format(self.name))
            self.register()
    
    def put_system_info(self):
        info = Reporter.get_system_info()
        put_url = "http://{}/put_system_info?name={}&update_key={}&info={}".format(self.host, self.name, self.update_key, info)
        response = urllib.request.urlopen(put_url)
        dic = json.loads(response.readlines()[0])

        if not dic["result"]:
            print("put system info error: {}".format(dic["reason"]))

    @classmethod
    def getIP_ByIfconfig(cls):
        p = Popen(['ifconfig'], stdout = PIPE)
        data = [x.decode('utf-8') for x in p.stdout.readlines()]
        data = ''.join(data)
        data = data.split('\n\n')
        data = [i for i in data if i and i.startswith('ppp0')][0]
        data = data.split(' ')
        c = data.index('inet')
        if c != -1:
            return data[c+1]
        else:
            return ""

    @classmethod
    def get_system_info(cls):
        gpus = GPUtil.getGPUs()
        cls.gpu_info = {}
        cls.gpu_info["gpu_count"] = len(gpus)
        cls.gpu_info["gpus"] = {}
        for i in range(len(gpus)):
            gpu = gpus[i]
            dic = {}
            dic["name"] = gpu.name
            dic["load"] = gpu.load
            dic["mem_load"] = gpu.memoryUtil
            dic["mem_total"] = gpu.memoryTotal
            cls.gpu_info["gpus"]["gpu{}".format(i)] = dic
        
        cls.cpu_info = {}
        cls.cpu_info["cpu_count"] = psutil.cpu_count()
        for i in range(cls.cpu_info["cpu_count"]):
            a = psutil.cpu_percent(interval=1, percpu=True)
            cls.cpu_info["cpu_{}".format(i)] = reduce(lambda x,y:x+y, a)/len(a)
        
        cls.mem_info = {}

        mem_info = {}
        rate = 30 # G 
        print( psutil.virtual_memory())
        m = psutil.virtual_memory()
        total_m = m.total >> rate
        used_m = m.used >> rate
        free_m = m.free >> rate
        ava_m = m.available >> rate
        percent_m = m.percent
        mem_info["total"] = total_m
        mem_info["used"] = used_m
        mem_info["free"] = free_m
        mem_info["ava"] = ava_m
        mem_info["percent"] = percent_m

        disk_info = {}
        disk_info["sys"] = {}

        sys_disk = psutil.disk_usage('/')
        sys_disk_total = sys_disk.total >> rate
        sys_disk_used = sys_disk.used >> rate
        sys_disk_percent = sys_disk.percent
        disk_info["sys"]["total"] = sys_disk_total
        disk_info["sys"]["used"] = sys_disk_used
        disk_info["sys"]["percent"] = sys_disk_percent

        disk_info["user"] = {}
        
        user_disk = psutil.disk_usage('/home')
        user_disk_total = user_disk.total >> rate
        user_disk_used = user_disk.used >> rate
        user_disk_percent = user_disk.percent
        disk_info["user"]["total"] = user_disk_total
        disk_info["user"]["used"] = user_disk_used
        disk_info["user"]["percent"] = user_disk_percent
        
        info = {}
        info["gpu"] = cls.gpu_info
        info["cpu"] = cls.cpu_info
        info["mem"] = cls.mem_info
        info["disk"] = disk_info
        return info
if __name__ == '__main__':
    server_name = 'server1_209'
    local_dbname = 'sqlitedb.db'
    server_url = '95.169.16.163'

    interval = 60

    report = Reporter (server_name, local_dbname, server_name)
    s = sched.scheduler(time.time, time.sleep)
    s.enter(0, 0, report.start_report, (s, interval))
    print('start...')
    s.run()