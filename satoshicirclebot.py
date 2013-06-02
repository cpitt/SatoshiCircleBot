#!/usr/bin/env python
###
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#  https://gnu.org/licenses/gpl-3.0-standalone.html
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  Support
#
#  You can show your thanks and support for this program
#  by starting your own account on satoshicircle.com using the following affiliate link:
#  https://satoshicircle.com/?aid=740
#  or by sending BTC to:
#  1PfcppGH4Sa96FK7xEWnCjAyz2whuKtgWP
#
###
import requests,math,random,re,time,sys,datetime

class SatoshiCircleBot:
    def __init__(self, secret, initial_bet):
        self.url = 'https://satoshicircle.com/'
        self.s = requests.Session() #Works without, but the site uses sessions so we might as well too
        self.a  = requests.adapters.HTTPAdapter(10,10,5,False)
        self.s.mount(self.url, self.a)
        self.secret = secret
        self.initial_bet = initial_bet
        self.max_bet = .25  #satoshicircle doesn't allow bets larger than this number
        self.wheel = 4  #wheel 4 is the 50/50 wheel changing this will break the martingale strategy
        self.total_earned = 0
        self.idbet = self.get_idbet(self.get_page())  # get the initial idbet
        self.balance = self.get_balance()
        self.starting_balance = self.balance
        self.running = False

    def post_request(self, endPoint, data):
        """Post request"""
        retries = 0
        while True:
            try:
                r = self.s.post(self.url+endPoint, data=data, verify=False, timeout=10)
                json = r.json()
                break
            except:
                #TODO: if queried too quickly satoshicircle will respond with a good (http status 200) but empty requests which leads to the json()
                #with an decode error... I have also encountered an ssl time out error #TODO: better error handling
                retries += 1
                if retries > 10:
                    exit("Max retries exceeded. Check your connection!")
                sys.stdout.write(" - response empty retrying ")
                sys.stdout.flush()
                time.sleep(2)
        return json

    def get_balance(self):
        """Get the current balance"""
        endPoint = 'control.php'
        data = {'function':'getBalance', 'secret':self.secret, 'idbet':self.idbet}
        r = self.post_request(endPoint, data)
        if r['newBets']:
            self.idbet = self.get_idbet(r['newBets'][0]) # it seems this needs to be updated whenever possible
        return r['balance']

    def get_spin(self, bet):
        """Spin the roulette wheel"""
        seed = math.floor(random.random() * 1e17)
        endPoint = 'control.php'
        data = {'function':'getSpin', 'bet':bet, 'secret':self.secret, 'clientSeed':seed, 'idbet': self.idbet, 'idgame':self.wheel}
        spin = self.post_request(endPoint, data)
        if spin['newBets']:
            self.idbet = self.get_idbet(spin['newBets'][0])
        return spin

    def get_outcome(self):
        # Probably not needed
        endPoint = 'control.php'
        data = {'function':'getOutcome', 'secret':self.secret}
        self.post_request(endPoint, data)

    def get_idbet(self, text):
        """given the string text it matches and extracts the idbet value."""
        #NOTE: I'm not sure if the idbet is necessary but it helps keep the responses smaller as far as I can tell
        m = re.search('idbet=\"(\d*)\"', text)
        return m.group(1)

    def get_page(self):
        """Load the entire page used mostly to get the initial idbet"""
        r = self.s.get(self.url+'?secret='+self.secret, verify=False)
        return r.text

    def martingale(self):
        """Continuously place bets according to the martingale strategy"""
        won_last = True
        bet = self.initial_bet
        while self.running:
            if won_last:
                bet = self.initial_bet
            else:
                bet *= 2
            if bet >= self.max_bet or bet >= self.balance:
                self.stop()
                return
            spin = self.get_spin(bet)
            if spin['newBets']:
                self.idbet = self.get_idbet(spin['newBets'][0]) # it seems this needs to be updated whenever possible
            self.total_earned += spin['addon']
            if spin['addon'] < 0:
                won_last = False
            else:
                won_last = True
            self.balance = spin['balance']
            #update ticker
            sys.stdout.write("\r\x1b[KCurrent bet: " + str(bet) + " | Add On: "+ str(spin['addon']) + " | Balance: " + str(spin['balance']) + \
                " |  Total Earned: " + str(self.total_earned) + \
                " | Rate: " + str( round((self.total_earned / (time.time() - self.start_time)) * 60 * 60 , 8) ) + " B/hour " + \
                " | Running Time: " + str(datetime.timedelta(seconds=time.time()-self.start_time)))
            sys.stdout.flush()
            time.sleep(6)   #lower than 6 seems to be faster than satoshicircle can handle and leads to errors

    def start(self):
        """Start the Bot"""
        print "Starting SatoshiCircleBot!"
        self.running = True
        self.start_time = time.time()
        self.martingale()

    def stop(self):
        """Stop the bot"""
        self.running = False

def main():
    """docstring for main"""
    #Config
    config = {}
    try:
        execfile("config.conf", config)
    except IOError:
        exit("Could not find config.conf!")
    secret = config['secret']
    initial_bet = config['initial_bet']
    bot = SatoshiCircleBot(secret, initial_bet)
    bot.start()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit("\r\n Good Bye!")