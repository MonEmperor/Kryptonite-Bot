import asyncio
import os
from random import randint, uniform, choice
import datetime
from json_utils import *
os.chdir("/home/loona/programming/Kryptonite-Bot/src")
crypto_cache = [] # the list of crypto currencies. we use this if someone wants to retrieve information on a currency

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
                values: history of all values the currency had including the times it had them.
                Vmax_mag: The maximum magnitude the value can fluctuate by
                threshold: the likelyhood of the value decreasing in percent range(0.0,100.0) exclusively
                Tmax_mag: the maximum magnitude the threshold can fluctuate by.

            todo:
                maybe allow self vars of all the json indexes, and saving sets all those values to the dict and saves


        """
        if currency is None: # if there was no argument given, it creates a new currency

            # creates the CryptoCurrency dict
            self.currency = {}

            self.currency["creation date"] = str(datetime.datetime.now().replace(minute=0,second=0, microsecond=0))
            self.currency["name"] = CryptoCurrency.regen_name() # uses a generator to generate a random name
            self.currency["UID"] = 0
            self.currency["total_shares"] = 0
            self.currency["delete_value"] = 0.0

            self.currency["value"] = uniform(0.5, 50.0)
            self.currency["Vmax_mag"] = max(
                0.005,
                uniform(0.2, 1.0)*(self.currency["value"]/20)
            )

            self.currency["threshold"] = 50.0
            self.currency["Tmax_mag"] = 1.0

            self.currency["values"] = []
            self.currency["values"].append({
                "date": self.currency["creation date"],
                "value": self.currency["value"]
            })

            # simulate the currency?

            # save the currency.
            self.save()

            # cache the currency
            self.cache()

        else: # otherwise loads up the currency from the dict given
            self.currency = currency # we only load in the dict as it makes writing changes easier

            # cache the currency
            self.cache()

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

    def save(self):
        """
            Writes data to the database.

            Loads up the crypto_currency.json file and looks for the currency that shares the same name as self,
            then writes the new data to the file.

            todo:
                consider deleting previous values older than 3 months(2016 entries ago)
        """
        db = load_json("db/crypto_currencies.json") # loads up the db containing all currencies

        for i in range(len(db["currencies"])): # cycles through all of them to find the matching one by name
            if db["currencies"][i]["name"] == self.currency["name"]:
                db["currencies"][i] = self.currency
                update_json("db/crypto_currencies.json", db)
                return

        # if the currency is not found, add it.
        db["currencies"].append(self.currency)
        db["count"] += 1 # updates the number of crypto currencies stored in the database
        update_json("db/crypto_currencies.json", db)
        return

    def cache(self):
        """
            Caches the value of a cryptocurrency.

            Used to keep track of the commonly used data of a cryptocurrency. Called upon loading in a Crypto.
            All instances of cryptocurrencies are cached when updated every minute. Additionally, they are cached on
            startup. This is to keep its stats(except Vmax_mag, threshold, Tmax_mag and only last week's values) in RAM.
            Due to this, everything the other functions will ever need can be accessed via the cache. accessing the json
            file is only to update the value and write the changes every minute and adding a new value every hour.
            This is to minimize writes to disk for both performance and longevity.

            Takes in a dict, deletes Vmax_mag, Tmax_mag, threshold and all instances of previous values from over a week
            ago. The previous values are stored every hour, there are 168 hours in a week, so if a value's index
            subtracted from the total length is greater than 168, its older than a week old. So long as it's not the
            initial value, we can delete it and append the dict to the crypto_cache array.
        """

        #del currency["Vmax_mag"], currency["Tmax_mag"], currency["threshold"] # deletes unecessary values
        #print(self.currency)
        #currency = del_dict_keys(self.currency, "Vmax_mag", "Tmax_mag", "threshold")

        # deletes all instances of older values.
        values_len = len(self.currency["values"])
        for i in range(values_len):
            if ((values_len-i)>168 and i!=0):
                del_dict_key(self.currency, "values", i)
                #del currency["values"][i]

        # searches for any previous records of the dict in the cache and overwrites it
        cache_len = len(crypto_cache)
        for i in range(cache_len-1, -1, -1): # iterates through the list backwards. not working because the dict is too small. go through normally and make a list of bad dicts to remove.
            if crypto_cache[i]["name"] == self.currency["name"]:
                del crypto_cache[i]

        crypto_cache.append(self.currency) # appends the dict to cache.

    def delete(self):
        """
            Deletes a crypto currency.

            Usually used when the currency's value drops below a certain point.

            Looks through the crypto currencies json and deletes the right entry as well as decrement the counter.
        """
        db = load_json("db/crypto_currencies.json")  # loads up the db containing all currencies

        # deletes from the json so it cannot be loaded again
        for i in range(len(db["currencies"])):
            if db["currencies"][i]["name"] == self.currency["name"]:
                db["currencies"].pop(i)
                db["count"] -=1
                update_json("db/crypto_currencies.json", db)
                break

        # deletes it from the cache as well so it cannot be referenced
        for cached in crypto_cache:
            if cached["name"] == self.currency["name"]: crypto_cache.remove(cached)
        #return # maybe deleter method?

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

        # modify Vmax_mag (adds +/-uniform(0.001, 0.01)). completely independant of the currency's value
        self.currency["Vmax_mag"] += randint(-1, 1) * uniform(0.001, 0.01)

    def simulate(self):
        """
        Simulates a cryptocurrency.

        Every minute, the cryptocurrency will be loaded and computed for change, saved and then cached.
        :return:
        """
        self.compute()

        self.save()

        self.cache()

        if self.currency["value"] <= self.currency["delete_value"]: # deletes the currency if it loses all value.
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
            self.currency["threshold"] += choice([-1, 1]) * 30
            print("spiked")

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
        #print("did it fluctuate?", Vfluc_chance, self.currency["threshold"])

        if Vfluc_chance >= self.currency["threshold"]:
            # modifies the threshold. likely to decrease
            Tfluc_chance = choice((-1, -1, 1))  # has a bias to decrease when value increases
            self.currency["threshold"] += Tfluc_chance * uniform(0, self.currency["Tmax_mag"])

            # increases the value
            self.currency["value"] += uniform(0, self.currency["Vmax_mag"])

        else:
            # modifies the threshold. likely to increase
            Tfluc_chance = choice((-1, 1, 1)) # has a bias to increase when value decreases
            self.currency["threshold"] += Tfluc_chance * uniform(0, self.currency["Tmax_mag"])

            # decrease the value
            self.currency["value"] += -uniform(0, self.currency["Vmax_mag"])

    def display_history(self): return

    def trade(self, num_shares:int, buy:bool):
        """
        Processes a buy/sell request.

        if the coin is bought(buy=True), the value will increase marginally based on the number of shares traded.
        If it has been sold, it will decrease the value accordingly.
        :param num_shares:
        :param buy:
        :return:
        """

# EXECUTION AND TESTING OF FEATURES BELOW
db = load_json("db/crypto_currencies.json")

# adding currencies
"""
new_crypto = CryptoCurrency()
print(new_crypto.currency)"""

#deleting currencies
"""
for dict in db["currencies"]:
    dict = CryptoCurrency(dict)
    dict.delete()
"""

# caching currencies
#"""
new = CryptoCurrency()
print(new.currency["value"], new.currency["threshold"], new.currency["Vmax_mag"])
new.simulate()
print(new.currency["value"], new.currency["threshold"], new.currency["Vmax_mag"])
#"""

#prints the cache
"""cache_dict = {
    "crypt_cache": crypto_cache
}
print(json.dumps(cache_dict, indent=4, sort_keys=False))"""