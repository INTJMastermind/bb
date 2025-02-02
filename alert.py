'''
Enter your email credentials below.
'''
try:
    from secret import USER, PASSWORD, TO, APP_TOKEN, USER_KEY
except:
    USER = 'your_email@gmail.com'
    PASSWORD = 'pass123'
    TO = 'recipient@gmail.com'
    APP_TOKEN = ''
    USER_KEY = ''

# For email alerts
import smtplib
from email.message import EmailMessage

# For Pushover notifications
import http.client
import urllib


def email_alert(message, subject = 'B6 Notification'):
    msg = EmailMessage()
    msg.set_content(message)
    msg['subject'] = subject
    msg['from'] = USER
    msg['to'] = TO


    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(USER, PASSWORD)
        server.send_message(msg)
        server.quit()
    except:
        print('Failed to send email alert.')
        return
    
def pushover(message):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    try:
        conn.request("POST", "/1/messages.json",
        urllib.parse.urlencode({
            "token": APP_TOKEN,
            "user": USER_KEY,
            "message": message,
        }), { "Content-type": "application/x-www-form-urlencoded" })
        conn.getresponse()
    except:
        print('Failed to send Pushover notification.')
        return

if __name__ == '__main__':
    email_alert('Hello, World!')
    pushover('Hello, World!')