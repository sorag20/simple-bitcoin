import socket
import threading
import pickle
import codecs
from concurrent.futures import ThreadPoolExecutor

from .core_node_list import CoreNodeList
from .edge_node_list import EdgeNodeList

from .message_manager import (
    MessageManager,
    MSG_ADD,
    MSG_REMOVE,
    MSG_CORE_LIST,
    MSG_REQUEST_CORE_LIST,
    MSG_PING,
    MSG_ADD_AS_EDGE,
    MSG_REMOVE_EDGE,

    ERR_PROTOCOL_UNMATCH,
    ERR_VERSION_UNMATCH,
    OK_WITH_PAYLOAD,
    OK_WITHOUT_PAYLOAD,
)


# 動作確認用の値。本来は30分(1800)くらいがいいのでは
PING_INTERVAL = 10


class ConnectionManager:

    def __init__(self, host,  my_port):
        print('Initializing ConnectionManager...')
        self.host = host
        self.port = my_port
        self.core_node_set = CoreNodeList()
        self.edge_node_set = EdgeNodeList()
        self.__add_peer((host, my_port))
        self.mm = MessageManager()

    # 待受を開始する際に呼び出される（ServerCore向け
    def start(self):
        t = threading.Thread(target=self.__wait_for_access)
        t.start()

        self.ping_timer = threading.Timer(PING_INTERVAL, self.__check_peers_connection)
        self.ping_timer.start()
        
        self.ping_timer_e = threading.Timer(PING_INTERVAL, self.__check_edges_connection)
        self.ping_timer_e.start()

    # ユーザが指定した既知のCoreノードへの接続（ServerCore向け
    def join_network(self, host, port):
        self.my_c_host = host
        self.my_c_port = port
        self.__connect_to_P2PNW(host, port)

    # 指定されたノードに対してメッセージを送信する
    def send_msg(self, peer, msg):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((peer))
            s.sendall(msg.encode('utf-8'))
            s.close()
        except OSError:
            print('Connection failed for peer : ', peer)
            self.__remove_peer(peer)

    # Coreノードリストに登録されている全てのノードに対して同じメッセージをブロードキャストする
    def send_msg_to_all_peer(self, msg):
        print('send_msg_to_all_peer was called!')
        current_list = self.core_node_set.get_list()
        for peer in current_list:
            if peer != (self.host, self.port):
                print("message will be sent to ... ", peer)
                self.send_msg(peer, msg)

    # 終了前の処理としてソケットを閉じる
    def connection_close(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        self.socket.close()
        s.close()
        #接続確認のスレッドの停止
        self.ping_timer.cancel()
        #離脱要求の送信
        msg = self.mm.build(MSG_REMOVE, self.port)
        self.send_msg((self.my_c_host, self.my_c_port), msg)


    def __connect_to_P2PNW(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        msg = self.mm.build(MSG_ADD, self.port)
        s.sendall(msg.encode('utf-8'))
        s.close()


    def __wait_for_access(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(0)

        executor = ThreadPoolExecutor(max_workers=10)

        while True:

            print('Waiting for the connection ...')
            soc, addr = self.socket.accept()
            print('Connected by .. ', addr)
            data_sum = ''

            params = (soc, addr, data_sum)
            executor.submit(self.__handle_message, params)

    # 受信したメッセージを確認して、内容に応じた処理を行う。クラスの外からは利用しない想定
    def __handle_message(self, params):

        soc, addr, data_sum = params

        while True:
            data = soc.recv(1024)
            data_sum = data_sum + data.decode('utf-8')

            if not data:
                break

        if not data_sum:
            return

        result, reason, cmd, peer_port, payload = self.mm.parse(data_sum)
        print(result, reason, cmd, peer_port, payload)
        status = (result, reason)

        if status == ('error', ERR_PROTOCOL_UNMATCH):
            print('Error: Protocol name is not matched')
            return
        elif status == ('error', ERR_VERSION_UNMATCH):
            print('Error: Protocol version is not matched')
            return
        elif status == ('ok', OK_WITHOUT_PAYLOAD):
            if cmd == MSG_ADD:
                print('ADD node request was received!!')
                self.__add_peer((addr[0], peer_port))
                if(addr[0], peer_port) == (self.host, self.port):
                    return
                else:
                    cl = pickle.dumps(self.core_node_set.get_list(), 0).decode()
                    msg = self.mm.build(MSG_CORE_LIST, self.port, cl)
                    self.send_msg_to_all_peer(msg)
                    self.send_msg_to_all_edge(msg)
            elif cmd == MSG_REMOVE:
                print('REMOVE request was received!! from', addr[0], peer_port)
                self.__remove_peer((addr[0], peer_port))
                cl = pickle.dumps(self.core_node_set.get_list(), 0).decode()
                msg = self.mm.build(MSG_CORE_LIST, self.port, cl)
                self.send_msg_to_all_peer(msg)
                self.send_msg_to_all_edge(msg)
            elif cmd == MSG_PING:
                # 特にやること思いつかない
                return
            elif cmd == MSG_REQUEST_CORE_LIST:
                print('List for Core nodes was requested!!')
                cl = pickle.dumps(self.core_node_set.get_list(), 0).decode()
                msg = self.mm.build(MSG_CORE_LIST, self.port, cl)
                self.send_msg((addr[0], peer_port), msg)
            elif cmd == MSG_ADD_AS_EDGE:
                self.__add_edge_node((addr[0], peer_port))
                cl = pickle.dumps(self.core_node_set.get_list(), 0).decode()
                msg = self.mm.build(MSG_CORE_LIST, self.port, cl)
                self.send_msg((addr[0], peer_port), msg)
            elif cmd == MSG_REMOVE_EDGE:
                self.__remove_edge_node((addr[0], peer_port))
                
            else:
                print('received unknown command', cmd)
                return
        elif status == ('ok', OK_WITH_PAYLOAD):
            if cmd == MSG_CORE_LIST:
                    # TODO: 受信したリストをただ上書きしてしまうのは本来セキュリティ的には宜しくない。
                    # 信頼できるノードの鍵とかをセットしとく必要があるかも
                    # このあたりの議論については６章にて補足予定
                    print('Refresh the core node list...')
                    new_core_set = pickle.loads(payload.encode('utf8'))
                    print('latest core node list: ', new_core_set)
                    self.core_node_set.overwrite(new_core_set)
            else:
                print('received unknown command', cmd)
                return
        else:
            print('Unexpected status', status)


    def __add_peer(self, peer):
        """
        Coreノードをリストに追加する。クラスの外からは利用しない想定

        param:
            peer : Coreノードとして格納されるノードの接続情報（IPアドレスとポート番号）
        """
        self.core_node_set.add((peer))


    def __remove_peer(self, peer):
        """
        離脱したと判断されるCoreノードをリストから削除する。クラスの外からは利用しない想定

        param:
            peer : 削除するノードの接続先情報（IPアドレスとポート番号）
        """
        self.core_node_set.remove(peer)
    
    def __add_edge_node(self, edge):
        """
        Edge ノードをリストに追加する。クラスの外からは利用しない想定
        """
        self.edge_node_set.add((edge))
    
    def __remove_edge_node(self, edge):
        """
        離脱したと判断される Edge ノードをリストから削除する。クラスの外からは利用しない想定
        """
        self.edge_node_set.remove(edge)
    
    def send_msg_to_all_edge(self, msg):
        print('send_msg_to_all_edge was called! ')
        current_list = self.edge_node_set.get_list()
        for edge in current_list:
            print("message will be sent to ... " ,edge)
            self.send_msg(edge, msg)


    def __check_peers_connection(self):
        """
        接続されているCoreノード全ての生存確認を行う。クラスの外からは利用しない想定
        この確認処理は定期的に実行される
        """
        print('check_peers_connection was called')
        current_core_list = self.core_node_set.get_list()
        changed = False
        dead_c_node_set = list(filter(lambda p: not self.__is_alive(p), current_core_list))
        if dead_c_node_set:
            changed = True
            print('Removing peer', dead_c_node_set)
            current_core_list = current_core_list - set(dead_c_node_set)
            self.core_node_set.overwrite(current_core_list)

        current_core_list = self.core_node_set.get_list()
        print('✔ current core node list:', current_core_list)
        # 変更があった時だけブロードキャストで通知する
        if changed:
            cl = pickle.dumps(current_core_list, 0).decode()
            msg = self.mm.build(MSG_CORE_LIST, self.port, cl)
            self.send_msg_to_all_peer(msg)
        self.ping_timer = threading.Timer(PING_INTERVAL, self.__check_peers_connection)
        self.ping_timer.start()
    
    def __check_edges_connection(self):
        """
        接続されているEdgeノード全ての生存確認を行う。クラスの外からは利用しない想定
        この確認処理は定期的に実行される
        """
        print('check_edges_connection was called')
        current_edge_list = self.edge_node_set.get_list()
        dead_e_node_set = list(filter(lambda p: not self.__is_alive(p), current_edge_list))
        if dead_e_node_set:
            print('Removing Edges', dead_e_node_set)
            current_edge_list = current_edge_list - set(dead_e_node_set)
            self.edge_node_set.overwrite(current_edge_list)

        current_edge_list = self.edge_node_set.get_list()
        print('💠current edge node list:', current_edge_list)
        self.ping_timer_e = threading.Timer(PING_INTERVAL, self.__check_edges_connection)
        self.ping_timer_e.start()


    def __is_alive(self, target):
        """
        有効ノード確認メッセージの送信
．．
        param:
            target : 有効ノード確認メッセージの送り先となるノードの接続情報（IPアドレスとポート番号）
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((target))
            msg_type = MSG_PING
            msg = self.mm.build(msg_type)
            s.sendall(msg.encode('utf-8'))
            s.close()
            return True
        except OSError:
            return False
