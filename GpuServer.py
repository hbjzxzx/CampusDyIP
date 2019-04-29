#! /usr/local/anaconda3/bin/python

import util.gputil.GPUtil as GPUtil
import psutil
import sqlite3, os, urllib.request, json, subprocess, sched, time, platform, urllib.parse
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
        
        result = c.execute(''' SELECT NAME FROM local_data WHERE NAME=?;''', (name,)).fetchall()
        if len(result) == 0:
            c.execute(''' INSERT INTO local_data (name) VALUES(?);''', (name,))
            conn.commit()
            conn.close()
            self.register()
        else:
            result = c.execute(''' SELECT update_key FROM local_data WHERE NAME=?;''', (name,)).fetchall()[0]
            if not result[0]:
                self.register()
            else:
                self.update_key = result[0]

    def start_report(self, timer, interval):
        if not self.update_key:
            print("put ip error: no update_key")
            print("try reregister with name:{}".format(self.name))
            self.register()
            timer.enter(interval, 0, self.start_report, (timer, interval) )
        else:
            print('update ip information...{}'.format(time.strftime("%H:%M:%S %b %d %Y ",time.localtime())))
            self.put_ip_info()
            print('update system information...{}'.format(time.strftime("%H:%M:%S %b %d %Y ",time.localtime())))
            self.put_system_info()
            timer.enter(interval, 0, self.start_report, (timer, interval) )
    def register(self):
        info = Reporter.get_system_info()
        info = json.dumps(info)
        info = urllib.parse.quote(info)
        register_url = "http://{}/register?name={}&info={}".format(self.host, self.name, info)
        
        response = urllib.request.urlopen(register_url)
        dic = json.loads(response.readlines()[0])
        if dic["update_key"]:
            conn = sqlite3.connect(self.dbname)
            c = conn.cursor()
            c.execute(''' UPDATE local_data SET update_key=? WHERE name=?;''', (dic["update_key"], self.name))

            self.update_key = dic["update_key"]
            conn.commit()
            conn.close()
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
        info = Reporter.get_system_info(get_cpu_load=True)
        info = json.dumps(info)
        info = urllib.parse.quote(info)
        put_url = "http://{}/put_system_info?name={}&update_key={}&info={}".format(self.host, self.name, self.update_key, info)
        response = urllib.request.urlopen(put_url)
        dic = json.loads(response.readlines()[0])

        if not dic["result"]:
            print("put system info error: {}".format(dic["reason"]))

    @classmethod
    def getIP_ByIfconfig(cls, use_router = False):
        if not use_router:
            p = Popen(['ifconfig'], stdout = PIPE)
            data = [x.decode('utf-8') for x in p.stdout.readlines()]
            data = ''.join(data)
            data = data.split('\n\n')

            data = [i for i in data if i and i.startswith('ppp0')]
            if not data:
                return "ppp0_break_down"
            data = data[0].split(' ')
            c = data.index('inet')
            if c != -1:
                return data[c+1]
            else:
                return ""
        else:
            from selenium import webdriver
            
            option = webdriver.ChromeOptions()
            option.add_argument('headless')
            br = webdriver.Chrome(options=option)
            br.get('http://192.168.1.1')
            br.find_element_by_id('pcPassword').send_keys('ibrain')
            br.find_element_by_id('loginBtn').click()

            time.sleep(3)
            frames = br.find_elements_by_tag_name("frame")
            targe = frames[4]
            br.switch_to.frame(targe)


            table = br.find_element_by_xpath('/html/body/center/form/table[4]/tbody/tr[2]/td/table/tbody/tr[1]/td[2]/table/tbody/tr[2]/td[2]').text

            return table


    @classmethod
    def get_system_info(cls, get_cpu_load = False):
        gpus = GPUtil.getGPUs()
        cls.gpu_info = {}
        cls.gpu_info["gpu_count"] = len(gpus)
        cls.gpu_info["gpus"] = {}
        for i in range(len(gpus)):
            gpu = gpus[i]
            dic = {}
            dic["name"] = gpu.name
            dic["load"] = int(gpu.load * 100)
            dic["mem_load"] = int(gpu.memoryUtil * 100)
            dic["mem_total"] = gpu.memoryTotal
            dic['temperature'] = gpu.temperature
            cls.gpu_info["gpus"]["gpu{}".format(i)] = dic
        
        cls.cpu_info = {}
        cls.cpu_info["cpu_count"] = psutil.cpu_count()
       
        if get_cpu_load:
           for i in range(cls.cpu_info["cpu_count"]):
                a = psutil.cpu_percent(interval=1, percpu=True)
                cls.cpu_info["cpu_{}".format(i)] = reduce(lambda x,y:x+y, a)/len(a)
        
        cls.mem_info = {}

        mem_info = {}

        m = psutil.virtual_memory()
        mem_info["total"] = m.total
        mem_info["used"] = m.used
        mem_info["free"] = m.free
        mem_info["ava"] = m.available
        mem_info["load"] = int(m.percent)

        disk_info = {}
        
        part_point = set()
        for p in psutil.disk_partitions():
            if p.device.startswith('/dev/s'):
                part_point.add(p.mountpoint)
        for d in part_point:
            disk_info[d] = psutil.disk_usage(d)
        
        info = {}
        info["gpu"] = cls.gpu_info
        info["cpu"] = cls.cpu_info
        info["mem"] = mem_info
        info["disk"] = disk_info
        return info

        
if __name__ == '__main__':
   
    while True:
        try:
            Reporter.get_system_info()

            server_name = 'server1_209'
            local_dbname = 'sqlitedb.db'
            server_ip_port = '95.169.16.163'
            #server_ip_port = '192.168.0.105:8080'


            interval = 60

            report = Reporter (server_name, local_dbname, server_ip_port)
            s = sched.scheduler(time.time, time.sleep)
            s.enter(0, 0, report.start_report, (s, interval))
            print('start...')
            s.run()
        except KeyboardInterrupt:
            print('stop')
            break
        except Exception as e:
            print('Exception : {}'.format(str(e)))
            print('continue...')