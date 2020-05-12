#!/usr/bin/env python3

import random
import datetime
import argparse
import subprocess
import json
import math
import time
import sys
import os
import re


def convert_network(network):
    nodes = {}

    # create a structure we can use efficiently
    for node in network.get('nodes', []):
        nodes.setdefault(str(node['id']), [])

    for link in network.get('links', []):
        source = str(link['source'])
        target = str(link['target'])
        nodes.setdefault(source, []).append(target)
        nodes.setdefault(target, []).append(source)

    return nodes

class Dijkstra:
    def __init__(self, network):
        self.dists_cache = {}
        self.prevs_cache = {}
        self.nodes = convert_network(network)

    def find_shortest_distance(self, source, target):
        source = str(source)
        target = str(target)

        # try cache
        dists = self.dists_cache.get(source)
        if dists is not None:
            return dists[target]

        # calculate
        self._calculate_shortest_paths(source)

        # try again
        dists = self.dists_cache.get(source)
        if dists is not None:
            return dists[target]

        # should not happen...
        return None

    def get_shortest_path(self, source, target):
        source = str(source)
        target = str(target)

        # calculate
        self._calculate_shortest_paths(source)

        prevs = self.prevs_cache.get(source)
        if prevs is None:
            return None

        path = []
        next = target

        while True:
            prev = prevs[next]
            if prev is not None:
                next = prev
                path.append(next)
            else:
                break

        return path

    '''
    Calculate shortest path from source to every other node
    '''
    def _calculate_shortest_paths(self, initial):
        initial = str(initial)

        dists = {}
        prevs = {}
        q = {}

        for id in self.nodes:
            dists[id] = math.inf
            prevs[id] = None
            q[id] = None

        dists[initial] = 0

        def get_smallest(q, dists):
            dist = math.inf
            idx = None

            for k in q:
                d = dists[k]
                if d < dist:
                    idx = k
                    dist = d
            return idx

        for _ in range(len(self.nodes)):
            u = get_smallest(q, dists)
            if u is None:
                break
            del q[u]
            for v in self.nodes[u]:
                if v in q:
                    # distance update
                    alt = dists[u] + 1
                    if alt < dists[v]:
                        dists[v] = alt
                        prevs[v] = u

        self.dists_cache[initial] = dists
        self.prevs_cache[initial] = prevs

def get_biggest_cluster(network):
    neighbors = {}
    visited = {}

    neighbors = convert_network(network)
    for node in neighbors:
        visited[node] = False

    def dfs(node, cluster):
        visited[node] = True
        cluster.add(node)
        for neighbor in neighbors[node]:
            if not visited[neighbor]:
                dfs(neighbor, cluster)

    cluster = set()
    for node in visited:
        if not visited[node]:
            c = set()
            dfs(node, c)
            if len(c) > len(cluster):
                cluster = c

    links = []
    for link in network.get('links', []):
        if str(link['source']) in cluster or str(link['target']) in cluster:
            links.append(link)

    nodes = []
    for node in network.get('nodes', []):
        if str(node['id']) in cluster:
            nodes.append(node)

    return {'nodes': nodes, 'links': links}

def filter_paths(network, paths, min_hops=1, max_hops=math.inf, path_count=None):
    dijkstra = Dijkstra(network)

    filtered = []
    for path in paths:
        d = dijkstra.find_shortest_distance(path[0], path[1])
        if d >= min_hops and d <= max_hops:
            filtered.append(path)

    if path_count is not None:
        if len(filtered) < path_count:
            eprint('Only {len(filtered)} paths left after filtering. Required were at least {path_count}.')
            exit(1)

        if len(filtered) > path_count:
            filtered = filtered[:path_count]

    return filtered

def eprint(s):
    sys.stderr.write(s + '\n')

def root():
    if os.geteuid() != 0:
        eprint('Need to run as root.')
        exit(1)

def load_json(path):
    with open(path) as file:
        return json.load(file)
    return None

def seed_random(value):
    random.seed(value)

def sleep(seconds):
    time.sleep(seconds)

def wait(beg_ms, until_sec):
    now_ms = millis()

    # wait until time is over
    if (now_ms - beg_ms) < (until_sec * 1000):
        time.sleep(((until_sec * 1000) - (now_ms - beg_ms)) / 1000.0)
    else:
        eprint('Wait timeout already passed by {:.2f}sec'.format(((now_ms - beg_ms) - (until_sec * 1000)) / 1000))
        exit(1)

def json_count(path):
    obj = path

    if isinstance(path, str):
        obj = json.load(open(path))

    links = obj.get('links', [])
    nodes = {}
    for link in links:
        nodes[link['source']] = 0;
        nodes[link['target']] = 0;
    links = obj.get('links', [])
    return (len(nodes), len(links))

def sysload():
    p = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out, err) = p.communicate()
    t = out.decode().split('load average:')[1].split(',')
    load1 = t[0].strip()
    load5 = t[1].strip()
    load15 = t[2].strip()

    titles = ['load1', 'load5', 'load15']
    values = [load1, load5, load15]

    return (titles, values)

class _Traffic:
    def __init__(self):
        self.rx_bytes = 0
        self.rx_packets = 0
        self.rx_errors = 0
        self.rx_dropped = 0
        self.rx_overrun = 0
        self.rx_mcast = 0
        self.tx_bytes = 0
        self.tx_packets = 0
        self.tx_errors = 0
        self.tx_dropped = 0
        self.tx_carrier = 0
        self.tx_collsns = 0

    def getData(self):
        titles = ['rx_bytes', 'rx_packets', 'rx_errors', 'rx_dropped',
            'rx_overrun', 'rx_mcast', 'tx_bytes', 'tx_packets',
            'tx_errors', 'tx_dropped', 'tx_carrier', 'tx_collsns'
        ]

        values = [self.rx_bytes, self.rx_packets, self.rx_errors, self.rx_dropped,
            self.rx_overrun, self.rx_mcast, self.tx_bytes, self.tx_packets,
            self.tx_errors, self.tx_dropped, self.tx_carrier, self.tx_collsns
        ]

        return (titles, values)

    def __sub__(self, other):
        ts = _Traffic()
        ts.rx_bytes = self.rx_bytes - other.rx_bytes
        ts.rx_packets = self.rx_packets - other.rx_packets
        ts.rx_errors = self.rx_errors - other.rx_errors
        ts.rx_dropped = self.rx_dropped - other.rx_dropped
        ts.rx_overrun = self.rx_overrun - other.rx_overrun
        ts.rx_mcast = self.rx_mcast - other.rx_mcast
        ts.tx_bytes = self.tx_bytes - other.tx_bytes
        ts.tx_packets = self.tx_packets - other.tx_packets
        ts.tx_errors = self.tx_errors - other.tx_errors
        ts.tx_dropped = self.tx_dropped - other.tx_dropped
        ts.tx_carrier = self.tx_carrier - other.tx_carrier
        ts.tx_collsns = self.tx_collsns - other.tx_collsns
        return ts

def traffic(nsnames=None):
    if nsnames is None:
        nsnames = [x for x in os.popen('ip netns list').read().split() if x.startswith('ns-')]

    ts = _Traffic()

    for nsname in nsnames:
        command = ['ip', 'netns', 'exec', nsname , 'ip', '-statistics', 'link', 'show', 'dev', 'uplink']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output, err) = process.communicate()
        lines = output.decode().split('\n')
        link_toks = lines[1].split()
        rx_toks = lines[3].split()
        tx_toks = lines[5].split()
        ts.rx_bytes += int(rx_toks[0])
        ts.rx_packets += int(rx_toks[1])
        ts.rx_errors += int(rx_toks[2])
        ts.rx_dropped += int(rx_toks[3])
        ts.rx_overrun += int(rx_toks[4])
        ts.rx_mcast += int(rx_toks[5])
        ts.tx_bytes += int(tx_toks[0])
        ts.tx_packets += int(tx_toks[1])
        ts.tx_errors += int(tx_toks[2])
        ts.tx_dropped += int(tx_toks[3])
        ts.tx_carrier += int(tx_toks[4])
        ts.tx_collsns += int(tx_toks[5])

    return ts

# add titles and values to a CSV file
def csv_update(file, delimiter, *args):
    titles = list()
    values = list()

    for arg in args:
        titles += arg[0]
        values += arg[1]

    # convert elements to str
    for i in range(0, len(titles)):
        titles[i] = str(titles[i])

    # convert elements to str
    for i in range(0, len(values)):
        values[i] = str(values[i])

    if file.tell() == 0:
        file.write(delimiter.join(titles) + '\n')

    file.write(delimiter.join(values) + '\n')

# get time in milliseconds
def millis():
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

# get random node pairs (unique, no self, no reverses)
def get_random_paths(network=None, count=10, seed=None):
    if network is None:
        # all ns-* network namespaces
        nodes = [x[3:] for x in os.popen('ip netns list').read().split() if x.startswith('ns-')]
    else:
        nodes = list(convert_network(network).keys())

    if len(nodes) < 2 and count > 0:
        eprint('Not enough nodes to get any pairs!')
        exit(1)

    if seed is not None:
        random.seed(seed)

    def decode(items, i):
        k = math.floor((1 + math.sqrt(1 + 8 * i)) / 2)
        return (items[k], items[i - k * (k - 1) // 2])

    def rand_pair(n):
        return decode(random.randrange(n * (n - 1) // 2))

    def rand_pairs(items, npairs):
        n = len(items)
        return [decode(items, i) for i in random.sample(range(n * (n - 1) // 2), npairs)]

    return rand_pairs(nodes, count)

'''
Return an IP address of the interface in this preference order:
1. IPv4 not link local
2. IPv6 not link local
3. IPv6 link local
4. IPv4 link local
'''
def _get_ip_address(id, interface):
    lladdr6 = None
    lladdr4 = None

    with os.popen('ip netns exec "ns-{}" ip addr list dev {}'.format(id, interface)) as file:
        lines = file.read().split('\n')

        for line in lines:
            if 'inet ' in line:
                addr4 = line.split()[1].split('/')[0]
                if addr4.startswith('169.254.'):
                    lladdr4 = addr4
                else:
                    return addr4

        for line in lines:
            if 'inet6 ' in line:
                addr6 = line.split()[1].split('/')[0]
                if addr6.startswith('fe80:'):
                    lladdr6 = addr6
                else:
                    return addr6

    if lladdr6 is not None:
        return lladdr6
    else:
        return lladdr4

class _PingResult:
    send = 0
    transmitted = 0
    received = 0
    rtt_min = 0.0
    rtt_max = 0.0
    rtt_avg = 0.0

    def getData(self):
        titles = ['packets_send', 'packets_received', 'rtt_avg_ms']
        values = [self.send, self.received, self.rtt_avg]
        return (titles, values)

_numbers_re = re.compile('[^0-9.]+')

def _parse_ping(output):
    ret = _PingResult()
    for line in output.split('\n'):
        if 'packets transmitted' in line:
            toks = _numbers_re.split(line)
            ret.transmitted = int(toks[0])
            ret.received = int(toks[1])
        if line.startswith('rtt min/avg/max/mdev'):
            toks = _numbers_re.split(line)
            ret.rtt_min = float(toks[1])
            ret.rtt_avg = float(toks[2])
            ret.rtt_max = float(toks[3])
            #ret.rtt_mdev = float(toks[4])

    return ret

def ping(count=10, duration_ms=1000, verbosity='normal', seed=None):
    paths = get_random_paths(network=None, count=count, seed=seed)
    return ping_paths(paths, duration_ms, verbosity)

def ping_paths(paths, duration_ms=1000, verbosity='normal'):
    def get_interface(source):
        # some protocols use their own interface as entry point to the mesh
        for ifce in ['bat0', 'tun0']:
            if os.system(f'ip netns exec ns-{source} ip addr list dev {ifce} > /dev/null 2>&1') == 0:
                return ifce
        return 'uplink'

    ping_deadline=1
    ping_count=1
    processes = []
    interface = None
    start_ms = millis()
    started = 0
    path_count = len(paths)
    while started < path_count:
        # number of expected tests to have been run
        started_expected = math.ceil(path_count * ((millis() - start_ms) / duration_ms))
        if started_expected > started:
            for _ in range(0, started_expected - started):
                if len(paths) == 0:
                    break
                (source, target) = paths.pop()

                if interface is None:
                    interface = get_interface(source)

                target_addr = _get_ip_address(target, interface)

                if target_addr is None:
                    eprint('Cannot get address of {} in ns-{}'.format(interface, target))
                    # count as started
                    started += 1
                else:
                    if verbosity == 'verbose':
                        print('[{:06}] Ping {} => {} ({} / {})'.format(millis() - start_ms, source, target, target_addr, interface))

                    command = ['ip', 'netns', 'exec', f'ns-{source}' ,'ping', '-c', f'{ping_count}', '-w', f'{ping_deadline}', '-D', target_addr]
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    processes.append(process)
                    started += 1
        else:
            # sleep a small amount
            time.sleep(duration_ms / path_count / 1000.0 / 10.0)

    stop1_ms = millis()

    # wait until duration_ms is over
    if (stop1_ms - start_ms) < duration_ms:
        time.sleep((duration_ms - (stop1_ms - start_ms)) / 1000.0)

    stop2_ms = millis()

    ret = _PingResult()

    # wait/collect for results from pings (prolongs testing up to 1 second!)
    for process in processes:
        process.wait()
        (output, err) = process.communicate()
        result = _parse_ping(output.decode())
        result.send = ping_count # TODO: nicer

        ret.send += result.send
        ret.transmitted += result.transmitted
        ret.received += result.received
        ret.rtt_avg += result.rtt_avg

    ret.rtt_avg = 0 if ret.received == 0 else int(ret.rtt_avg / ret.received)
    result_duration_ms = stop1_ms - start_ms
    result_filler_ms = stop2_ms - stop1_ms

    if verbosity != 'quiet':
        print('send: {}, received: {}, arrived: {}%, measurement span: {}ms + {}ms'.format(
            ret.send,
            ret.received,
            '-' if (ret.send == 0) else '{:0.2f}'.format(100.0 * (ret.received / ret.send)),
            result_duration_ms,
            result_filler_ms
        ))

    return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action', required=True)

    parser_ping = subparsers.add_parser('ping', help='Ping various nodes.')
    parser_ping.add_argument('--input', default=None, help='JSON state of the network.')
    parser_ping.add_argument('--min-hops', type=int, default=1, help='Minimum hops to ping.')
    parser_ping.add_argument('--max-hops', type=int, default=math.inf, help='Maximum hops to ping.')
    parser_ping.add_argument('--pings', type=int, default=10, help='Number of pings.')
    parser_ping.add_argument('--duration', type=int, default=1000, help='Spread pings over duration in ms.')

    args = parser.parse_args()

    if args.action == 'ping':
        paths = []
        if args.input is None:
            paths = get_random_paths(None, args.pings)
        else:
            state = json.load(args.input)
            paths = get_random_paths(state, args.pings)
            paths = filter_paths(state, paths, min_hops=args.min_hops, max_hops=args.max_hops)

        ping_paths(paths=paths, duration_ms=args.duration, verbosity='verbose')
    else:
        eprint('Unknown action: {}'.format(args.action))
        exit(1)
