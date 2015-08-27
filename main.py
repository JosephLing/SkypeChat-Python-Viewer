
from __future__ import unicode_literals
import datetime
import time
import logging
import os
__version__ = 0.1
try:
    import Skype4Py
except ImportError:
    raise ImportError( 'Make sure that you have Skype4Py installed https://pypi.python.org/pypi/Skype4Py/')

class Client():
    def __init__(self):
        LEVELS = { 'debug':logging.info,
            'info':logging.INFO,
            'warning':logging.WARNING,
            'error':logging.ERROR,
            'critical':logging.CRITICAL,
            }
        #TODO: play around with this when I look into the code behind it FORMAT = '%(filename)s %(asctime)-15s %(user)-8s %(message)s'
        level_name = "info" #TODO: config
        logging.basicConfig(level=LEVELS.get(level_name, logging.NOTSET)) # ,format=FORMAT
        self.skype = Skype4Py.Skype()
        logging.info('Attaching to Skype Application')
        try:
            self.skype.Attach()
        except Skype4Py.SkypeAPIError as e:
            logging.error('Could not find Skype Application open or you have not allowed this program to connect to your Skype program')
        logging.info('Successfully Attached to Skype Application')

        self.CurrentUser = self.skype.CurrentUser.Handle
        self.contacts = self.getContacts()

        self.chats = self.getChats()


        configData = self._getConfigData()
        self.initailMessageCount = int(configData['initailMessageCount'])
        self.keyboardInterruptToExitChat = bool(configData['keyboardInterruptToExitChat'])
        self.chatCheckClock = int(configData['chatCheckClock'])

        # Bot stuff
        self.botCommands = {}
        self.botUserCommands = {}
        self.botCommandsEnabled = bool(configData['botCommandsEnabled'])
        self.botCommandsEnabledUser = bool(configData['botCommandsEnabledUser'])

    def _getConfigData(self):
        print os.path.dirname(os.path.realpath(__file__))
        # path = '/'.join(__file__.split('/')[:-1]) + '/config.txt'
        path = os.path.dirname(os.path.realpath(__file__)) + '/config.txt'
        logging.info('Getting config file data: ' + path)
        configData = {}
        try:
            filedata = open(path, 'r')
        except IOError:
            filedata = None
        if not filedata is None:
            configData = dict([line.replace('\n','').replace(' ', '').split('=') for line in filedata.readlines()[1:]])
            if configData['version'] != str(__version__):
                logging.warning("Config file is not the save version as the script")

        else:
            logging.warning('Config being set to default values as no config file found at ' + path)
            configData['botCommandsEnabled'] = False
            configData['botCommandsEnabledUser'] = False
            configData['initailMessageCount'] = 200
            configData['chatCheckClock'] = 2
            configData['keyboardInterruptToExitChat'] = True
        return configData

    def getChatPeople(self, ChatName):
        Users = []
        for user in ChatName.split(";")[0].replace("#", "").replace('$','').split("/"):
            try:
                Users.append(self.contacts[user])
            except KeyError:
                Users.append('Unkown Contact') # for contacts/friends that we don't know but still can be in group chats
        Users.sort() # so when sorting out chats where its Me, Other person and Other person, Me are acutally the same chat
        return Users


    def getContacts(self):
        contacts = {self.CurrentUser : "Me"}
        for contact in self.skype.Friends:
            if contact.FullName is None or contact.FullName == '':
                contacts[contact.Handle] = contact.Handle
            else:
                contacts[contact.Handle] = contact.FullName
        return contacts

    def getChats(self):
        chats = self.skype._DoCommand('SEARCH CHATS')[5:].replace(' ','').split(',')
        ChatDict = {}
        for chat in chats:
            temp = self.skype._DoCommand('GET CHAT {0} TOPIC'.format(chat)).split('TOPIC')[1]
            if len(temp) == 1:
                ChatDict[chat] = ', '.join(self.getChatPeople(chat))
            else:
                ChatDict[chat] = temp

        return ChatDict

    def getChatNameForMessage(self, Message):
        return 'Chat: ' + ', '.join(self.chats[Message.ChatName])

    def getChatString(self, Body, Datetime, FullName):
        return '{0} [{1}]  {2}'.format(datetime.datetime.fromtimestamp(int(Datetime)).strftime('%Y/%m/%d %H:%M:%S'), FullName.replace(' ', ''), Body)

    def getUserChatString(self, Body, Datetime, FullName):
        return '{0} <{1}>{2}'.format(datetime.datetime.fromtimestamp(int(Datetime)).strftime('%Y/%m/%d %H:%M:%S'), FullName.replace(' ', ''), Body)


    def UI_chatSelectView(self):
        i = 0
        chatKeys = []
        for chat in self.chats.keys():
            print self.chats[chat] + " : " + str(i)
            chatKeys.append(chat)
            i += 1

        userInput = self.validateChatId(i)
        if userInput is None:
            return None
        else:
            return chatKeys[userInput]

    def InitialchatSelected(self, chat):
        if not chat is None:
            print chat
            print self.chats[chat]
            chatMessages = self.skype._DoCommand('GET CHAT {0} CHATMESSAGES'.format(chat)).split('CHATMESSAGES')[1].replace(' ', '').split(',')
            if len(chatMessages) > self.initailMessageCount:
                chatMessages = chatMessages[:len(chatMessages)-self.initailMessageCount]
                print 'Reducing the size of the chat down to {0}'.format(self.initailMessageCount)
            self.chatIndex = len(chatMessages)
            logging.info('Chat Index = ' + str(self.chatIndex))
            self.chatId = chat
            self.outputCurrentMessages(chatMessages, live=False)

    def outputCurrentMessages(self, chatMessages, live=True):
        chatMessages.reverse()
        if live:
            for chatMessage in chatMessages:
                try:
                    Body=self.skype._DoCommand('GET CHATMESSAGE {0} BODY'.format(chatMessage)).split('BODY')[1]
                    Datetime=self.skype._DoCommand('GET CHATMESSAGE {0} TIMESTAMP'.format(chatMessage)).split('TIMESTAMP')[1]
                    FullName=self.skype._DoCommand('GET CHATMESSAGE {0} FROM_DISPNAME'.format(chatMessage)).split('FROM_DISPNAME')[1]
                    Handle=self.skype._DoCommand('GET CHATMESSAGE {0} FROM_HANDLE'.format(chatMessage)).split('FROM_HANDLE')[1].replace(' ', '')

                    if Handle == self.CurrentUser:
                        FullName = "Me"
                        if self.botCommandsEnabledUser:
                            self.botRunUserCommands(Body, Datetime)
                        print(self.getUserChatString(Body, Datetime, FullName))
                    else:
                        print(self.getChatString(Body, Datetime, FullName))
                        if self.botCommandsEnabled:
                            self.botRunCommand(Body, Handle, Datetime)
                except Skype4Py.errors.SkypeError as e:
                    print(e)
        else:
            # Bluck print statement but as still in python 2 no endWith != "\n" option available
            output = ""
            print "Loading chat..."
            for chatMessage in chatMessages:
                try:
                    Body=self.skype._DoCommand('GET CHATMESSAGE {0} BODY'.format(chatMessage)).split('BODY')[1]
                    Datetime=self.skype._DoCommand('GET CHATMESSAGE {0} TIMESTAMP'.format(chatMessage)).split('TIMESTAMP')[1]
                    FullName=self.skype._DoCommand('GET CHATMESSAGE {0} FROM_DISPNAME'.format(chatMessage)).split('FROM_DISPNAME')[1]
                    Handle=self.skype._DoCommand('GET CHATMESSAGE {0} FROM_HANDLE'.format(chatMessage)).split('FROM_HANDLE')[1].replace(' ', '')

                    if Handle == self.CurrentUser:
                        FullName = "Me"
                        output += self.getUserChatString(Body, Datetime, FullName) + "\n"
                    else:
                        output += self.getChatString(Body, Datetime, FullName) + "\n"
                except Skype4Py.errors.SkypeError as e:
                    print(e)
            print output

    def UpdatechatSelected(self):
        if self.chatIndex is None:
            raise Exception("self.chatIndex is not defined make sure to run self.InitialchatSelected before running")

        if self.chatId is None:
            raise Exception("self.chatId is not defined make sure to run self.InitialchatSelected before running")

        chatMessages = self.skype._DoCommand('GET CHAT {0} CHATMESSAGES'.format(self.chatId)).split('CHATMESSAGES')[1].replace(' ', '').split(',')
        #print 'UPDATE Chat Index = ' + str(self.chatIndex)
        old_chatMessagesLength = len(chatMessages)
        chatMessages = chatMessages[0:len(chatMessages)-self.chatIndex]
        if len(chatMessages) != 0:
            self.chatIndex = self.chatIndex + (old_chatMessagesLength - self.chatIndex)
            #print 'VALUE RESET Chat Index = ' + str(self.chatIndex)
        self.outputCurrentMessages(chatMessages)


    def botRunUserCommands(self, bodyMessage, timeStamp):
        if bodyMessage in self.botUserCommands.keys():
            self.botUserCommands[bodyMessage](timeStamp)

    def botRunCommand(self, bodyMessage, Handle, fullName, timeStamp):
        if bodyMessage in self.botCommands.keys():
            self.botCommands[bodyMessage](Handle, fullName, timeStamp)

    def getUserStatus(self):
        return ["{0}: {1}".format(self.contacts[k], self.skype._DoCommand('GET USER {0} ONLINESTATUS'.format(k)).split('ONLINESTATUS')[1]) for k in self.contacts]

    def getMostRecentChats(self):
        chatError = {}
        chatDict = {}
        for k in self.chats.keys():
            temp = self.skype._DoCommand('GET CHAT {0} CHATMESSAGES'.format(k)).split('CHATMESSAGES')[1].replace(' ', '').split(',')
            if len(temp) != 0:
                TimeStamp = 0
                try:
                    TimeStamp=self.skype._DoCommand('GET CHATMESSAGE {0} TIMESTAMP'.format(temp[0])).split('TIMESTAMP')[1]
                except Skype4Py.SkypeError:
                    logging.info('could not find message data for: {0} = {1}'.format(self.chats[k], k))
                    if str(self.chats[k]) in chatError.keys():
                        chatError[self.chats[k]] += 1
                    else:
                        chatError[self.chats[k]] = 1

                if self.chats[k] in chatDict.keys() and TimeStamp != 0:
                    if chatDict[self.chats[k]][1] < TimeStamp:
                        chatDict[self.chats[k]] = [k, TimeStamp]
                        if self.chats[k] in chatError.keys():
                            chatError.pop(self.chats[k])
                            logging.info('Found message data for: ' + self.chats[k])
                else:
                    chatDict[self.chats[k]] = [k, TimeStamp]

        for chatKeyError in chatError.keys():
            chatDict.pop(chatKeyError)
            logging.info('Deleting ' + chatKeyError + ' from chat list')

        #print '\n'.join(['{0}:{1}'.format(k, chatDict[k]) for k in chatDict.keys()])
        return chatDict

    def validateChatId(self, maxCount, Tries=5):
        userValidInput = False
        while not userValidInput and Tries > 0:
            try:
                userInput = int(raw_input('What chat do you want to select? '))
                if userInput in range(0, maxCount):
                    userValidInput = True
                else:
                    Tries -= 1
                    print 'enter a no. between 0 and {0}'.format(maxCount)
            except ValueError:
                Tries -= 1
                print 'enter a valid input'
                userValidInput = False
        print userInput
        if userValidInput:
            return userInput
        else:
            return None

    def UI_selectChat(self, chats=None):
        if chats is None:
            chats = self.getMostRecentChats()
        count = 0
        for k in chats.keys():
            #print '{0}:{1} = {2}'.format(count, k, chats[k])
            print '{0}:{1}'.format(count, k)
            count += 1

        userInput = self.validateChatId(count)
        print userInput
        if not userInput is None:
            return [chats[k] for k in chats.keys()][userInput][0]
        else:
            return None

    def sendChat(self, chatId):
        print chatId
        if chatId is None:
            ContinueChat = False
        else:
            ContinueChat = True
        print '-------------------------'
        while ContinueChat:
            print 'Chat Name: ' + self.chats[chatId]
            msg = raw_input('chat msg: ')
            if raw_input('msg = "' + msg + '" | Confirm (y/n)') == 'y':
                self.skype._DoCommand('CHATMESSAGE {0} {1}'.format(chatId, msg))
            stayInChat = raw_input('\nstay in this chat (y/n)')
            if stayInChat == 'n':
                ContinueChat = False

    def cmd_updateViewChat(self):
        if self.keyboardInterruptToExitChat:
            try:
                while True:
                    time.sleep(self.chatCheckClock)
                    self.UpdatechatSelected()
            except KeyboardInterrupt:
                print 'Exiting chat'
        else:
            while True:
                time.sleep(self.chatCheckClock)
                self.UpdatechatSelected()

    def cmd_viewMostRecentChats(self):
        self.InitialchatSelected(self.UI_selectChat())
        print '----update mode---'
        self.cmd_updateViewChat()

    def cmd_viewAllChats(self):
        tempChat = self.getChats()
        self.InitialchatSelected(self.UI_chatSelectView())
        print '----update mode---'
        self.cmd_updateViewChat()

    def cmd_sendMessage(self):
        self.sendChat(self.UI_selectChat())

    def cmd_getVersion(self):
        print "Version: " + str(__version__)

    def cmd_getContacts(self):
        print '- ' + '\n- '.join([self.contacts[k] for k in self.contacts.keys()])

    def cmd_main(self):
        self._Running = True
        def Quit():
            print 'Closing down application'
            self._Running = False

        def getHelp():
            print 'Aviable Commands:\n-> ' + '\n-> '.join([k for k in commands.keys()])

        commands = {
            'message':self.cmd_sendMessage,
            'help':getHelp,
            'viewChat':self.cmd_viewAllChats,
            'version':self.cmd_getVersion,
            'viewMostRecentChat':self.cmd_viewMostRecentChats,
            'userContacts':self.cmd_getContacts,
            'quit':Quit
            }
        print '\n\n-----------------'
        while self._Running:
            cmd = raw_input(">>>").replace(' ','')
            if cmd in commands.keys():
                commands[cmd]()
            elif len(cmd) > 0:
                print 'Command not found'

def main():
    test = Client()
    test.cmd_main()

if __name__ == "__main__":
    print 'running....'
    main()
