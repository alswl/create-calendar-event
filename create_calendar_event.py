# coding=utf-8

"""
Auto ording room

python create_calendar_event.py -u you@domain.com -s mail.domain.com -l "6F-F16-天箭座-14人" -m skybolt@domain.com -b"技术之夜 03-21" -d "2018-03-21 18:00" -a "90"

"""

from __future__ import unicode_literals, print_function

import os
import argparse
import logging.config
import getpass
import socket
from datetime import timedelta

import requests
from exchangelib import DELEGATE, Account, Credentials, Configuration, CalendarItem, EWSDateTime, \
    EWSTimeZone, Attendee, Mailbox
from exchangelib.errors import UnauthorizedError
from exchangelib.items import SEND_ONLY_TO_ALL
from requests import ReadTimeout
from urllib3.exceptions import ReadTimeoutError
from dateutil import parser

DEFAULT_INTERVAL_SECONDS = 10

DEFAULT_SOCKET_TIMEOUT = 10
DSN_TOKEN = os.environ.get('EXCHANGE_AUTO_FORWARD_DSN')
ENV_PASSWORD = 'EXCHANGE_ORDER_PASSWORD'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'defaultFormatter': {
            'format': '%(levelname)s %(asctime)s %(module)s:%(lineno)d %(message)s ',
            'datefmt': '%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'defaultHandler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'defaultFormatter',
            'filename': 'exchange-auto-forward.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
        },
        'sentryHandler': {
            'level': 'ERROR',
            'class': 'raven.handlers.logging.SentryHandler',
            'dsn': DSN_TOKEN,
        },
        'consoleHandler': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['defaultHandler', 'sentryHandler'],
            'level': 'INFO',
            # 'level': 'DEBUG',
        },
        'console': {
            'handlers': ['consoleHandler'],
            'level': 'INFO',
            # 'level': 'DEBUG',
            'propagate': False,
        },
    },
}


logging.config.dictConfig(LOGGING)

logger = logging.getLogger(__name__)
console = logging.getLogger('console')
socket.setdefaulttimeout(DEFAULT_SOCKET_TIMEOUT)

tz = EWSTimeZone.timezone('Asia/Shanghai')


def create_event(account, subject, location, location_mail, date, duration):
    start = parser.parse(date)
    start_ews = tz.localize(EWSDateTime(start.year, start.month, start.day, start.hour,
                                        start.minute))
    end = parser.parse(date) + timedelta(seconds=duration * 60)
    end_ews = tz.localize(EWSDateTime(end.year, end.month, end.day, end.hour, end.minute))
    item = CalendarItem(
        folder=account.calendar,
        subject=subject,
        location=location,
        start=start_ews,
        end=end_ews,
        required_attendees=[
            Attendee(mailbox=Mailbox(email_address=location_mail),
                     response_type='Accept')
        ]
    )
    item.save(send_meeting_invitations=SEND_ONLY_TO_ALL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', '-u', required=True)
    parser.add_argument('--server', '-s', required=True)
    parser.add_argument('--location', '-l', required=True)
    parser.add_argument('--location-mail', '-m', required=True)
    parser.add_argument('--subject', '-b', required=True)
    parser.add_argument('--date', '-d', required=True)
    parser.add_argument('--duration', '-a', required=True, type=int)
    args = parser.parse_args()
    password = os.environ.get(ENV_PASSWORD)
    if password is None:
        password = getpass.getpass('EXCHANGE password:')

    # auth
    credentials = Credentials(username=args.username, password=password)
    try:
        config = Configuration(server=args.server, credentials=credentials)
    except UnauthorizedError as e:
        logger.error('Login failed, message: %s' % e)
        return

    # main logic
    try:
        account = Account(primary_smtp_address=args.username, config=config, autodiscover=False,
                          access_type=DELEGATE)
        # main_logic TODO
    except (ConnectionResetError, requests.exceptions.ConnectionError, TimeoutError,
            ReadTimeoutError, ReadTimeout) as e:
        logger.debug(e)
        return
    create_event(account=account, subject=args.subject, location=args.location,
                 location_mail=args.location_mail, date=args.date, duration=args.duration)


if __name__ == '__main__':
    main()
