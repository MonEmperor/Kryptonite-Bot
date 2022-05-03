import asyncio
import os
from random import randint, uniform, choice
import datetime
from src.utils.json_utils import *
from src.utils.math_funcs import *
crypto_cache = [] # the list of crypto currencies. we use this if we wants to retrieve information on a currency

class CryptoCurrency:
    def __init__(self, currency:dict=None):
        """
            Initializes a crypto currency.

            Cryptocurrencies are stored in the db/crypto_currencies.json file. on init, the dict pointing to the
            currency in the json file is passed in as an argument. If none is given, a new currency will be generated
            instead.

            Upon generation, several properties will be generated, then saved:
                name: the name of the crypto currency generated by a name generator
                creation date: The day the crypto currency was created accurate to the hour.
                value: Value of the currency
                num_shares: the number of shares in total
                m_cap: the market cap. the total volume of all existing shares
                values: history of all values the currency had including the times it had them.
                Vmax_mag: The maximum magnitude the value can fluctuate by
                threshold: the likelyhood of the value decreasing in percent range(0.0,100.0) exclusively
                Tmax_mag: the maximum magnitude the threshold can fluctuate by.
                total_shares: the total number of shares bought
                delete_value: the value the currency will be deleted at
                UID: id of the token. do we need this?

        """
        if currency is None: # if there was no argument given, it creates a new currency

            # creates the CryptoCurrency dict
            #self.currency = {}

            self.creation_date = str(datetime.datetime.now().replace(minute=0,second=0, microsecond=0))
            self.name = CryptoCurrency.regen_name() # uses a generator to generate a random name
            self.uid = 0
            self.delete_value = 0.0 # normally 0

            self.value = uniform(0.5, 50.0) # normally 0.5 -> 50
            self.Vmax_mag = max(
                0.005,
                uniform(0.004, 0.00013)*self.value
            )
            # if too volatile, 5M-15M
            self.total_shares = randint(9_000, 100_000) # normally 9k-100k.

            self.threshold = 35.0 # normally 50.0
            self.Tmax_mag = 1.0

            self.values = []
            self.values.append({
                "date": self.creation_date,
                "value": self.value
            })

            # save the currency.
            self.save()

            # cache the currency
            self.cache()

        else: # otherwise loads up the currency from the dict given
            self.dict_to_obj(currency) # loads all the currency data

            # saves.
            self.save()

            # cache the currency
            self.cache()

    @property
    def market_cap(self): # the market is the total value of all shares
        return self.value * self.total_shares

    @staticmethod
    def name_generator()->str:
        """
            Generates a random name.

            Loads up data from db/crypto_names.json and randomly chooses a prefix and suffix and returns them.
        """
        names = load_json("db/crypto_names.json")
        prefix = choice(names["prefixes"])
        suffix = choice(names["suffixes"])
        return prefix+"-"+suffix

    @staticmethod
    def is_unique(name:str)->bool:
        """
        Checks if the given name is unique or not.

        Used when generating a new cryptocurrency so it dosent overwrite another or share the same name.
        """
        db = load_json("db/crypto_currencies.json")
        for index in db["currencies"]:
            if name == index["name"]: return False
        return True

    @staticmethod
    def regen_name()->str:
        """
        Regenerates the name of the currency if it matches another currency in the database.

        Most of the code identifies a currency by name. Upon generation, a currency may be given a name that already
        exists. the danger in this is that it could overwrite an existing currency.
        so this function recursively will continuously regenerate a name until a unique one is generated.
        There will likely be a limit on how many currencies will exist at a time and there are many name possibilities,
        however this is more foolproof. an additional level of security could be a has or numerical UID so that the code
        is completely unreliant on names. this can be implemented later

        :return:
        """
        unique = False

        while not unique:
            name = CryptoCurrency.name_generator()
            unique = CryptoCurrency.is_unique(name)
            if unique: break
        return name

    def dict_to_obj(self, currency):
        """
        transforms a dict to an object.

        Will be used upon init when a dictionary is given.
        """
        self.name = currency["name"]
        self.creation_date = currency["creation_date"]
        self.uid = currency["uid"]
        #self.total_shares = currency["total_shares"]
        self.delete_value = currency["delete_value"]
        self.value = currency["value"]
        self.Vmax_mag = currency["Vmax_mag"]
        self.total_shares = currency["total_shares"]
        self.threshold = currency["threshold"]
        self.Tmax_mag = currency["Tmax_mag"]
        self.values = currency["values"]

    def obj_to_dict(self)->dict:
        """
        transforms an object to a dictionary type.

        functions such as caching and saving require dicts, so a function was made.
        """
        currency = {}
        currency["name"] = self.name
        currency["creation_date"] = self.creation_date
        currency["uid"] = self.uid
        #currency["total_shares"] = self.total_shares
        currency["delete_value"] = self.delete_value
        currency["value"] = self.value
        currency["Vmax_mag"] = self.Vmax_mag
        currency["total_shares"] = self.total_shares
        currency["threshold"] = self.threshold
        currency["Tmax_mag"] = self.Tmax_mag
        currency["values"] = self.values

        return currency

    def save(self):
        """
            Writes data to the database.

            Loads up the crypto_currency.json file and looks for the currency that shares the same name as self,
            then writes the new data to the file.

            todo:
                consider deleting previous values older than 3 months(2016 entries ago)
        """
        db = load_json("db/crypto_currencies.json") # loads up the db containing all currencies

        currency = self.obj_to_dict() # transforms the object into a dict to be used

        for i in range(len(db["currencies"])): # cycles through all of them to find the matching one by name
            if db["currencies"][i]["name"] == currency["name"]:
                db["currencies"][i] = currency
                update_json("db/crypto_currencies.json", db)
                return

        # if the currency is not found, add it.
        db["currencies"].append(currency)
        db["count"] += 1 # updates the number of crypto currencies stored in the database
        update_json("db/crypto_currencies.json", db)
        return

    def cache(self):
        """
            Caches the value of a cryptocurrency.

            Used to keep track of the commonly used data of a cryptocurrency. Called upon loading in a Crypto.
            All instances of cryptocurrencies are cached when updated every minute. Additionally, they are cached on
            startup. This is to keep its statistics in RAM.
            Due to this, everything the other functions will ever need can be accessed via the cache. accessing the json
            file is only to update the value and write the changes every minute and adding a new value every hour.
            This is to minimize writes to disk for both performance and longevity.

            Takes in a dict, deletes all instances of previous values from over a week
            ago. The previous values are stored every hour, there are 168 hours in a week, so if a value's index
            subtracted from the total length is greater than 168, its older than a week old. So long as it's not the
            initial value, we can delete it and append the dict to the crypto_cache array.
        """

        currency = self.obj_to_dict() # transforms the object to a dict

        # deletes all instances of older values.
        values_len = len(currency["values"])
        for i in range(values_len):
            if ((values_len-i)>168 and i!=0):
                del_dict_key(currency, "values", i)

        # searches for any previous records of the dict in the cache and overwrites it
        cache_len = len(crypto_cache)
        for i in range(cache_len-1, -1, -1): # iterates through the list backwards.
            if crypto_cache[i]["name"] == currency["name"]:
                del crypto_cache[i]

        crypto_cache.append(currency) # appends the dict to cache.

    def delete(self):
        """
            Deletes a crypto currency.

            Usually used when the currency's value drops below a certain point.

            Looks through the crypto currencies json and deletes the right entry as well as decrement the counter.
        """
        db = load_json("db/crypto_currencies.json")  # loads up the db containing all currencies

        # deletes from the json so it cannot be loaded again
        for i in range(len(db["currencies"])):
            if db["currencies"][i]["name"] == self.name:
                db["currencies"].pop(i)
                db["count"] -=1
                update_json("db/crypto_currencies.json", db)
                break

        # deletes it from the cache as well so it cannot be referenced
        for cached in crypto_cache:
            if cached["name"] == self.name:
                crypto_cache.remove(cached)
                break
        #return db# returns the db

    def compute(self):
        """
        Computes a cryptocurrency's fluctuations.

        Fluctuates the vale and threshold increases. based off a random number compared to the current threshold
        then increases the threshold and decreases the value if the number < threshold and vice versa.

        Then simulates a quarterly spike by checking if the current spike matches the right quarter.

        Finally, modify the Vmax_mag value so the average value change gradually changes over time.
        """

        self.fluctuate()

        self.spike()

        self.Vmax_mag_fluctuate()

    def simulate(self):
        """
        Simulates a cryptocurrency.

        Every minute, the cryptocurrency will be loaded and computed for change, saved and then cached.
        :return:
        """
        self.compute() # runs the calculations to fluctuate it

        if datetime.datetime.now().minute == 0:
            self.history_append() # adds to history of values

        # when testing, comment this line
        self.save() # saves the values to the database.

        self.cache() # caches it

        if self.value <= self.delete_value: # deletes the currency if it loses all value.
            self.delete()
            return

    def spike(self):
        """
        A quarterly spike that drastically modifies the threshold.

        Every 3 months, (march 31, june 30th, sept 31, dec 31), a spike is generated. the threshold changes
        by a magnitude of 30 in either direction.

        issues:
            due to synchronization issues; the code may trigger a spike twice or not at all. minor issue tbh
                maybe try a different method other than datetimes?
        """
        # quarterly spike. +/-30% to threshold
        now = str(datetime.datetime.now().replace(second=0, microsecond=0))
        q1,q2,q3,q4 = "-03-31 00:00","-06-30 00:00","-09-31 00:00","-12-31 00:00" # the quarter datetimes
        if ((q1 in now) or (q2 in now) or (q3 in now) or (q4 in now)):
            self.threshold += (choice([-1, 1]) * 30) + 50

        # daily spike
        # uses rng and not a datetime object because this can happen at any point in the day.
        spike_chance = randint(0,1440) # rolls a random. 1440 mins/day so this will spike daily
        if spike_chance == 1440: self.threshold = 50

    def Vmax_mag_fluctuate(self):
        """
        Fluctuates Vmax_mag.

        The Vmax_mag is the maximum magnitude the value can fluctuate by every cycle. the Vmax_mag's initial value
        is based on the value of the currency, however, it's fluctuation is completely independent.

        The only limitation on Vmax_mag is that it cannot equal 0. this causes all value manipulations to inverse and
        adds unecessary complexity and is harder to predict.

        We check if the Vmax_mag is below a certain limit, if so, we only allow increases of vmax_mag. otherwise,
        the sign is random.
        """

        if self.Vmax_mag <= 0.02: # 0.02 is chosen as it is the twice the maximum it can increase by.
            # 0.001-0.01 is arbitrary since Vmax_mag's value is unimportant as long as its not too large or negative
            self.Vmax_mag += 1 * uniform(0.001, 0.01)
            return
        else:
            self.Vmax_mag += randint(-1,1) * uniform(0.001, 0.01) # normally 0.001, 0.01

    def thresh_fluctuate(self, val_increased:bool):
        """
        Modifies the threshold.

        The threshold is modified whenever the value is modified. usually in the opposite direction.
        This is done so that when the currency increases, it appears to have a large spike instead of pure randomness.

        For Example, when Value is increased, the threshold is more likely to decrease and vice versa.
        However, to prevent the threshold from going too high or too low, it flips direction when >65 or <35.

        We solve for Tfluc_chance and then sign. we take those values and substitute them into the equation to
        determine the value of fluctuate.
        Example:
            when increasing value, threshold decreases
            Tfluc_chance is more likely to be -1
            sign returns either -1 or 1.                 -1 if T<35; 1 if T>35.
            When T>35 and value increases, Tfluc_chance is likely -1. we want to decrease the threshold.
            so sign needs to be +1 to do so.

        """
        T = self.threshold # threshold value. stored as a variable for typing convenience and readibility

        if val_increased:
            Tfluc_chance = choice((-1,-1,1)) # this is more likely to return -1 which decreases the threshold

            # The expression for sign below returns -1 or 1.
            # -1 for T<35 and +1 for T>35.
            # It is intended to determine the directon of the change in threshold.
            try:sign = -(35-T)/abs(35-T)
            except ZeroDivisionError: sign = choice((-1,1))

        else:
            Tfluc_chance = choice((1,1,-1)) # this is more likely to return 1 which increases the threshold

            # The expression for sign below returns -1 or 1.
            # +1 for T<65 and -1 for T>65.
            # It is intended to determine the direction of the change in threshold.
            try: sign = (65-T)/abs(65-T)
            except ZeroDivisionError: sign = choice((-1,1))

        self.threshold += sign * Tfluc_chance  * uniform(0, self.Tmax_mag)

    def value_fluctuate(self, val_increased:bool):
        """
        Fluctuates the value.
        
        The value can fluctuate based on a ranged determined by Vmax_mag or based on a percentage of its value.
        When fluctuating based on percentage, it is a spike since the percentage scales with the value.
        When not on percentage, the value does not spike at all as the Vmax_mag does not scale with the value 
        Which way it fluctuates is determined by the threshold. If the threshold is within bounds, it goes off 
        percentage and when it is out of bounds, it is based off Vmax_mag.
        
        The final equation to fluctuate value is determined by several factors:
            The base_factor is the amount the currency will always increase by. it is based off Vmax_mag
            the percent_factor is the amount the currency will increase by when increasing by percentage.
            If the value of the currency is increasing this cycle, sign ==1 and -1 if it is decreasing.
            
            the bounds_factor determines if the currency will fluctuate based off percentage. it outputs either 0 or 1.
            the bound_factor's value is multiplied by the percent_factor. when the value is to spike, bounds_factor == 1
            and otherwise, 0. The bounds factor will be undefined at the bounds(35, 65) so in those cases, it will be
            set to 1 so that it may spike. 
            
        This causes value to always increase by a small amount, but if spiking, also by a percentage.
        """
        T = self.threshold
        percent = self.value/100

        base_factor = uniform(0, self.Vmax_mag) # the normal amount the currency increases by
        try: bounds_factor = max(0, -abs((T**2) - (100*T) + 2275)/((T**2) - (100*T) + 2275)) # outside the bounds, return 1. within bounds, return 0
        except: bounds_factor = 0 # if the bounds factor is undefined, we just set it as 0 so it behaves normally
        percent_factor = uniform(0, percent/500_000) * gaussian_function(x=T, a=10_000, b=50, c=4) # ranges from 0->0.0002 times the value.

        if val_increased: sign =1
        else:
            sign =-1
            if self.value < 2.5: # tp prevent currencies from dying too easily, it will only fluctuate by a small amount at dangerously low values
                self.value += sign * uniform(0.05,0.1)
                return

        self.value += sign * (base_factor + (bounds_factor * percent_factor))

    def fluctuate(self):
        """
        Fluctuates the threshold and value.

        Generates a random number from [0,100]. if the num is >= threshold, we increase the value and
        decrease the threshold. and vice versa.

        Threshold:
            Threshold's fluctuation direction is inversely proportionate to value's direction(Ex: +value, -threshold)
            This however, does not mean threshold is garunteed to decrease if value increases, but rather,
            is more likely to decrease.
            when modifying threshold, the magnitude ranges from [0, Tmax_mag] * (1 or -1)

        Value:
            Simply is increased by a magnitude ranging from [0, Vmax_mag].
            value is garunteed to increase if the random num >= threshold.
        """
        Vfluc_chance = randint(0, 100)
        val_increased:bool

        if Vfluc_chance >= self.threshold:

            self.thresh_fluctuate(val_increased=True) # changes the threshold
            val_increased = True

        else:
            self.thresh_fluctuate(val_increased=False) # changes the threshold
            val_increased = False


        self.value_fluctuate(val_increased=val_increased)

    def display_history(self): return

    def buy(self, volume:float):
        """
        Buy function. Modifies the cryptocurrency value when buying it.

        When buying, the currency value is increased very slightly. the percentage of the market cap is determined based
        on the total volume of a user's purchase. then, that same percentage is added to the value.

        Examples:
            >>>volume = 1
            >>>self.value = 1
            >>>self.market_cap = 100
            >>>self.buy(1) # buys 1 share
                >>>percent = volume / self.market_cap # 0.01
                >>>self.value += self.value * percent # 1.01
        """
        percent = volume / self.market_cap
        delta = self.value * percent
        self.value+= delta
        return delta

    def sell(self, volume:float):
        """
        Sell function. Modifies the cryptocurrency value when selling it.

        When buying, the currency value is increased very slightly. the percentage of the market cap is determined based
        on the total volume of a user's purchase. then, that same percentage is subtracted from the value.

        Examples:
            >>>volume = 1
            >>>self.value = 1
            >>>self.market_cap = 100
            >>>self.sell(1) # buys 1 share
                >>>percent = volume / self.market_cap # 0.01
                >>>self.value -= self.value * percent # 0.99
        """
        percent = volume / self.market_cap
        delta = self.value * percent
        self.value -= delta
        return delta

    def history_append(self):
        """
        Adds the current value to the history of values.

        Is called every hour on the frst minute. Example: 01:00:00. at 1:00 am
        """
        self.values.append( # make sure date is casted to str as JSON cant store datetime objects
            {
                "date": str(datetime.datetime.now().replace(microsecond=0, second=0)),
                "value": self.value
            }
        )

    def __str__(self):
        return f"name: {self.name}, created date: {self.creation_date}, uid: {self.uid}, total_shares: {self.total_shares}, market_cap: {self.market_cap}, " \
               f"delete_value: {self.delete_value}, value: {self.value}, Vmax_mag: {self.Vmax_mag}, threshold: {self.threshold}, " \
               f"Tmax_mag: {self.Tmax_mag}, values: {self.values}"

if __name__ == '__main__':
    os.chdir("/home/loona/programming/Kryptonite-Bot/src")

    # EXECUTION AND TESTING OF FEATURES BELOW
    db = load_json("db/crypto_currencies.json")

    # adding currencies

    new_crypto = CryptoCurrency()
    print(new_crypto.currency)

    #deleting currencies
    """
    for dict in db["currencies"]:
        dict = CryptoCurrency(dict)
        dict.delete()
    """

    # caching currencies
    """
    new = CryptoCurrency()
    new.cache()
    print(crypto_cache)
    #print(new.currency["value"], new.currency["threshold"], new.currency["Vmax_mag"])
    #new.simulate()
    #print(new.currency["value"], new.currency["threshold"], new.currency["Vmax_mag"])
    """

    #prints the cache
    """cache_dict = {
        "crypt_cache": crypto_cache
    }
    print(json.dumps(cache_dict, indent=4, sort_keys=False))"""

