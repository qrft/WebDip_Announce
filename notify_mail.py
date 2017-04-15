#!/usr/bin/env python3

def mail_me(who,text):
   for u in who:
      print("should mail to {0!s}: {1!s}".format(u,text))
   return
