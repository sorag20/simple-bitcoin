import socket

from p2p.connection_manager_4edge import ConnectionManager4Edge



STATE_INIT = 0
STATE_ACTIVE = 1
STATE_SHUTTING_DOWN = 2


class ClientCore:

    def __init__(self, my_port=50082, core_host=None, core_port=None):
        self.client_state = STATE_INIT
        print('Initializing server...')
        self.my_ip = self.__get_myip()
        print('Server IP address is set to ... ', self.my_ip)
        self.my_port = my_port
        self.cm = ConnectionManager4Edge(self.my_ip,my_port, core_host, core_port)

    def start(self):

        self.client_state = STATE_ACTIVE
        self.cm.start()
        self.cm.connect_to_core_node()

    def shutdown(self):
        """
            待ち受け状態のServer Socketを閉じて終了する（上位UI層向け
        """
        self.client_state = STATE_SHUTTING_DOWN
        print('Shutdown edge node ...')
        self.cm.connection_close()

    def get_my_current_state(self):
        """
            現在のEdgeノードの状態を取得する（上位UI層向け
        """
        return self.client_state


    def __get_myip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
