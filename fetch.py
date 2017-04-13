#!/usr/bin/env python3

import urllib.request
import json
import os
import time
from bs4 import BeautifulSoup

#STANDARD SETTINGS###################
#MODIFY SETTINGS IN settings.py #####
gameURL='http://webdiplomacy.net/board.php?' #Tested with WebDiplomacy 1.43
gameID='1234'
ONESHOT=True #Run only once if True
WAITTIME=5 #Time in minutes between fetches
TURNWARNING=12 #in hours
TURNFATAL=6 #in hours
ANNOUNCESTATUSCHANGE=True
SAVEPATH='' #uses current dir if empty, needs to end with delimiter (/)
#END SETTINGS###########################

try: #Load custom settings if there are any
   from settings import *
except ModuleNotFoundError: pass

def announce(text):
   print(text)

###BEAUTIFUL SOUP HTML###################################################################
def GetPage():
   global soup
   try:
      with urllib.request.urlopen(gameURL+'gameID='+gameID) as response:
         html = response.read()
   except urllib.error.URLError as e:
      announce("There was an error fetching the page:\n{0!s}".format(e))
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
   countrylist = soup.find('div', {'class':'chatbox', 'class':'chatboxnotabs'})
   if countrylist:
      countrylist = countrylist.find('div', {'class':'chatboxMembersList'})
      for c in countrylist.findAll('span'):
         if 'country' in "".join(c['class']):
            countries[c['class'][0]] = c.contents[0]
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
   if os.path.exists(SAVEPATH+'db{0!s}.json'.format(gameID)):
      os.rename(SAVEPATH+'db{0!s}.json'.format(gameID), SAVEPATH+'db{0!s}_old.json'.format(gameID))
   with open(SAVEPATH+'db{0!s}.json'.format(gameID), 'w') as outfile:
      json.dump(data, outfile)

def CompareStatus(current,past):
   '''
   Checks if status has changed compared to last fetch
   '''
   if len(current) != len(past):
      print("Different length of Status")
   else:
      for s in current:
         if (s in past) and current[s]['status'] != past[s]['status']:
            announce("{0!s}'s status has changed from {1!s} to {2!s}".format(s,past[s]['status'],current[s]['status']))
   return

def CompareTurn(current,past):
   '''
   Checks if we are in a new turn, compared to last fetch
   '''
   if current['gamedate'] != past['gamedate']:
      announce('The game "{1!s}" advanced to a new turn! It is now {0!s}.'.format(current['gamedate'],current['gameName']))
      return True
   elif current['gamephase'] != past['gamephase']:
      announce('The Game "{2!s}" advanced to a new phase! It is now in the {0!s} phase of {1!s}.'.format(current['gamephase'],current['gamedate'],current['gameName']))
      return False

def CompareMessages(current,past):
   try:
      if len(current) == len(past) and current[-1] == past[-1]: #No new messages
         return
   except IndexError: return
      
   for m in current:
      if m not in past:
         announce('New message from {0!s}: "{1!s}"'.format(m['who'],m['text']))
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
   if current['gameturn']['unixdiff'] < TURNWARNING and not current['warned']['warning']:
      announce("{1!s} still need to make orders. Hurry up, only {0!s} until the turn ends".format(current['gameturn']['timeremaining'],r))
      current['warned']['warning'] = True
   if current['gameturn']['unixdiff'] < TURNFATAL and not current['warned']['fatal']:
      announce("{1!s}, you are slow! Only {0!s} until the turn ends".format(current['gameturn']['timeremaining'],r))
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
         announce("Something went wrong, not processing gameID:{0!s}\nDumpFetch:\n{1!s}".format(gameID,current))
         break
      if os.path.exists(SAVEPATH+'db{0!s}.json'.format(gameID)):
         with open(SAVEPATH+'db{0!s}.json'.format(gameID)) as infile:
            past = json.load(infile)
            current['warned'] = past['warned']
         if not CompareTurn(current['gameturn'], past['gameturn']):
            TimerWarning(current)
            if ANNOUNCESTATUSCHANGE:
               CompareStatus(current['status'], past['status'])
         else:
            current['warned']['warning'] = False #Reset warnings
            current['warned']['fatal'] = False #Reset warnings
         CompareMessages(current['messages'], past['messages'])
         DumpFile(current)
      else:
         print("No db.json file found, dumping current to file. Location: {0!s}".format(SAVEPATH+"db{0!s}.json".format(gameID)))
         DumpFile(current)

      if(ONESHOT): break
      time.sleep(t*60)

if __name__ == "__main__":
      MainLoop(WAITTIME)
