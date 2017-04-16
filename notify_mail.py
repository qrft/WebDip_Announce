#!/usr/bin/env python3

#This function hugely depends on the type of mailserver you want to connect to
#Therefore, you might have to alter the code . The code provided here is just
#an example of how it could be done, you have to adopt the code and handle  the sending by yourself.

MYMAILSERVER='localhost'
MYPORT=587
MYUSERNAME='myusername'
MYPASSWORD='mypassword'
MYMAILADDRESS='mymailaddress'

from smtplib import SMTP
from email.mime.text import MIMEText

def mail_me(who,text):
   '''
   The function mail_me is called with a list of recipients ([who]) and the
   text ("text"). How you handle the actual sending is up to yourself. You can write a
   whole new mail_me function adopted to your and your mailserver needs.
   '''
   smtp = SMTP()
   smtp.connect(MYMAILSERVER, MYPORT)
   if MYUSERNAME and MYPASSWORD:
      smtp.login(MYUSERNAME, MYPASSWORD)

   from_addr = MYMAILADDRESS
   subj = text
   date = datetime.datetime.now().strftime( "%d/%m/%Y %H:%M" )
   message_text = text
   for u in who:
      msg = "From: {0!s}\nTo: {1!s}\nSubject: {2!s}\nDate: {3!s}\n\n{4!s}".format(from_addr,u,subj,date,message_text)
      smtp.sendmail(from_addr, u, msg)
   smtp.quit()
   return
