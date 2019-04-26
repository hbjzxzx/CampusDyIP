import gputil.GPUtil as GPUtil
import sqlite3, os, urllib, json, subprocess


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
        
    def register(self):
        register_url = "http://{}/register?name={}".format(self.host,self.name)
        response = urllib.request.urlopen(register_url)
        dic = json.loads(response.readlines()[0])
        if dic["update_key"]:
            conn = sqlite3.connect(dbname)
            c = conn.cursor()
            c.execute(''' UPDATE local_data SET update_key=? WHERE name=?;''', (dic["update_key"], name))
            self.register = True
        else:
            print("Error while register:{}".format(dic))
            self.register = False


def get_interface_ip(remote_ip=None):
    interface_ip = '127.0.0.1'
    remote_ip = remote_ip or '8.8.8.8'
    result = subprocess.check_output('ip route get {}'.format(remote_ip), shell=True)
    result_split = result.split()

    # result_split will look like:
    # ['8.8.8.8', 'via', '172.16.185.2', 'dev', 'eth0', 'src', '172.16.185.173', 'cache']
    #
    # So just find the index containing 'src', and the next token will be the interface IP
    index_containing_src = 0
    print( result_split )
    for i in range(len(result_split)):
        if result_split[i].decode() == 'src':
            index_containing_src = i
            break

    interface_ip_index = index_containing_src + 1
    if interface_ip_index < len(result_split):
        interface_ip = result_split[interface_ip_index]

    return interface_ip

if __name__ =="__main__":
    print(get_interface_ip())