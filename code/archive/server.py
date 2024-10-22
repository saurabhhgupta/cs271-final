import socket 
from threading import Thread 
from SocketServer import ThreadingMixIn 
import time
import threading
import json, sys
import logging
import random
import csv
import copy

REQVOTE = 'RequestVote'
RESVOTE = 'ResponseVote'
APPENDENTRIES = 'AppendEntries'
RESENTRIES = 'ResponseEntries'
CLIREQ = 'ClientRequest'
SHOWREQ = 'ShowRequest'
CONFIGCHANGE = 'ConfigChangeRequest'

CONFIGFILE = 'config.json'

PHASE1 = -1
PHASE2 = -2
YES = 'Yes'
NO = 'No'

STATES = {1: 'FOLLOWER', 2: 'CANDIDATE', 3: 'LEADER'}

class RaftServer():
    def __init__(self, serverId):
        self.serverId = serverId
        self.electionTimer = None
        self.heartbeatTimer = None
        self.voteCount = 0
        self.replicatedIndexCount = {}
        self.logEntries = []
        self.results = {}
        self.oldConfig = None
        self.newConfig = None
        self.commitLock = threading.Lock()
        self.stateChangeLock = threading.Lock()

        self.initParam()
        self.resetElectionTimer()
        self.startServer()


    def initParam(self):
        '''Read from log file and update in memory variables based on last log entry'''
        self.initState()
        self.applyConfig()
        self.initLogEntries()

    def initState(self):
        with open(self.serverId + '_state.json') as state_file:    
            state = json.load(state_file)

        self.state = state['state']
        self.term = state['term']
        self.leaderId = state['leaderId']
        self.votedFor = state['votedFor']
        self.followers = state['followers']
        self.commitIdx = state['commitIdx']
        self.money = state['money']
        # self.money = state['money']
        self.config = state['config']
        

    def initLogEntries(self):
        '''Initialize log related variables from the .log file'''
        
    	if os.path.isfile("saved_state_{}.txt".format(STATION_ID)):
            with open(str(serverId) + '.log') as log_file:
                reader = csv.reader(log_file, delimiter=',', quoting=csv.QUOTE_NONE)
        
                for entry in reader:
                    '''Convert idx, term and money to integers and append to logEntries variable'''
                    entry[0], entry[1], entry[2] = \
                    int(entry[0]), int(entry[1]), int(entry[2])
                    self.logEntries.append(entry)
                    '''Populate the mapping of requestId to its result from log'''
                    self.results[entry[3]] = entry[4]

        '''From lastLog, initialize lastLogIdx and lastLogTerm values'''
        lastLog = self.logEntries[-1] if self.logEntries else None
        if not lastLog:
            lastLog = [-1, 0, None, None, None]
    
        self.lastLogIdx = lastLog[0]
        self.lastLogTerm = lastLog[1]


    def applyConfig(self):
        '''Read from config file and update in memory variables'''

        self.election_timeout = self.config['election_timeout']
        self.heartbeat_timeout = self.config['heartbeat_timeout']
        dcInfo= {'dc_name':self.serverId.upper()}
        self.logger = self.logFormatter(dcInfo)
        totalDcs = len(self.config['datacenters'])
        self.majority = totalDcs/2 + 1


    def logFormatter(self, dcInfo):
        '''Logging info'''
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(dc_name)s: %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger = logging.LoggerAdapter(logger, dcInfo)
        return logger


    def writeLogEntriesToFile(self):
        with open(self.serverId+".log", "w") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONE)
            writer.writerows(self.logEntries)


    def writeStateToFile(self):
        state = {
            "state":self.state,
            "term":self.term,
            "leaderId":self.leaderId,
            "votedFor": self.votedFor,
            "followers":self.followers,
            "commitIdx":self.commitIdx,
            # "money":self.money,
            "config":self.config
        }

        with open(self.serverId +'_state.json', 'w') as fp:
            json.dump(state, fp, indent=4)
        

    ############################# Message forming methods #############################

    def formRequestVoteMsg(self):
        msg = { 
        'RequestVote': {
            'candidateId': self.serverId,
            'term': self.term,
            'lastLogIdx': self.lastLogIdx,
            'lastLogTerm': self.lastLogTerm
            }
        }
        return msg


    def formResponseVoteMsg(self, voteGranted=False):
        msg = { 
        'ResponseVote': {
            'term': self.term,
            'voteGranted': voteGranted,
            'serverId':self.serverId
            }
        }
        return msg


    def formAppendEntriesMsg(self, nextIdx):
        msg = {
        'AppendEntries' : {
            'term': self.term,
            'leaderId': self.serverId,
            'prevLogIdx': self.logEntries[nextIdx-1][0] if nextIdx>0 else -1,
            'prevLogTerm': self.logEntries[nextIdx-1][1] if nextIdx>0 else 0,
            'entries': self.getLogEntries(nextIdx),
            'commitIdx': self.commitIdx
            }
        }
        return msg


    def formResponseEntriesMsg(self, success=False):
        msg = { 
        'ResponseEntries': {
            'term': self.term,
            'followerId':self.serverId,
            'lastLogIdx':self.lastLogIdx,
            'success': success
            }
        }
        return msg


    def formClientResponseMsg(self, success=False, redirect=False, respMsg=None):
        msg = { 
        'ClientResponse': {
            'leaderId': self.leaderId,
            'success': success,
            'redirect':redirect,
            'response':respMsg
            }
        }
        return msg


    def formShowResponseMsg(self, respMsg=None):
        msg = { 
        'ShowResponse': {
            'leaderId': self.leaderId,
            'response':respMsg
            }
        }
        return msg


    def getLogEntries(self, nextIdx):
        '''Send everything from nextIdx to lastIdx; if they are equal, send empty list for heartbeat'''
        return self.logEntries[nextIdx:]

    ############################# Leader election methods #############################

    def resetElectionTimer(self):
        '''Start a timer; when it goes off, start the election'''
        if self.electionTimer:
            self.electionTimer.cancel()

        timeout = random.uniform(self.election_timeout[0], self.election_timeout[1])

        self.electionTimer = threading.Timer(timeout, self.startElection)
        self.electionTimer.start()


    def startElection(self):
        '''Start election only if not already a leader and current server is present in the config'''
        if (not self.state == STATES[3]) and (self.serverId in self.config['datacenters']):
            '''If not already a leader, change to candidate, increment term and req vote'''
            self.voteCount = 0
            self.state = STATES[2]
            self.term += 1
            self.votedFor[self.term] = self.serverId
            self.voteCount += 1
            self.requestVote()
            self.writeStateToFile()
            

    def requestVote(self):
        reqMsg = self.formRequestVoteMsg()
        self.resetElectionTimer()
        for serverId in self.config['datacenters']:
            if serverId == self.serverId:
                continue
            ip, port = self.getServerIpPort(serverId)
            self.sendTcpMsg(ip, port, reqMsg)


    def handleVoteRequest(self, msg):
        grantingVote = False
        ip, port = self.getServerIpPort(msg['candidateId'])

        if msg['candidateId'] not in self.config['datacenters']:
            '''If candidate is not in current cofig, ignore it's vote requests'''
            return

        if msg['term'] > self.term:
            '''Update term if it is lesser than candidate's term'''
            self.term = msg['term']
            self.convertToFollower()

        if msg['term'] >= self.term:
            '''Check if log entries of candidate is good enough to be elected as leader'''
            if (msg['term'] not in self.votedFor) or (self.votedFor[msg['term']] == msg['candidateId']):
                if (msg['lastLogTerm'] > self.lastLogTerm or \
                    (msg['lastLogTerm'] == self.lastLogTerm and msg['lastLogIdx'] >= self.lastLogIdx)):
                    '''Candidate's log is at least as much as voter's log'''
                    respMsg = self.formResponseVoteMsg(voteGranted=True)
                    self.sendTcpMsg(ip, port, respMsg)
                    grantingVote = True
                    self.votedFor[msg['term']] = msg['candidateId']
                    self.convertToFollower()

        self.writeStateToFile()
        if not grantingVote:
            '''If conditions for granting vote failed, respond with "no"'''
            respMsg = self.formResponseVoteMsg(voteGranted=False)
            self.sendTcpMsg(ip, port, respMsg)


    def handleVoteReply(self, msg):
        '''If vote is granted and you get majority of votes, convert to 
        leader else update term and convert to follower.'''
        if msg['voteGranted'] == True:
            self.voteCount += 1
            self.stateChangeLock.acquire()
            try:
                if self.voteCount >= self.majority and self.state != STATES[3]:
                    self.convertToLeader()
            finally:
                self.stateChangeLock.release()

        elif msg['term'] > self.term:
            self.term = msg['term']
            self.convertToFollower()


    def convertToLeader(self):
        self.logger.debug('\nConverting to LEADER.\n')
        self.state = STATES[3]
        self.leaderId = self.serverId
        self.initFollowerDetails()
        self.sendAppendEntriesToAll()
        self.resetHeartbeatTimer()
        self.writeStateToFile()


    ############################# Leader responsibilities methods #############################

    def resetHeartbeatTimer(self):
        '''Start a timer; keep sending hearbeats after it goes off'''
        if self.heartbeatTimer:
            self.heartbeatTimer.cancel()
        self.heartbeatTimer = threading.Timer(self.heartbeat_timeout, self.sendAppendEntriesToAll)
        self.heartbeatTimer.start()


    def sendAppendEntriesToAll(self):
        if self.state == STATES[3]:
            for serverId in self.followers:
                self.sendAppendEntriesMsg(serverId)
            self.resetHeartbeatTimer()


    def sendAppendEntriesMsg(self, serverId, display=True):
        msg = self.formAppendEntriesMsg(self.followers[serverId])
        ip, port = self.getServerIpPort(serverId)
        # if len(msg['AppendEntries']['entries']) == 0:
        display = False
        self.sendTcpMsg(ip, port, msg, display=display)


    def initFollowerDetails(self):
        '''Initialize next index for every follower once the server becomes leader'''
        for serverId in self.config['datacenters']:
            if serverId == self.serverId:
                continue
            if serverId not in self.followers:
                '''Initialize nextIdx for each follower as leader's lastIdx+1.'''
                self.followers[serverId] = self.lastLogIdx + 1


    def handleResponseEntries(self, msg):
        if msg['term'] > self.term:
            '''There is new leader; step down'''
            self.convertToFollower()
        else:
            if msg['success'] == True:
                self.updateReplicationCount(msg)
            else:
                self.retryAppendEntries(msg)

            self.writeStateToFile()


    def retryAppendEntries(self, msg):
        '''Consistency check has failed for this follower.
        Decrement its nextIdx and retry appendEntries RPC'''
        followerId = msg['followerId']
        if followerId in self.followers:
            if self.followers[followerId] > 0:
                self.followers[followerId] -= 1
            self.sendAppendEntriesMsg(followerId)


    def updateReplicationCount(self, msg):
        followerId = msg['followerId']
        if followerId not in self.config['datacenters']:
            '''If a stale follower responds, remove it from the follower list and 
            do not perform any more operation'''
            self.followers.pop(followerId)
            return

        nextIdx = self.followers[followerId]
        
        '''Starting from nextIdx of the follower who responded till its lastIdx, updated 
        replicated count of new entries that hasn't gotten majority yet'''
        while nextIdx <= msg['lastLogIdx']:
            if nextIdx in self.replicatedIndexCount:
                self.replicatedIndexCount[nextIdx] += 1
                if self.replicatedIndexCount[nextIdx] >= self.majority:
                    self.updateCommitIdx(nextIdx)
            nextIdx += 1

        self.followers[followerId] = nextIdx


    def updateCommitIdx(self, nextIdx):
        '''Get the term for the entry that just got majority'''
        logTerm = self.logEntries[nextIdx][1]

        '''If the term of the entry is same as current leader's term, then mark all 
        entries till that entry as committed'''
        if logTerm == self.term:
            self.commitLock.acquire()
            try:
                while self.commitIdx < nextIdx:
                    self.commitIdx += 1
                    self.logger.debug('Updated commited index to %d' %self.commitIdx)
                    if self.commitIdx in self.replicatedIndexCount:
                        self.replicatedIndexCount.pop(self.commitIdx)
                    self.checkAndCommitConfigChange(self.commitIdx)
                    '''Once an entry is commited, update ticket count and respond to client'''
                    self.executeClientRequest(self.commitIdx, respondToClient=True)
                    '''Update the log entry for the committed index with executed as true'''
                    self.updateResult(self.commitIdx, res=YES)
                    self.writeStateToFile()
                    self.writeLogEntriesToFile()
            finally:
                self.commitLock.release()


    def checkAndCommitConfigChange(self, commitIdx):
        cmd, reqId = self.getClientRequestFromLog(self.commitIdx)
        if cmd == PHASE1:
            '''If we get majority for PHASE1, initiate PHASE2'''
            self.handleConfigChange(PHASE2, reqId)
        elif cmd == PHASE2:
            '''If we get majority of PHASE2, reply to client'''
            response = 'Successfully changed configuration.'
            respMsg = self.formClientResponseMsg(success=True, redirect=False, respMsg=response)
            self.replyToClient(reqId, respMsg)

            if self.serverId not in self.config['datacenters']:
                self.sendAppendEntriesToAll()
                time.sleep(2)
                '''If current server is leader and it is not in new config, make it a follower'''
                self.convertToFollower()
                self.leaderId = None


    ############################# Follower functionalities methods #############################

    def handleAppendEntries(self, msg):
        '''Reset election timer as leader is alive'''
        success = False
        if self.term > msg['term']:
            '''Invalid leader; just return failure RPC to update stale leader'''
            success = False

        else:
            self.term = msg['term']
            self.leaderId = msg['leaderId']
            self.convertToFollower()

            '''Perform consistency check on logs of follower and leader'''
            if self.lastLogIdx < msg['prevLogIdx']:
                '''Missing entries case: send failure so that leader decrements next index and retries'''
                success = False

            else:
                if msg['prevLogIdx'] >= 0 and self.logEntries[msg['prevLogIdx']][1] != msg['prevLogTerm']:
                    '''Inconsistent entries case: At prevLogIdx, follower's and leader's terms don't match.
                    Send failure so that leader decrements next idx and retries'''
                    success = False
                else:
                    '''Success case: Keep entries only till prevLogIdx, to that append the newly sent entries'''
                    self.logEntries = self.logEntries[:msg['prevLogIdx'] + 1]
                    self.logEntries.extend(msg['entries'])
                    if len(msg['entries']) > 0:
                        self.lastLogIdx = len(self.logEntries)-1
                        self.lastLogTerm = self.logEntries[self.lastLogIdx][1]
                        self.logger.debug('\nAppending new entries %s to local log.'%repr(msg['entries']))
                        self.checkForConfigChange(msg['entries'])
                    success = True
                    if msg['commitIdx'] > self.commitIdx:
                        self.updateCommitIdxOfFollower(msg['commitIdx'])

                    if len(msg['entries']) > 0:
                        self.logger.debug('Updated (lastLogIdx, lastLogTerm) to (%d, %d)\n' \
                        %(self.lastLogIdx, self.lastLogTerm))

        if len(msg['entries']) > 0 or success==False:
            '''Respond only for msgs that are not heartbeats'''
            respMsg = self.formResponseEntriesMsg(success=success)
            ip, port = self.getServerIpPort(msg['leaderId'])
            self.sendTcpMsg(ip, port, respMsg)

        self.writeStateToFile()
        self.writeLogEntriesToFile()


    def updateCommitIdxOfFollower(self, newCommitIdx):
        '''Update commit idx and state machine of follower'''
        self.commitLock.acquire()
        try:
            while self.commitIdx < newCommitIdx:
                self.commitIdx += 1
                self.logger.debug('Updated commited index to %d' %self.commitIdx)
                '''Once an entry is commited, update ticket count and respond to client'''
                self.executeClientRequest(self.commitIdx)
                '''Update the log entry for the committed index with executed as true'''
                self.updateResult(self.commitIdx, res=YES)
                self.writeStateToFile()
                self.writeLogEntriesToFile()
        finally:
            self.commitLock.release()


    def convertToFollower(self):
        self.state = STATES[1]
        self.voteCount = 0
        self.followers = {}
        self.replicatedIndexCount = {}
        if self.heartbeatTimer:
            '''Cancel heartbeat timer once it converts to follower'''
            self.heartbeatTimer.cancel()
        self.resetElectionTimer()
        self.writeStateToFile()

    ############################# Client request methods #############################

    def validRequest(self, requestedmoney):
        '''Chech if there enough money to serve the clients request'''
        if requestedmoney <= self.money:
            return True
        return False


    def handleClientRequest(self, recvMsg, msg):
        if not self.state == STATES[3]:
            '''This server is not leader; reply client with redirect message'''
            response = 'Current leader is %s. Please redirect request to server %s' % (self.leaderId, self.leaderId)
            respMsg = self.formClientResponseMsg(success=False, redirect=True, respMsg=response)
            self.replyToClient(msg['reqId'], respMsg)

        else:
            if self.validRequest(msg['money']):
                # ! Line below should be +=, not =+ like originally...
                self.lastLogIdx += 1
                self.lastLogTerm = self.term
                entry = self.getNextLogEntry(msg['money'], msg['reqId'])
                self.logEntries.append(entry)
                self.results[msg['reqId']] = NO
                '''Initialize count for this index as 1 in replicatedIndexCount variable'''
                self.replicatedIndexCount[self.lastLogIdx] = 1
                self.sendAppendEntriesToAll()
                self.writeLogEntriesToFile()
            else:
                '''Client requested too many money; repond with appropriate message'''
                response = 'Total money available: ' + str(self.money) + '.'
                response += ' money requested should be less that total money available.'
                respMsg = self.formClientResponseMsg(success=False, redirect=False, respMsg=response)
                self.replyToClient(msg['reqId'], respMsg)


    def getNextLogEntry(self, command, reqId):
        '''Get the format of how new log entry should be'''
        return [self.lastLogIdx, self.term, command, reqId, NO]


    def updateResult(self, logIdx, res=NO):
        '''Update the result part of entry for the log at passed idx'''
        self.logEntries[logIdx][4] = res
        reqId = self.logEntries[logIdx][3]
        self.results[reqId] = res


    def executeClientRequest(self, idx, respondToClient=False):
        '''Actual fucntion that decrements no. of money in the pool.
        This fucntion is called only when majority of the followers have responded.'''

        requestedmoney, reqId = self.getClientRequestFromLog(idx)
        if requestedmoney > 0:
            self.money -= requestedmoney

            if respondToClient:
                response = 'Successfully purchased %s money.' % requestedmoney    
                respMsg = self.formClientResponseMsg(success=True, redirect=False, respMsg=response)
                self.replyToClient(reqId, respMsg)


    def handleShowCommand(self, msg):
        response = '\nThe current number of avaliable money are: %d\n' %(self.money)
        response += 'Current log present on server %s is:\n' %(self.serverId)
        
        for entry in self.logEntries:
            cmd = entry[2]
            if cmd == -1:
                logResp = '[' + str(entry[0]) + ']: Config change (old + new).\n'
            elif cmd == -2:
                logResp = '[' + str(entry[0]) + ']: Config change (new).\n'
            else:
                clientId = entry[3].split(':')[0]
                logResp = '[' + str(entry[0]) + ']: Client %s bought %d money successfully.\n' %(clientId, cmd)

            response += logResp
        respMsg = self.formShowResponseMsg(respMsg=response)
        self.replyToClient(msg['reqId'], respMsg, display=False)


    def isRequestExecuted(self, msgType, msg):
        '''Check if the client request is already executed; if is it, just send
        the appropriate response to client and return true; else return false'''
        reqId = msg['reqId']
        if reqId in self.results:
            '''If the request was already taken, don't do anything with it'''
            if self.results[reqId] == YES:
                '''If the command was already executed, send success message to client'''
                if msgType == CONFIGCHANGE:
                    response = 'Successfully changed configuration.'
                else:
                    response = 'Successfully purchased %s money.' %msg['money']
                respMsg = self.formClientResponseMsg(success=True, redirect=False, respMsg=response)
                self.replyToClient(reqId, respMsg)
            return True

        return False


    ############################# Config change methods #############################

    def handleConfigChange(self, phase, reqId):
        '''Add entry to log, update config and send AppendEntriesRPC to all'''
        self.lastLogIdx += 1
        self.lastLogTerm = self.term
        entry = self.getNextLogEntry(phase, reqId)
        self.logEntries.append(entry)
        '''Initialize count for this index as 1 in replicatedIndexCount variable'''
        self.replicatedIndexCount[self.lastLogIdx] = 1
        self.updateConfig(phase)
        self.sendAppendEntriesToAll()
        self.writeLogEntriesToFile()


    def updateConfig(self, phase):
        '''For PHASE1 read the changed config from file and store in a variable.
        For PHASE2 just move to the stored values'''
        if phase == PHASE1:
            self.oldConfig = copy.deepcopy(self.config)
            self.readAndApplyNewConfig()
        else:
            self.moveToNewConfig()

        self.writeStateToFile()


    def readAndApplyNewConfig(self):
        '''Read from config file and update in memory variables'''
        with open(CONFIGFILE) as config_file:    
            self.newConfig = json.load(config_file)

        '''From the newly read config, update my current config such that it
        is old + new config'''
        for serverId in self.newConfig['datacenters']:
             if serverId not in self.config['datacenters']:
                self.config['datacenters'].append(serverId)

        if self.state == STATES[3]:
            '''If the server is current leader, it should add newly added followers to the 
            follower list and set their nextIdx'''
            self.initFollowerDetails()

        self.config['clients'] = self.newConfig['clients']
        oldDcs = len(self.oldConfig['datacenters'])
        newDcs = len(self.newConfig['datacenters'])
        self.majority = (oldDcs+newDcs)/2 


    def moveToNewConfig(self):
        '''Since newConfig contains the right config, move current config to new one
        and update majority'''
        if self.newConfig:
            self.config['datacenters'] = copy.deepcopy(self.newConfig['datacenters'])
        totalDcs = len(self.config['datacenters'])
        self.majority = (totalDcs)/2 + 1
        self.oldConfig, self.newConfig = None, None


    def checkForConfigChange(self, newEntries):
        '''Go through all newly sent entries, check if any of them are config changes
        for phase1 or phase2, and update config accordingly'''
        for entry in newEntries:
            cmd = entry[2]
            if cmd == PHASE1:
                self.updateConfig(PHASE1)
            elif cmd == PHASE2:
                self.updateConfig(PHASE2)

    ############################# Misc methods #############################

    def sendTcpMsg(self, ip, port, msg, display=True):
        try:
            tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcpClient.settimeout(1)
            tcpClient.connect((ip, port))
            tcpClient.send(json.dumps(msg))
            if display:
                logMsg = 'Sent message to: (%s, %d). Message is: %s' %(ip, port, msg)
                self.logger.debug(logMsg)

        except Exception as e:
            '''When a site is down, tcp connect fails and raises exception; catching and 
            ignoring it as we don't care about sites that are down'''
            pass
        

    def replyToClient(self, reqId, respMsg, display=True):
        clientId = reqId.split(':')[0]
        ip, port = self.getClientIpPort(clientId)
        self.sendTcpMsg(ip, port, respMsg, display=display)


    def getServerIpPort(self, serverId):
        '''Get ip and port on which server is listening from config'''
        return self.config['dc_addresses'][serverId][0], self.config['dc_addresses'][serverId][1]


    def getClientIpPort(self, clId):
        '''Get ip and port on which client is listening from config'''
        return self.config['clients'][clId][0], self.config['clients'][clId][1]


    def extractTermFromLog(self, logIdx):
        '''Implement from log'''
        return self.lastLogTerm


    def getClientRequestFromLog(self, logIdx):
        return self.logEntries[logIdx][2], self.logEntries[logIdx][3] 


    # Multithreaded Python server : TCP Server Socket Thread Pool
    class ConnectionThread(Thread):
        def __init__(self, conn, ip, port, raft): 
            Thread.__init__(self) 
            self.ip = ip
            self.port = port
            self.conn = conn
            self.raft = raft


        def run(self): 
            display = True
            conn, recvMsg = self.conn, self.conn.recv(2048)
            
            msgType, msg = self.parseRecvMsg(recvMsg)

            if msgType == APPENDENTRIES:
                display = False

            elif msgType == RESENTRIES and msg['success'] == True:
                display = False

            if display:
                logMsg = 'Received message from: (%s:%d). Message is: %s' %(self.ip, self.port, recvMsg)
                self.raft.logger.debug(logMsg)
    
            if msgType == SHOWREQ:
                self.raft.handleShowCommand(msg)
            elif msgType == REQVOTE:
                self.raft.handleVoteRequest(msg)
            elif msgType == RESVOTE:
                self.raft.handleVoteReply(msg)
            elif msgType == APPENDENTRIES:
                self.raft.handleAppendEntries(msg)
            elif msgType == RESENTRIES and self.raft.state == STATES[3]:
                '''Only leader should handle response entries'''
                self.raft.handleResponseEntries(msg)
            elif msgType == CLIREQ:
                if not self.raft.isRequestExecuted(msgType, msg):
                    self.raft.handleClientRequest(recvMsg, msg)
            elif msgType == CONFIGCHANGE:
                if not self.raft.isRequestExecuted(msgType, msg):
                    self.raft.handleConfigChange(PHASE1, msg['reqId'])

            conn.close() 
            sys.exit()


        def parseRecvMsg(self, recvMsg):
            recvMsg = json.loads(recvMsg)
            msgType, msg = recvMsg.keys()[0], recvMsg.values()[0]
            return msgType, msg


    def startServer(self):
        ip, port = self.getServerIpPort(self.serverId)

        tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        tcpServer.bind((ip, port))

        print 'Server ready to listen on (%s:%d)' %(ip, port)
        while True: 
            tcpServer.listen(4) 
            (conn, (cliIP,cliPort)) = tcpServer.accept()
            newthread = self.ConnectionThread(conn, cliIP, cliPort, self) 
            newthread.start()
    
 
serverId = sys.argv[1]
delay = int(sys.argv[2])
time.sleep(delay)
raftSrvr = RaftServer(serverId)