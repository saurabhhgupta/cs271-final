# encoding=utf8

import os
import sys
import json
import time
import queue
import socket
import threading
import string
import random
import pickle
import math
import hashlib
from string import ascii_uppercase
from string import digits
from random import SystemRandom

########## Configuration setup ##########
FILE = "config.json"
with open(FILE, 'r') as json_file:
	data = json.load(json_file)

TCP_IP = data["TCP_IP"][0]
PORTS = [data["NETWORK_MAP"][str(i)] for i in data["NETWORK_MAP"]]
print(PORTS)
CHANNELS = {port : [i for i in PORTS if i != port] for port in PORTS}
BALANCE = {port : data["BALANCE"][0] for port in PORTS}
FOLLOWER, CANDIDATE, LEADER = data["FOLLOWER"], data["CANDIDATE"], data["LEADER"]
CONNECTION_ONLINE = True
INIT_BLOCKCHAIN_FILE = "initialize_blockchain.txt"
# majority is 2 b/c we have 3 sites
MAJORITY = 2
SOCKET_LISTEN_BOUND = 10
########## End configuration setup ##########

def threaded(sending_sockets):
	global current_money
	global current_port
	global current_leader
	global halt_process
	global heartbeat
	global current_term

	while(True):
		query_1 = "\nWhat would you like to do?\n"
		query_2 = "> A. Send money to a bank <args: (to where) (amount)>\n"
		query_3 = "> B. Print balance\n"
		query_4 = "> C. Print blockchain\n"
		query_5 = "> D. Turn off server\n"
		query_6 = "> E. Turn on server\n"
		query_7 = "> F. Show status\n"
		query_7 = "> G. Toggle connection\n"
		query_8 = "> H. Shut down bank\n"
		query = query_1 + query_2 + query_3 + query_4 + query_5 + query_6 + query_7 + query_8 + "\n"
		user_input = input(query)
		user_input = user_input.split()
		if user_input[0] == "A":
			where_to_send = int(user_input[1])
			amount_to_send = int(user_input[2])
			if amount_to_send > get_balance():
				print("Not enough money in [{}]. Balance = ${}".format(current_port, get_balance()))
			else:
				if current_port != current_leader:
					send_money("{} {} {}".format(str(current_port), str(where_to_send), str(amount_to_send)), current_port, current_leader)
				else:
					# current server is leader
					queue_transactions.put("{} {} {}".format(str(current_port), str(where_to_send), str(amount_to_send)))
				print("[{}] sent ${} to [{}].".format(current_port, amount_to_send, str(where_to_send)))
		elif user_input[0] == "B":
			print("Balance = ${}".format(get_balance()))
		elif user_input[0] == "C":
			print("fuck me")
		elif user_input[0] == "D":
			halt_process = 1
		elif user_input[0] == "F":
			pass
		elif user_input[0] == "E":
			halt_process = 0
		elif user_input[0] == "G":
			CONNECTION_ONLINE = not CONNECTION_ONLINE
			print("Connection online:", CONNECTION_ONLINE)
		elif user_input[0] == "H":
			break
			sys.exit()
		else:
			print("\nUser input not recognized. Try again (A-H).\n")

class Thread(object):
	thread_dest = None
	thread_args = None
	thread_created = None

	def __init__(self, target, args):
		self.thread_dest = target
		self.thread_args = args

	def create_thread(self):
		self.thread_created = threading.Thread(name=self.thread_dest.__name__, target=self.thread_dest, args=self.thread_args)
		self.thread_created.start()
		return self

	def join_thread(self):
		self.thread_created.join()

class Socket(object):
	socket_ip = None
	socket_port = None
	socket_object = None

	def __init__(self, ip, port):
		self.socket_ip = ip
		self.socket_port = port

	def send_to_socket(self, message):
		try:
			self.socket_object.send(message)
		except socket.error as socket_error:
			print("[{}] ERROR! Failed to send.".format(int(sys.argv[1])), socket_error)

	def create_send_socket(self):
		while(True):
			try:
				self.socket_object = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.socket_object.connect((self.socket_ip, self.socket_port))
			except ConnectionRefusedError:
				time.sleep(3)
				print("[{}] Connecting to <{}:{}>...".format(int(sys.argv[1]), self.socket_ip, self.socket_port))
			else:
				print("[{}] CONNECTED to <{}:{}>".format(int(sys.argv[1]), self.socket_ip, self.socket_port))
				return self

	def create_recv_socket(self):
		while(True):
			try:
				self.socket_object = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.socket_object.bind((self.socket_ip, self.socket_port))
				self.socket_object.listen(SOCKET_LISTEN_BOUND)
			except:
				print("[{}] ERROR! Cannot create socket <{}:{}>".format(int(sys.argv[1]), self.socket_ip, self.socket_port))
				time.sleep(3)
			else:
				print("[{}] Created socket <{}:{}>".format(int(sys.argv[1]), self.socket_ip, self.socket_port))
				return self

	def close_socket(self):
		return self.socket_object.close()

	def toggle_connect(self):
		return self.socket_object.accept()[0]

class Message(object):
	port_sender = 0
	port_receiver = 0
	message_type = None
	message_content = None

	def __init__(self, sender, receiver, content, send_type):
		self.port_sender = sender
		self.port_receiver = receiver
		self.message_content = content
		self.message_type = send_type

	def pack(self):
		return pickle.dumps(self)

class RequestVoteRPC(object):
	message_type = None
	candidate_id = 0
	term = 0
	last_log_index = 0
	last_log_term = 0
	result_term = None
	result_vote_granted = None
	vote_from = None

	def __init__(self, id, term, log_index, log_term):
		self.message_type = "RequestVoteRPC"
		self.candidate_id = id
		self.term = term
		self.last_log_index = log_index
		self.last_log_term = log_term

	def pack(self):
		return pickle.dumps(self)

class AppendEntriesRPC(object):
	message_type = None
	term = 0
	leader_id = 0
	prev_log_index = 0
	prev_log_term = 0
	entries = []
	commit_index = 0
	result_term = 0
	success = 0
	port_sender = 0

	def __init__(self, term, leader_id, prev_log_index, prev_log_term, entries, commit_index):
		self.message_type = "AppendEntriesRPC"
		self.term = term
		self.leader_id = leader_id
		self.prev_log_index = prev_log_index
		self.prev_log_term = prev_log_term
		self.entries = entries
		self.commit_index = commit_index

	def pack(self):
		return pickle.dumps(self)

class Block(object):
	current_term = 0
	prev_header_hash = None
	current_transactions_hash = None
	nonce = None
	transaction_list = None

	def __init__(self, prev_header_hash):
		self.transaction_list = []
		self.prev_header_hash = prev_header_hash

	# ! TODO: add transaction
	def add_transaction(self, transaction):
		self.transaction_list.append(transaction)

	# ! TODO: calculate number of transactions
	def calculate_number_of_transactions(self):
		return len(self.transaction_list)

	# ! TODO: calculate the nonce (done)
	def calculate_nonce(self):
		accept_digit = ['0', '1', '2']
		self.nonce = generate_string()
		while hash(str(self.nonce) + self.current_transactions_hash)[-1] not in accept_digit:
			calculate_nonce()

	# ! TODO: formulate the block
	def formulate_block(self, term):
		tx_a, tx_b = hash(self.transaction_list[0]), hash(self.transaction_list[1])
		self.current_transactions_hash = hash(tx_a + tx_b)
		self.nonce = self.calculate_nonce()
		self.current_term = term

	# ! TODO: display the block contents (print_blockchain)
	def print_block(self, number):
		print("block # - {}".format(number))
		print("term - {}".format(self.current_term))
		print("H_header(B-1) - {}".format(self.prev_header_hash))
		print("H_txs(B) - {}".format(self.current_transactions_hash))
		print("nonce - {}".format(self.nonce))
		print("list of trans - {}".format(', '.join(self.transaction_list)))

current_port = 0
objects_socket_recv = []
objects_socket_send = {}
queue_task = queue.Queue()
queue_transactions = queue.Queue()
current_money = 0
current_term = 0
current_block = None
heartbeat = 0
current_leader = 0
current_status = 0
voted_for = {}
log = []
self_votes = 0
next_index = {}
halt_process = 0

def read_socket(packet):
	global queue_task
	while(True):
		try:
			data = packet.recv(2048)
			if data:
				# need to split b/c of stupid read error
				data = data.split(b'\x80')
				for chunk in data[1:]:
					convert_to_bin = b'\x80' + chunk
					message_type = pickle.loads(convert_to_bin).message_type
					queue_task.put(convert_to_bin)
		except OSError:
			sys.exit()

def process(current_port):
	global PORTS
	global queue_task
	global log
	global current_term
	global current_status
	global voted_for
	global self_votes
	global heartbeat
	global current_leader
	global next_index
	global queue_transactions
	global halt_process

	while(True):
		while queue_task.empty():
			time.sleep(0.1)
		data = pickle.loads(queue_task.get())
		if halt_process:
			continue
		if (data.message_type == "RequestVoteRPC") and (data.result_vote_granted == None):
			# check to see if requested leader qualifies to become new leader
			if data.term > current_term:
				current_term = data.term
				if current_status != FOLLOWER:
					current_status = FOLLOWER
			if data.term == current_term:
				if data.term not in voted_for:
					voted_for[data.term] = 0
				if (voted_for[data.term] == 0 or voted_for[data.term] == data.candidate_id) and (len(log) <= data.last_log_index):
					# grant vote for this candidate
					voted_for[data.term] = data.candidate_id
					print("Vote granted to {}.".format(data.candidate_id))
					send_vote(current_port, data, current_term, 1)
		# check if the server voted current server as leader
		elif (data.message_type == "RequestVoteRPC") and (data.result_vote_granted != None):
			if data.result_vote_granted == 1:
				self_votes += 1
			# gained majority --> winner
			if self_votes >= MAJORITY:
				print("Elected as new leader.")
				current_status = LEADER
				self_votes = 0
				current_leader = current_port
				next_index = {PORTS[0]: len(log), PORTS[1]: len(log), PORTS[2]: len(log)}
				send_heartbeat(current_port)
		elif data.message_type == "AppendEntriesRPC" and data.result_term == 0:
			# ignore b/c older term
			if data.term < current_term:
				continue
			# adjust to new term if FOLLOWER
			if data.term > current_term:
				current_term = data.term
			# step down to FOLLOWER if trying to be leader
			if current_status == CANDIDATE or current_status == LEADER:
				current_status = FOLLOWER
			current_leader = data.leader_id
			heartbeat = 0
			voted_for[current_term] = data.leader_id
			self_votes = 0
			# entries do not exist, obtain from leader
			if data.prev_log_index > (len(log) - 1):
				return_append(data, current_term, 0, current_port)
			else:
				if data.prev_log_index == -1:
					log = data.entries
					return_append(data, current_term, 1, current_port)
				# logs are mismatched, prompt leader to send log
				elif log[data.prev_log_index].current_term != data.prev_log_term:
					return_append(data, current_term, 0, current_port)
				else:
					# logs to replicate
					if data.entries != []:
						log = log + data.entries
					return_append(data, current_term, 1, current_port)
		elif data.message_type == "AppendEntriesRPC" and data.result_term != 0:
			# receiver missing entries in log
			if data.success == 0:
				next_index[data.port_sender] -= 1
			else:
				next_index[data.port_sender] = len(log)
		elif data.message_type == "money":
			queue_transactions.put(data.message_content)

def leader_alive():
	global heartbeat
	global current_port
	global current_leader
	global current_status
	global current_term
	global voted_for
	global self_votes
	global halt_process
	global next_index

	while(True):
		if not halt_process:
			if current_status == FOLLOWER or current_status == CANDIDATE:
				if heartbeat == 5:
					print("Leader is down. Start new election.")
					current_term += 1
					current_status = CANDIDATE
					self_votes += 1
					voted_for[current_term] = current_port
					send_request_vote(current_port, current_term)
					heartbeat = 0
				else:
					heartbeat += 1
			elif current_status == LEADER:
				send_heartbeat(current_port)
		time.sleep(random.randint(500, 2500)/1000)

def get_balance():
	global current_port
	global log
	initial_balance = BALANCE[current_port]
	# ! TODO: need to cycle through the transactions in a block
	# ! check if the current port is the same as the sender, if so then decrement the amt 
	# ! if receiver == current_port then increment the amt
	for i in log:
		for j in i.transaction_list:
			j = j.split()
			sender, receiver, amount = int(j[0]), int(j[1]), int(j[2])
			# if sending, subtract from bank balance
			if current_port == sender:
				initial_balance -= amount
			# if receiving, add to bank balance
			if current_port == receiver:
				initial_balance += amount
	return initial_balance

def send_heartbeat(current_port):
	global current_term
	global next_index
	global log

	for host, socket in objects_socket_send.items():
		if len(log) == 0:
			send_message = AppendEntriesRPC(current_term, current_leader, 0, 0, 0, 0).pack()
		else:
			send_message = AppendEntriesRPC(current_term, current_leader, next_index[host] - 1, log[next_index[host] - 1].current_term, log[next_index[host]:], 0).pack()
		socket.send_to_socket(send_message)

def send_money(money, port_sender, port_receiver):
	send_message = Message(port_sender, port_receiver, money, "money").pack()
	objects_socket_send[port_receiver].send_to_socket(send_message)

def send_vote(current_port, unpacked_data, current_term, vote_granted):
	unpacked_data.result_term = current_term
	unpacked_data.result_vote_granted = vote_granted
	unpacked_data.vote_from = current_port
	send_message = unpacked_data.pack()
	objects_socket_send[unpacked_data.candidate_id].send_to_socket(send_message)

def return_append(unpacked_data, term, success, current_port):
	unpacked_data.result_term = term
	unpacked_data.success = success
	unpacked_data.port_sender = current_port
	send_message = unpacked_data.pack()
	objects_socket_send[unpacked_data.leader_id].send_to_socket(send_message)

def send_request_vote(current_port, current_term):
	global log
	for host, socket in objects_socket_send.items():
		if(len(log) == 0):
			send_message = RequestVoteRPC(current_port, current_term, 0, 0).pack()
		else:
			send_message = RequestVoteRPC(current_port, current_term, len(log), log[-1].current_term).pack()
		socket.send_to_socket(send_message)

# Source: https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
def generate_string():
	return ''.join(SystemRandom().choice(ascii_uppercase + digits) for _ in range(8))

def hash(data):
	return hashlib.sha256(data.encode('utf-8')).hexdigest()

def create_block():
	global log
	global next_index
	global queue_transactions
	global current_block
	global current_leader
	global current_port
	global current_status

	# delay until leader elections is finished
	while current_leader == 0:
		time.sleep(0.01)

	# empty out the queue if i'm the leader
	if current_port != current_leader:
		queue_transactions.queue.clear()

	while True:
		# just wait if there aren't any transactions
		while queue_transactions.empty():
			time.sleep(0.1)
		data = queue_transactions.get()
		if current_block == None:
			# block #1 created here
			if len(log) == 0:
				prev_header_hash = hash('NULL')
			else:
				# header contains: 1) term #, 2) H_header(B-1), 3) H_txs(B), 4) nonce
				block_term = str(log[-1].current_term)
				block_prev_header_hash = str(log[-1].prev_header_hash)
				block_current_transactions_hash = str(log[-1].current_transactions_hash)
				block_nonce = str(log[-1].nonce)				
				# need to hash all 4 things
				prev_header_hash = hash(block_term + block_prev_header_hash + block_current_transactions_hash + block_nonce)
			current_block = Block(prev_header_hash)
		current_block.add_transaction(data)
		 # block is populated --> commit it & create the new block
		if current_block.calculate_number_of_transactions() == 2:
			print("A block has been added to the blockchain.")
			# formulate_block takes in 1 arg (term #)
			current_block.formulate_block(current_term)
			# add block to log
			log.append(current_block)
			print("A log entry has been committed.")
			# each site has its own index, which is just the length of its log 
			# the log length should follow the current log's length
			next_index = {PORTS[0]: len(log), PORTS[1]: len(log), PORTS[2]: len(log)}
			# since block has been added already, reset the variable
			current_block = None

def main():
	global current_port
	global current_money
	global current_status
	threads_recv = []

	current_port = int(sys.argv[1])
	print("current port: ", current_port)
	current_status = FOLLOWER
	port_list = CHANNELS[current_port]
	print("list of ports: ", port_list)
	current_money = BALANCE[current_port]
	print("port balance: ", current_money)

	socket_recv = Socket(TCP_IP, current_port).create_recv_socket()
	for port in port_list:
		objects_socket_send[port] = Socket(TCP_IP, port).create_send_socket()

	while len(objects_socket_recv) != len(port_list):
		objects_socket_recv.append(socket_recv.toggle_connect())

	for object in objects_socket_recv:
		threads_recv.append(Thread(read_socket, (object,)).create_thread())

	time.sleep(random.randint(0, 2500)/1000)
	thread_heartbeat = Thread(leader_alive, ()).create_thread()
	thread_queue = Thread(process, (current_port, )).create_thread()
	thread_task = Thread(threaded, (objects_socket_send,)).create_thread()
	thread_transactions = Thread(create_block, ()).create_thread()
	thread_task.join_thread()
	thread_queue.join_thread()
	thread_heartbeat.join_thread()
	thread_transactions.join_thread()

	for thread in threads_recv:
		thread.join_thread()

	sys.exit()

if __name__ == "__main__":
	main()