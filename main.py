
from __future__ import unicode_literals
import Skype4Py
import datetime
import time



class Client():
    def __init__(self):
        self.skype = Skype4Py.Skype()
        print 'Attaching to Skype Application'
        try:
            self.skype.Attach()
        except Skype4Py.SkypeAPIError as e:
            raise Exception('Could not find Skype Application open or you have not allowed this program to connect to your Skype program')
        print 'Successfully Attached to Skype Application'
        
        self.CurrentUser = self.skype.CurrentUser.Handle
        self.contacts = self.getContacts()
        self.chats = self.getChats()
        
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
        return '[{0} -> {1}]  {2}'.format(datetime.datetime.fromtimestamp(int(Datetime)).strftime('%Y/%m/%d %H:%M:%S'), FullName, Body)




    def UI_chatSelectView(self):
        i = 0
        chatKeys = []
        for chat in self.chats.keys():
            print self.chats[chat] + " : " + str(i)
            chatKeys.append(chat)
            i += 1

        userValidInput = False
        while not userValidInput:
            try:
                userInput = int(raw_input('What chat do you want to view? '))
                if userInput in range(0, i):
                    userValidInput = True
                else:
                    print 'enter a no. between 0 and {0}'.format(i)
            except ValueError:
                print 'enter a valid input'
                userValidInput = False


        return chatKeys[userInput]

    def InitialchatSelected(self, chat):
        print chat
        print self.chats[chat]
        chatMessages = self.skype._DoCommand('GET CHAT {0} CHATMESSAGES'.format(chat)).split('CHATMESSAGES')[1].replace(' ', '').split(',')
        if len(chatMessages) > 200:
            chatMessages = chatMessages[:len(chatMessages)-200]
            print 'Reducing the size of the chat down to 200'
        self.chatIndex = len(chatMessages)
        print 'Chat Index = ' + str(self.chatIndex)
        self.chatId = chat
        self.outputCurrentMessages(chatMessages)
        

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

    def outputCurrentMessages(self, chatMessages):
        chatMessages.reverse()
        for chatMessage in chatMessages:
            try:
                Body=self.skype._DoCommand('GET CHATMESSAGE {0} BODY'.format(chatMessage)).split('BODY')[1]
                Datetime=self.skype._DoCommand('GET CHATMESSAGE {0} TIMESTAMP'.format(chatMessage)).split('TIMESTAMP')[1]
                FullName=self.skype._DoCommand('GET CHATMESSAGE {0} FROM_DISPNAME'.format(chatMessage)).split('FROM_DISPNAME')[1]
                Handle=self.skype._DoCommand('GET CHATMESSAGE {0} FROM_HANDLE'.format(chatMessage)).split('FROM_HANDLE')[1].replace(' ', '')

                if Handle == self.CurrentUser:
                    FullName = "Me"
                print(self.getChatString(Body, Datetime, FullName))
            except Skype4Py.errors.SkypeError as e:
                print(e)
    
    def updateCommand(self, Message, Status):
        if Status == "RECEIVED":
            print 'RECEIVED a new message'
        elif Status == "SENT": # outputs sending twice... so will need check to be in place with a temp var stored globally in the class
            print 'SENT a message'
        elif Status == 'READ':
            print 'READ'
        else:
            print Status

    def getUserStatus(self):
        return ["{0}: {1}".format(self.contacts[k], self.skype._DoCommand('GET USER {0} ONLINESTATUS'.format(k)).split('ONLINESTATUS')[1]) for k in self.contacts]

    def getChatsByName(self):
        chatError = {}
        chatDict = {}
        for k in self.chats.keys():
            temp = self.skype._DoCommand('GET CHAT {0} CHATMESSAGES'.format(k)).split('CHATMESSAGES')[1].replace(' ', '').split(',')
            if len(temp) != 0:
                try:
                    TimeStamp=self.skype._DoCommand('GET CHATMESSAGE {0} TIMESTAMP'.format(temp[0])).split('TIMESTAMP')[1]
                    if self.chats[k] in chatDict.keys():
                        if chatDict[self.chats[k]][1] < TimeStamp:
                            chatDict[self.chats[k]] = [k, TimeStamp]
                    else:
                        chatDict[self.chats[k]] = [k, TimeStamp]
                except:
                    print 'ERROR could not find message data for: {0} = {1}'.format(self.chats[k], k)
                    if str(self.chats[k]) in chatError.keys():
                        chatError[str(self.chats[k])] += 1
                    else:
                        chatError[str(self.chats[k])] = 1

        # gets rid of chats that throw errors
        # potentailly buggy only one version of that chat is broken
        for chatKeyError in chatError.keys():
            chatDict.pop(chatKeyError)
            print 'Deleting ' + chatKeyError + ' from chat list'
                    
        #print '\n'.join(['{0}:{1}'.format(k, chatDict[k]) for k in chatDict.keys()])
        return chatDict

    def UI_selectChat(self):
        chats = self.getChatsByName()
        count = 0
        for k in chats.keys():
            #print '{0}:{1} = {2}'.format(count, k, chats[k])
            print '{0}:{1}'.format(count, k)
            count += 1

        userValidInput = False
        while not userValidInput:
            try:
                userInput = int(raw_input('What chat do you want to select? '))
                if userInput in range(0, count):
                    userValidInput = True
                else:
                    print 'enter a no. between 0 and {0}'.format(count)
            except ValueError:
                print 'enter a valid input'
                userValidInput = False
        return [chats[k] for k in chats.keys()][userInput][0]

    def sendChat(self, chatId):
        print '-------------------------'
        print 'Chat Name: ' + self.chats[chatId]
        #print chatId
        ContinueChat = True
        while ContinueChat:
            msg = raw_input('chat msg: ')
            if raw_input('msg = "' + msg + '" | Confirm (y/n)') == 'y':
                self.skype._DoCommand('CHATMESSAGE {0} {1}'.format(chatId, msg))

            stayInChat = raw_input('\nstay in this chat (y/n)')
            # put this is a loop maybe a some stage
            if stayInChat == 'n':
                ContinueChat = False
    
    def mainTest(self):
        print '\n'.join([k + " = " + self.chats[k] for k in self.chats.keys()])
        print '---------------------------------------------------------'
        print '\n'.join([k + " = " + self.contacts[k] for k in self.contacts.keys()])
        print '---------------------------------------------------------'
        print '\n'.join(self.getUserStatus())
        print '---------------------------------------------------------'

        
    def chatTest(self):
        a = [self.InitialchatSelected(k) for k in self.chats.keys()]


def main():
    
    test = Client()

    def chatMessage():
        test.sendChat(test.UI_selectChat())
    
    def chatViewing():
        test.InitialchatSelected(test.UI_chatSelectView())
        while True:
            time.sleep(5)
            test.UpdatechatSelected()

    def getHelp():
        print 'Aviable Commands:\n-> ' + '\n-> '.join([k for k in commands.keys()])

    def getVersion():
        print 'Version 0.1 WIP'

    def getSkypeApiDocumentation():
        print 'http://www.trynull.com/wp-content/uploads/files/skype4cocoa/public_api_ref.html'

    def getUserStatus():
        print '\n'.join(test.getUserStatus())

    def getContacts():
        print '- ' + '\n- '.join([test.contacts[k] for k in test.contacts.keys()])

    def Quit():
        print 'Closing down application'

    commands = {
        'message':chatMessage,
        'help':getHelp,
        'viewChat':chatViewing,
        'version':getVersion,
        'userStatus':getUserStatus,
        'userContacts':getContacts,
        'quit':Quit
        }
    
    Running = True
    while Running:
        cmd = raw_input(">>>").replace(' ','')
        if cmd in commands.keys():
            commands[cmd]()
            if cmd == 'quit':
                Running = False
        elif len(cmd) > 0:
            print 'Command not found'



if __name__ == "__main__":
    print 'running....'
    main()
