import socket
import time
import logging
import json, sys
import random
import threading
from threading import Thread
logging.basicConfig(filename='client.log',level=logging.DEBUG)


clientId = sys.argv[1]
BUFFER_SIZE = 2000 
CLIRES= 'ClientResponse'
SHOWRES= 'ShowResponse'
# ! TODO: need to change TICKETREQ to MONEYREQ (or something)
# MONEYREQ = 'MoneyRequest'
TICKETREQ = 'TicketRequest'
CONFIGCHANGE = 'ConfigChangeRequest'

CONFIGFILE = 'config.json'

client_server_map =  {
    "cl1":"dc1",
    "cl2":"dc2",
    "cl3":"dc3",
}

class RaftClient():
    def __init__(self, clientId):
        self.leaderId = None
        self.reqId = 0
        self.clientId = clientId
        # ! TODO: change below
        # self.money = 0
        self.tickets = 0
        self.lastReq = None
        self.readAndApplyConfig()
        thread = Thread(target = self.requestMoneyFromUser)
        thread.start()
        self.startListening()


    def readAndApplyConfig(self):
        with open(CONFIGFILE) as config_file:    
            self.config = json.load(config_file)
        self.timeout = self.config['client_request_timeout']
        if self.leaderId not in self.config['datacenters']:
            self.leaderId = None



    def getServerIpPort(self, serverId):
        '''Get ip and port on which server is listening from config'''
        return self.config['dc_addresses'][serverId][0], self.config['dc_addresses'][serverId][1]

    # ! TODO: function below should be changed to something like this
    # def formRequestMsg(self, money):
    #     msg = {
    #         'ClientREquest': {
    #             'reqId': self.clientId + ':' + str(self.reqId),
    #             'money': money
    #         }
    #     }
    def formRequestMsg(self, tickets):
        msg = { 
        'ClientRequest': {
            'reqId': self.clientId + ':' + str(self.reqId),
            'tickets': tickets
            }
        }
        return msg


    def formShowCommandMsg(self):
        msg = { 
        'ShowRequest': {
             'reqId': self.clientId + ':' + str(self.reqId) 
            }
        }
        return msg


    def formConfigChangeCmdMsg(self):
        msg = { 
        'ConfigChangeRequest': {
             'reqId': self.clientId + ':' + str(self.reqId),
             'configFile': CONFIGFILE
            }
        }
        return msg        


    def parseRecvMsg(self, recvMsg):
            ''' msg = {'leaderId': <id>, 'response':<>}'''
            recvMsg = json.loads(recvMsg)
            msgType, msg = recvMsg.keys()[0], recvMsg.values()[0]
            return msgType, msg


    def startListening(self):
        '''Start listening for server response'''
        ip, port = self.config["clients"][self.clientId][0], self.config["clients"][self.clientId][1]

        tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        tcpClient.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        tcpClient.bind((ip, port))

        while True:
            tcpClient.listen(4) 
            (conn, (cliIP, cliPort)) = tcpClient.accept()
            
            data = conn.recv(BUFFER_SIZE)
            msgType, msg = self.parseRecvMsg(data)

            '''Update leader id based on the server response'''
            self.leaderId = msg['leaderId']

            if msgType == CLIRES:
                '''If its response for ticket request, cancel timer and handle the message accordingly'''
                self.cancelTimer()
                if msg['redirect'] == True:
                    # ! TODO: change below
                    # self.requestMoney()
                    self.requestTicket()
                else:
                    if self.lastReq == CONFIGCHANGE:
                        self.readAndApplyConfig()
                    if self.leaderId:
                        print '\nCurrent LEADER is %s.'%self.leaderId 
                    print msg['response']
                    self.requestMoneyFromUser()

            else:
                print '\nCurrent LEADER is %s.'%self.leaderId 
                print msg['response']
                '''If its response of show, continue prompting user'''
                self.requestMoneyFromUser()


    def sendRequest(self):
        '''Form the request message and send a tcp request to server asking for tickets''' # ! TODO: <--- MONEY, not asking for tickets
        if not self.leaderId:
            '''If leader is not known, randomly choose a server and request tickets'''
            randomIdx =  random.randint(0, len(self.config['datacenters'])-1)
            serverId = self.config['datacenters'][randomIdx]
        else:
            serverId = self.leaderId

        ip, port = self.getServerIpPort(serverId)
        reqMsg = self.formRequestMsg(self.tickets)
        reqMsg = json.dumps(reqMsg)
        try:
            tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            '''Start timer to get a reply within certain time; if timeout happens, resend the same request'''
            self.startTimer()
            tcpClient.settimeout(1)
            tcpClient.connect((ip, port))
            tcpClient.send(reqMsg)
            time.sleep(0.5)
            tcpClient.close()
        except Exception as e:
            '''When a site is down, tcp connect fails and raises exception; catching and 
            ignoring it as we don't care about sites that are down'''
            pass


    def startTimer(self):
        self.timer = threading.Timer(self.timeout, self.handleTimeout)
        self.timer.start()

    def cancelTimer(self):
        self.timer.cancel()


    def handleTimeout(self):
        '''On timeout, choose a server that is not previous leader and send money request''' # ! TODO: change comment
        '''On timeout, choose a server that is not previous leader and send ticket request'''
        oldLeader = self.leaderId
        while True:
            randomIdx =  random.randint(0, len(self.config['datacenters'])-1)
            serverId = self.config['datacenters'][randomIdx]
            if serverId != oldLeader:
                self.leaderId = serverId
                break
        # ! TODO: change below
        # if self.lastReq == MONEYREQ:
        if self.lastReq == TICKETREQ:
            self.sendRequest()
        elif self.lastReq == CONFIGCHANGE:
            self.sendConfigChangeCommand()

    # # ! TODO: change below
    # def requestMoney(self):
    #     self.sendRequest()
    def requestTicket(self):
        self.sendRequest()


    def sendShowCommand(self):
        serverId = client_server_map[clientId]
        ip, port = self.getServerIpPort(serverId)
        reqMsg = self.formShowCommandMsg()
        reqMsg = json.dumps(reqMsg)
        try:
            tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcpClient.settimeout(1)
            tcpClient.connect((ip, port))
            tcpClient.send(reqMsg)
            time.sleep(0.5)
            tcpClient.close()
        except Exception as e:
            '''When a site is down, tcp connect fails and raises exception; catching and 
            ignoring it as we don't care about sites that are down'''
            pass


    def sendConfigChangeCommand(self):
        if not self.leaderId:
            '''If leader is not known, randomly choose a server and request tickets'''
            randomIdx =  random.randint(0, len(self.config['datacenters'])-1)
            serverId = self.config['datacenters'][randomIdx]
        else:
            serverId = self.leaderId

        ip, port = self.getServerIpPort(serverId)
        reqMsg = self.formConfigChangeCmdMsg()
        reqMsg = json.dumps(reqMsg)
        try:
            tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            '''Start timer to get a reply within certain time; if timeout happens, resend the same request'''
            self.startTimer()
            tcpClient.settimeout(1)
            tcpClient.connect((ip, port))
            tcpClient.send(reqMsg)
            time.sleep(0.5)
            tcpClient.close()
        except Exception as e:
            '''When a site is down, tcp connect fails and raises exception; catching and 
            ignoring it as we don't care about sites that are down'''
            pass


    def requestMoneyFromUser(self): 
        # ! TODO: the commented block below should be MODIFIED to fit the uncommented block underneath it
        # '''Prompt user for options'''
        # while True:
        #     try:
        #         query_1 = "\nWhat would you like to do?\n"
        #         query_2 = "> A. Send money to a bank <args: [to where] [amount]>\n"
        #         query_3 = "> B. Take a snapshot\n"
        #         query_4 = "> C. Toggle connection\n"
        #         query_5 = "> D. Shut down bank\n"
        #         query = query_1 + query_2 + query_3 + query_4 + query_5 + "\n"
        #         choice = raw_input(query)
        #         choice = str(choice)
        #     except:
        #         continue

        #     if choice != 'A' and choice != 'B' and choice != 'C' and choice != 'D':
        #         print 'Invalid option! Please entier A, B, C, or D.'
        #         continue

        #     if choice == 'A':
        #         choice = choice.split()
        #         amtMoney = int(choice[1])
        #         if amtMoney <= 0:
        #             print 'Invalid entry! Please enter a valid money amount.'
        #             continue

        '''Take request from user and request tickets from server''' 
        while True:
            try:
                displayMsg = "\nChoose an option:\na) Press 1 to buy tickets.\nb) Press 2 to show log on the server.\n"
                displayMsg += "c) Press 3 initiate configuration change.\n"
                choice = raw_input(displayMsg)
                choice = int(choice)
            except:
                continue

            if choice != 1 and choice != 2 and choice != 3:
                print 'Invalid option! Please enter either 1 or 2.'
                continue

            if choice == 1: 
                noOfTickets = raw_input("Enter no. of tickets: ")
                noOfTickets = int(noOfTickets)
                if noOfTickets <= 0:
                    print 'Invalid entry! Please enter a valid ticket count.'
                    continue
            break

        
        if choice == 1:
            self.tickets = noOfTickets
            '''Increment request id on each valid user request'''
            self.reqId += 1
            # ! TODO: change below
            # self.lastReq = MONEYREQ
            self.lastReq = TICKETREQ
            self.sendRequest()
        elif choice == 2:
            self.sendShowCommand()
        else:
            self.reqId += 1
            self.lastReq = CONFIGCHANGE
            self.sendConfigChangeCommand()

# def prompt_user(my_port, sendingSockets):
#     global current_money, num_snapshots, my_state, saved_states, in_snap, current_marker

#     while True:
#         query_1 = "\nWhat would you like to do?\n"
#         query_2 = "> A. Send money to a bank <args: [to where] [amount]>\n"
#         query_3 = "> B. Take a snapshot\n"
#         query_4 = "> C. Toggle connection\n"
#         query_5 = "> D. Shut down bank\n"
#         query = query_1 + query_2 + query_3 + query_4 + query_5 + "\n"
#         run_command = input(query)
#         run_command = run_command.split()
#         if run_command[0] == "A":
#             where_to_send = int(run_command[1])
#             amount_to_send = int(run_command[2])
#             current_money -= amount_to_send
#             print("<{}> sent {} dollars to <{}>. The current balance for <{}> is {}.".format(my_port, amount_to_send, str(where_to_send), my_port, current_money))
#             send_money(str(amount_to_send), my_port, where_to_send, 0)
#         elif run_command[0] == "B":
#             in_snapshot = 1
#             print("\nA snapshot has been initiated by <{}>.".format(my_port))
            
#             num_snapshots += 1
#             # snapshot_leader = my_port
#             marker_id = str(my_port) + "." + str(num_snapshots)
#             my_state[marker_id] = current_money
#             current_marker = marker_id
#             marker_received[marker_id] = {}
#             saved_states[marker_id] = []
#             for port_id in FIFO_CHANNELS[my_port]:
#                 marker_received[marker_id][port_id] = 0
#                 send_marker(my_port, port_id, marker_id, my_port)
#         elif run_command[0] == "C":
#             CONNECTION_ONLINE = not CONNECTION_ONLINE
#             print("Connection online:", CONNECTION_ONLINE)
#         elif run_command[0] == "D":
#             break
#             for x, my_socket in sendingSockets.items():
#                 my_socket.socket_object.shutdown(socket.SHUT_RDWR)
#                 my_socket.socket_object.close()
#             sys.exit()
#         else:
#             print("Invalid input. Try again.")
        
        
client = RaftClient(clientId)

