"""Flair bot."""
import sys
import os
import re
import codecs
import csv
import time
from time import gmtime, strftime, sleep
import praw
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


class FlairBot:
    """Flair bot."""

    def __init__(self):
        """Initial setup."""

        self.conf = ConfigParser()
        self.flairs = {}
        self.reddit = None

        os.chdir(sys.path[0])
        if os.path.exists('conf.ini'):
            self.conf.read('conf.ini')
        else:
            raise FileNotFoundError('Config file, conf.ini, was not found.')

        if self.conf.get('log', 'logging') == 'False':
            self.logging = False
        else:
            self.logging = True

        self.login()

    def login(self):
        """Log in via script/web app."""

        app_id = self.conf.get('app', 'app_id')
        app_secret = self.conf.get('app', 'app_secret')
        user_agent = self.conf.get('app', 'user_agent')

        if self.conf.get('app', 'auth_type') == 'webapp':
            token = self.conf.get('auth-webapp', 'token')
            self.reddit = praw.Reddit(
                client_id=app_id,
                client_secret=app_secret,
                refresh_token=token,
                user_agent=user_agent)
        else:
            username = self.conf.get('auth-script', 'username')
            password = self.conf.get('auth-script', 'passwd')
            self.reddit = praw.Reddit(
                client_id=app_id,
                client_secret=app_secret,
                username=username,
                password=password,
                user_agent=user_agent)

        self.get_flairs()

    def get_flairs(self):
        """Read flairs from CSV."""

        with open('flair_list.csv') as csvf:
            csvf = csv.reader(csvf)
            flairs = {}
            for row in csvf:
                if len(row) == 2:
                    flairs[row[0]] = row[1]
                else:
                    flairs[row[0]] = None

        self.flairs = flairs
        self.fetch_pms()

    def fetch_pms(self):
        """Grab unread PMs."""

        target_sub = self.conf.get('subreddit', 'name')
        valid = r'[A-Za-z0-9_-]+'
        subject = self.conf.get('subject', 'subject')
        for msg in self.reddit.inbox.unread():
            if msg.author is None:
                continue  # Skip if the author is None
            author = str(msg.author)
            valid_user = re.match(valid, author)
            if msg.subject == subject and valid_user:
                self.process_pm(msg, author, target_sub)
            else:  # If someone sends something wack
                self.badmsg(author)
                msg.mark_read()
        sys.exit()

    def process_pm(self, msg, author, target_sub):
        """Process unread PM."""

        content = msg.body.split(',', 1)

        try:  #From flair site
            firsthalf = content[0].rstrip()
            first, *middle, class_name = firsthalf.split()
        except:  #Direct PM
            class_name = content[0].rstrip()

        subreddit = self.reddit.subreddit(target_sub)

        if class_name in self.flairs:
            if len(content) > 1:
                flair_text = content[1].lstrip()[:64]
            else:
                flair_text = self.flairs[class_name] or ''

            subreddit.flair.set(author, flair_text, class_name)
            self.reddit.redditor(author).message(
                'Flair Request Processed!',
                'Your flair request has been processed. The next time you visit /r/future_fight, your flair should be applied!'
            )
            if self.logging:
                self.log(author, flair_text, class_name)
        else:
            self.badmsg(author)
        # print("Flair " + class_name + " applied to user /u/" + author)
        msg.mark_read()

    def badmsg(self, author):
        self.reddit.redditor(author).message(
            'Flair Request Invalid!',
            '''If you are receiving this message your flair request was not accepted. This is likely because you changed either the title or the body of your message.

Please ensure you have read and understood the instructions, then try again. If the issue persists, send a [modmail](https://www.reddit.com/message/compose?to=%2Fr%2Ffuture_fight).'''
        )
        if self.logging:
            self.badlog(author)

    @staticmethod
    def log(user, text, cls):
        """Log applied flairs to file."""

        with codecs.open('log.txt', 'a', 'utf-8') as logfile:
            time_now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            log = 'user: ' + user
            log += ' | class(es): ' + cls
            if len(text):
                log += ' | text: ' + text
            log += ' @ ' + time_now + '\n'
            logfile.write(log)

    @staticmethod
    def badlog(user):
        """Log if user PM was invalid."""

        with codecs.open('log.txt', 'a', 'utf-8') as logfile:
            time_now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            log = 'user: ' + user
            log += ' | failed to process'
            log += ' @ ' + time_now + '\n'
            logfile.write(log)


FlairBot()