import os

def gen_page(infos):
    '''
    a["status"] = "success"
    a["name"] = "name"
    a["ip"] = "192.168.1.1"
    a["last_ip_update"] = "yyyy-mm-dd: hh-mm-ss"
    a["cpu_load"] = "100%"
    a["gpu_load"] = "100%"
    a["last_sys_update"] = "yyyy-mm-dd: hh-mm-ss"
    '''
    
    f = open('./web_template/dashboard.html')
    T = f.readlines()

    head = ''.join(T[0:42])
    body_general_info = ''.join(T[42:65]).format(**get_general_block(infos))
   
    body_detail_info = ''.join(T[65:]).format(**get_detail_block(infos))
    return head + body_general_info + body_detail_info

def get_general_block(infos):
    general_tbody_template = '''
    <tr class="{status}">
                    <td>{name}</td>
                    <td>{ip} </td>
                    <td>{last_ip_update}</td>
                    <td>{cpu_load}</td>
                    <td>{gpu_load}</td>
                    <td>{last_sys_update}</td></tr>
    '''
    block = ""
    for info in infos:
        block += general_tbody_template.format(**info)
    return {"General_body":block}

def get_detail_block(infos):
    temlate = '''
                <div class="panel panel-primary">
                <div class="panel-heading">
                    <h3 class="panel-title">{name}</h3>
                </div>
                <div class="panel-body">
                    
                    <div class="container">
                         <div class="row">
                            <div class="col-xs-12 placeholder">     
                            <b style="font-size: 25px">Gpu load curve</b>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-xs-12 placeholder">
                                <img src="{gpu_load_url}" class="img-responsive" alt="Gpu load curve">
                            </div>
                        </div>
                        

                        <div class="row">
                            <div class="col-xs-12 placeholder">     
                            <b style="font-size: 25px">Cpu load curve</b>
                            </div>
                        </div>


                        <div class="row">
                        <div class="col-xs-12  placeholder">
                            <img src="{cpu_load_url}" class="img-responsive" alt="cpu load curve">
                        </div>
                        </div>




                        <div class="row">
                            <div class="col-xs-12 placeholder">     
                            <b style="font-size: 25px">memory load</b>
                            </div>
                        </div>
                        <div class="row">
                                <div class="col-xs-12 placeholder">
                                    <img src="{memory_load_url}" class="img-responsive" alt="memory load">
                                </div>
                        </div>
                        <div class="row">
                            <div class="col-xs-12 placeholder">     
                            <b style="font-size: 25px">disk usage</b>
                            </div>
                        </div>
                        <div class="row">
                                <div class="col-xs-12 placeholder">
                                    <img src="{disk_usage_url}" class="img-responsive" alt="disk usage">
                                </div>
                        </div>
                    </div>
                </div>
            </div>
    '''
    block = ""
    for info in infos:
        feed_dic = {}
        name = info["name"]
        feed_dic["name"] = name
        feed_dic["gpu_load_url"] = 'get_image?name={}&device={}'.format(name, 'gpu')
        feed_dic["cpu_load_url"] = 'get_image?name={}&device={}'.format(name, 'cpu')
        feed_dic["memory_load_url"] = 'get_image?name={}&device={}'.format(name, 'mem')
        feed_dic["disk_usage_url"] = 'get_image?name={}&device={}'.format(name, 'disk')
        block += temlate.format(**feed_dic)
    return {"Detail_body":block}
        

 
