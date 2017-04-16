#!/usr/bin/env python3

import urllib.request
import json
import os
import time
import sys
from bs4 import BeautifulSoup, Tag

#STANDARD SETTINGS###################
#MODIFY SETTINGS IN settings.py #####
#END SETTINGS###########################


#Load Custom Settings File
s,settingsfile = dict(),False
if os.path.exists('settings.json'):
   settingsfile = 'settings.json'
if settingsfile:
   with open(settingsfile) as infile:
      s = json.load(infile)
#Add Standard Settings
stdsettings = {
   'gameURL':'http://webdiplomacy.net/board.php?',
   'gameID':'1234',
   'ONESHOT':True,
   'WAITTIME':5,
   'TURNWARNING':12,
   'TURNFATAL':6,
   'ANNOUNCESTATUSCHANGE':True,
   'SAVEPATH':'',
   'NOTIFYBYMAIL':False,
   'NOTIFYBYSTDOUT':True,
   'notify':{'message':{},'turn':{},'warning':{}}
   }
for st in stdsettings:
   if st not in s:
      s[st] = stdsettings[st]

def announce(text,type=None):
   #Here you could implement a new function for notifying according to your needs.
   if s['NOTIFYBYMAIL']:
      import notify_mail
      who = get_recipient(type)
      if who: notify_mail.mail_me(who,text)
   if s['NOTIFYBYSTDOUT']:
      print(text)
   return

def get_recipient(mytype):
   who = list()
   try:
      if 'WDA_stop_all' in s['notify'][mytype]:
         if s['notify'][mytype]['WDA_stop_all'] == True:
            return False
      for u in s['notify'][mytype]:
         if s['notify'][mytype][u] == True:
            who.append(u)
   except KeyError:
      return False

   recipients = list()
   for i,w in enumerate(who):
      if w in s['users']:
         recipients.append(s['users'])
   return recipients

###BEAUTIFUL SOUP HTML###################################################################
def GetPage():
   global soup
   try:
      with urllib.request.urlopen(s['gameURL']+'gameID='+s['gameID']) as response:
         html = response.read()
   except urllib.error.URLError as e:
      announce("There was an error fetching the page:\n{0!s}".format(e),'error')
      return False
   soup = BeautifulSoup(html, 'html.parser')
   return True

def PlayerStatus():
   '''
   Extracts the countries and their status from the left side of the game panel and
   returns a dict of dicts of countries and their status.
   {Country1: {'status':status}, Country2: {'status':status},...}
   '''
   orders = soup.findAll('td', {'class':'memberLeftSide'})
   r = dict()
   for o in orders:
      spans = o.findAll('span')
      status,country = False,False
      for span in spans:
         if 'StatusIcon' in "".join(span['class']):
            img = span.find('img')
            if(img): status = img['alt']
            else: status = span.contents[0]
         elif 'country' in "".join(span['class']):
            country = span.contents[0]
         if 'Defeated' in "".join(span['class']):
            status = 'Defeated'
         if not status and 'memberStatus' in "".join(span['class']):
            status = span['class'][1].split('memberStatus')[1]
      if country and status:
         r[country] = {'status':status}
   return r

def GameTurn():
   '''
   Extracts turn specific information from the title bar,
   returns a dict with game date, phase, status and remaining time.
   '''
   r = dict()
   titlebar = soup.find('div', {'class':'titleBar'})
   if not titlebar: return {}
   r['gameName'] = titlebar.find('span', {'class':'gameName'}).contents[0]
   r['gamedate'] = titlebar.find('span', {'class':'gameDate'}).contents[0]
   r['gamephase'] = titlebar.find('span', {'class':'gamePhase'}).contents[0]
   state = ("".join(str(i) for i in titlebar.find('span', {'class':'gameTimeRemaining'}).contents))
   if 'Paused' in state: r['state'] = 'Paused'
   elif 'Finished' in state: r['state'] = 'Finished'
   timeinfo = titlebar.find('span', {'class':'timeremaining'})
   if timeinfo:
      r['timeremaining'] = timeinfo.contents[0]
      r['unixtime'] = timeinfo['unixtime']
      r['unixtimefrom'] = timeinfo['unixtimefrom']
      r['unixdiff'] = (int(timeinfo['unixtime'])-int(timeinfo['unixtimefrom']))/3600 #in hours
   return r

def Messages():
   '''
   Extracts a list of messages sent and their date.
   Stores as chronological list.
   Returns the list of messages and additionally a dict of countries:
   countries = {'Country1':'England','Country2:'France',...}
   '''
   countries,messages = dict(),list()

   #Extract country information
   countrylist = soup.find('div', {'class':'chatboxMembersList'})
   if countrylist:
      for spans in countrylist:
         for t in spans:
            if not isinstance(t, Tag): continue
            if 'country' in t['class'][0]:
               countries[t['class'][0]] = t.contents[0]
   else: countries = {}

   #Get messages
   chatbox = soup.find('div', {'class':'chatbox', 'id':'chatboxscroll'})
   if not chatbox: return [],countries
   mgs = chatbox.findAll('tr')
   for m in mgs:
      got = dict()
      mytime = m.find('span', {'class':'timestamp'})
      if(mytime):
         got['time'] = mytime.contents[0]
      for td in m.findAll('td'):
         if 'country' in "".join(td['class']):
            text = ""
            who = td['class'][1]
            if (who in countries):
               who = countries[who]
            for child in td:
               if not child.name == 'strong':
                  if str(child).startswith(": "):
                     text += ''.join(str(child)[2:])
                  else:
                     text += ''.join(child)
            got['text'] = text
            got['who'] = who
            continue
      messages.append(got)
   return messages,countries
#########################################################################################

def DumpFile(data):
   '''
   Saves information in json file
   '''

   a = ['message','turn','warning']
   data['notify'] = dict()
   for x in a:
      data['notify'][x] = s['notify'][x]

   #if os.path.exists(s['SAVEPATH']+'db{0!s}.json'.format(s['gameID'])):
   #   os.rename(s['SAVEPATH']+'db{0!s}.json'.format(s['gameID']), s['SAVEPATH']+'db{0!s}_old.json'.format(s['gameID']))
   with open(s['SAVEPATH']+'db{0!s}.json'.format(s['gameID']), 'w') as outfile:
      json.dump(data, outfile)

def LoadFile(filename):
   with open(filename) as infile:
      F = json.load(infile)
   s['notify'] = F['notify']
   return F

def CompareStatus(current,past):
   '''
   Checks if status has changed compared to last fetch
   '''
   if len(current) != len(past):
      print("Different length of Status")
   else:
      for s in current:
         if (s in past) and current[s]['status'] != past[s]['status']:
            announce("{0!s}'s status has changed from {1!s} to {2!s}".format(s,past[s]['status'],current[s]['status']),'status')
   return

def CompareTurn(current,past):
   '''
   Checks if we are in a new turn, compared to last fetch
   '''
   if current['gamedate'] != past['gamedate']:
      announce('The game "{1!s}" advanced to a new turn! It is now {0!s}.'.format(current['gamedate'],current['gameName']),'turn')
      return True
   elif current['gamephase'] != past['gamephase']:
      announce('The Game "{2!s}" advanced to a new phase! It is now in the {0!s} phase of {1!s}.'.format(current['gamephase'],current['gamedate'],current['gameName']),'turn')
      return True
   return False

def CompareMessages(current,past):
   #if len(current) == len(past) and current[-1] == past[-1]: #No new messages
   #   print("seems like no new message appeared")
   #   return False
   for m in current:
      if m not in past:
            #Check if its a WebDipAnn command
         if m['text'].startswith('WDA: '):
            cmd = m['text'][5:].split(' ')
            if len(cmd) != 3: continue #break if not enough arguments
            if cmd[1] == 'notify':
               if cmd[0] == 'admin':
                  if cmd[2] == 'stop':
                     for x in s['notify']:
                        s['notify'][x]['WDA_stop_all'] = True
                  elif cmd[2] == 'reset':
                     for x in s['notify']:
                        s['notify'][x]['WDA_stop_all'] = False
               elif cmd[0] in ['start','stop']:
                  if cmd[0] == 'start': cmd[0] = True
                  elif cmd[0] == 'stop': cmd[0] = False
                  cmd[2] = cmd[2].lstrip('[').rstrip(']')
                  for x in cmd[2].split(','):
                     if x not in s['notify'] and x != 'all':
                        s['notify'][x] = dict() #Generate new entry
                     if x in s['notify']:
                        s['notify'][x][m['who']] = cmd[0]
                     if x == 'all':
                        for y in s['notify']:
                           s['notify'][y][m['who']] = cmd[0]
         else:
            announce('New message from {0!s}: "{1!s}"'.format(m['who'],m['text']),'message')
   return


def TimerWarning(current):
   '''
   Warns if time left is below threshold
   '''
   if 'unixdiff' not in current['gameturn']: return
   if current['gameturn']['gamephase'] == 'Pre-game': return
   if 'state' in current:
      if current['state'] == 'Paused' or current['state'] == 'Finished': return
   r = [i for i in current['status'] if current['status'][i]['status'] not in ['Completed','Defeated']]
   if current['gameturn']['unixdiff'] < s['TURNWARNING'] and not current['warned']['warning']:
      announce("{1!s} still need to make orders. Hurry up, only {0!s} until the turn ends".format(current['gameturn']['timeremaining'],r),'warning')
      current['warned']['warning'] = True
   if current['gameturn']['unixdiff'] < s['TURNFATAL'] and not current['warned']['fatal']:
      announce("{1!s}, you are slow! Only {0!s} until the turn ends".format(current['gameturn']['timeremaining'],r),'warning')
      current['warned']['fatal'] = True
   return

def FetchAll():
   '''
   Gather all information and pack them nicely
   '''
   info = dict()
   msg,ctr = Messages()
   info['messages'],info['countries'] = Messages()
   info['gameturn'] = GameTurn()
   info['status'] = PlayerStatus()
   if 'warned' not in info:
      info['warned'] = dict()
      info['warned']['warning'] = False
      info['warned']['fatal'] = False
   #Check validity of information
   if info['gameturn'] == {} and info['status'] == {}: return False
   return info

def MainLoop(t=5):
   while True:
      if not GetPage():
         print("There was an Error fetching the Webpage")
         break
      current = FetchAll()
      if not current:
         announce("Something went wrong, not processing gameID:{0!s}\nDumpFetch: {1!s}".format(s['gameID'],current),'error')
         break
      if os.path.exists(s['SAVEPATH']+'db{0!s}.json'.format(s['gameID'])):
         past = LoadFile(s['SAVEPATH']+'db{0!s}.json'.format(s['gameID']))
         current['warned'] = past['warned']
         if not CompareTurn(current['gameturn'], past['gameturn']):
            TimerWarning(current)
            if s['ANNOUNCESTATUSCHANGE']:
               CompareStatus(current['status'], past['status'])
         else:
            current['warned']['warning'] = False #Reset warnings
            current['warned']['fatal'] = False #Reset warnings
         CompareMessages(current['messages'], past['messages'])
      DumpFile(current)
      if not s["ONESHOT"]:
         time.sleep(t*60)
      else: break

if __name__ == "__main__":
      MainLoop(s['WAITTIME'])
