import os
import time
from collections import defaultdict
from copy import deepcopy

monitor_threshold_bytes = 5000

mode = "dump-ports"
# mode = "dump-flows"

if mode ==  "dump-ports":
    record_rx, pre_record_rx, record_tx, pre_record_tx = defaultdict(dict), defaultdict(dict), defaultdict(dict), defaultdict(dict)
    o_cmd = "sudo ovs-ofctl dump-ports %s -O OpenFlow13"
elif mode == "dump-flows":
    record, pre_record = defaultdict(dict), defaultdict(dict)
    o_cmd = "sudo ovs-ofctl dump-flows %s -O OpenFlow13"

get_next = defaultdict(dict)
    
## add 30XX
for switch in range(3001, 3008+1):
    if switch % 2 == 1:
        get_next[str(switch)]['port1'] = str(switch - 1000)
        get_next[str(switch)]['port2'] = str(switch - 999)
    else :
        get_next[str(switch)]['port1'] = str(switch - 1001)
        get_next[str(switch)]['port2'] = str(switch - 1000)

    get_next[str(switch)]['port3'] = "h%03d" % (switch % 1000 * 2 - 1)
    get_next[str(switch)]['port4'] = "h%03d" % (switch % 1000 * 2)

## add 20XX
for switch in range(2001, 2008+1):
    if switch % 2 == 1:
        get_next[str(switch)]['port1'] = "1001"
        get_next[str(switch)]['port2'] = "1002"
        get_next[str(switch)]['port3'] = str(switch + 1000)
        get_next[str(switch)]['port4'] = str(switch + 1001)
    else :
        get_next[str(switch)]['port1'] = "1003"
        get_next[str(switch)]['port2'] = "1004"
        get_next[str(switch)]['port3'] = str(switch + 999)
        get_next[str(switch)]['port4'] = str(switch + 1000)

## add 10XX
for switch in range(1001, 1004+1):
    if switch == 1001 or switch == 1002:
        get_next[str(switch)]['port1'] = "2001"
        get_next[str(switch)]['port2'] = "2003"
        get_next[str(switch)]['port3'] = "2005"
        get_next[str(switch)]['port4'] = "2007"
    else :
        get_next[str(switch)]['port1'] = "2002"
        get_next[str(switch)]['port2'] = "2004"
        get_next[str(switch)]['port3'] = "2006"
        get_next[str(switch)]['port4'] = "2008"

# print(get_next)
# raise "s"

switch_list = ['1001', '1002', '1003', '1004', 
        '2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008', 
        '3001', '3002', '3003', '3004', '3005', '3006', '3007', '3008']
    
visit = {sw:False for sw in switch_list}

def handle_dump_flows(switch, res, record):
    res = res.replace(' ', '')
    res = res.split('\n')
    for r in res:
        r = r.split(',')
        if len(r) > 7 and 'nw_dst' in r[7]: 
            n_byte = r[4].split("=")[1]
            nw_dst = r[7].split("actions")[0].split("=")[1]
            record[str(switch)][str(nw_dst)] = int(n_byte)
            # print(n_byte, nw_dst)

def handle_dump_ports(switch, res):
    # print(res)
    res = res.replace(' ', '')
    res = res.split('\n')
    # print(len(res))
    if len(res) == 17:
        for line in range(1, len(res)-1, 3): 
            r1 = res[line].split(":")
            r2 = res[line+1]
            port = r1[0]
            if port == "portLOCAL": continue
            rx = r1[1].split(",")[1].split("=")[1]
            tx = r2.split(",")[1].split("=")[1]
            # print(port, rx, tx)
            record_rx[switch][port] = int(rx)
            record_tx[switch][port] = int(tx)
            # if len(r) > 1:
            # print(r1, r2)
    else:
        print('error', res)

def get_different(pre_rec, rec):
    for switch in switch_list:
        for dstORport in pre_rec[switch]:
            if rec[switch][dstORport] > pre_rec[switch][dstORport]:
                print(switch, dstORport)
            # print(rec[switch][nw_dst], pre_rec[switch][nw_dst])
            # pass
    print('--')

def dfs(node):
    # print(visit)
    if node[0] == 'h': # end
        print("dst > %s" % node)
        return
    if visit[node]: 
        print("v %s" % node)
        return
    visit[node] = True
    for port in pre_record_tx[node]:
        if record_tx[node][port] - pre_record_tx[node][port] > monitor_threshold_bytes:
            print("d switch %s sent %d bytes to %s" % (node, record_tx[node][port] - pre_record_tx[node][port], get_next[node][port]))
            dfs(get_next[node][port])

def show_flow():
    # check rx
    first_switch_list = ['3001', '3002', '3003', '3004', '3005', '3006', '3007', '3008']
    for fs in first_switch_list:
        # check each switch
        for o_port in pre_record_tx[fs]:
            # check each port of this switch
            if record_tx[fs][o_port] - pre_record_tx[fs][o_port] > monitor_threshold_bytes and get_next[fs][o_port][0] != 'h':
                # this port sent
                print("s switch %s sent %d bytes to %s" % (fs, record_tx[fs][o_port] - pre_record_tx[fs][o_port], get_next[fs][o_port]))
                for vis in visit: visit[vis] = False
                # print(visit)
                visit[fs] = True
                dfs(get_next[fs][o_port])
    print('--')

if __name__ == '__main__':
    while True:
        for switch in switch_list:
            cmd = o_cmd % switch
            res = os.popen(cmd).read()
            # print('--', switch)
            # print(res)
            if mode ==  "dump-ports": handle_dump_ports(switch, res)
            elif mode == "dump-flows": handle_dump_flows(switch, res, record)
        if mode ==  "dump-ports": 
            if len(pre_record_tx):
                # get_different(pre_record_rx, record_rx)
                show_flow()
            pre_record_rx = deepcopy(record_rx)
            pre_record_tx = deepcopy(record_tx)
        elif mode == "dump-flows": 
            if len(pre_record):
                get_different(pre_record, record)
                print(pre_record == record)
            pre_record = deepcopy(record)
        time.sleep(1)
        # break