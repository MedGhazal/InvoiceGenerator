from django.shortcuts import render
from django.core.mail import EmailMessage


def send_hello_world():
    email = EmailMessage(
        'Hello World',
        'Hello World',
        'infos@lamome.business',
        to=['latifa-aitalioubihi@lamome.business'],
    )
    email.send()
