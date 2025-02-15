import simpy
import random as rd


# Session 5, 6

class Bank(object):
    def _init_(self, env: simpy.Environment):
        self._env = env
        self.clients = 0
        self.total_arrival_time = 0
        self.customers_list = []
        self.tellers = simpy.Resource(env, capacity=2)
        self.action = env.process(self.customer_arrival())

    def gen_customer(self) -> simpy.Process:
        for i in range(10):
            yield self._env.timeout(1)
            Customer(i, self._env).service(self)

    def customer_arrival(self) -> simpy.Process:
        """ Generator method for the arrival of customers"""
        arrival_time = 0
        pre_arrival_time = 0
        while True:
            try:
                self.clients += 1
                waiting_time = abs(rd.normalvariate(3))
                yield self._env.timeout(waiting_time)
                arrival_time = self._env.now
                print('The interravial time is %.2f' % (arrival_time - pre_arrival_time))
                self.total_arrival_time += arrival_time - pre_arrival_time
                pre_arrival_time = arrival_time
                c = Customer(self.clients, self._env)
                self.customers_list.append(c)
                self._env.process(c.service(self))

            except simpy.Interrupt:
                print('The bank is closes at %.2f get out' % (self._env.now))

    def service_customer(self) -> simpy.Process:
        yield self._env.timeout(abs(rd.normalvariate(5)))

    def get_waiting_time(self) -> float:
        return sum([c.waiting_time for c in self.customers_list]) / self.clients


class Customer(object):
    def _init_(self, id: int, env: simpy.Environment):
        self._id = id
        self._env = env
        self.patience = abs(rd.normalvariate())
        self.arrival_time = env.now
        self.waiting_time = 0
        print('Customer %d arrives at %.2f' % (self._id, self._env.now))

    def service(self, bank: Bank) -> simpy.Process:
        with bank.tellers.request() as teller:
            res = yield teller | self._env.timeout(self.patience)
            self.waiting_time = self._env.now - self.arrival_time
            print('Customer %d waited %.2f' % (self._id, self.waiting_time))
            if teller in res:
                print('Customer %d is being served at %.2f' % (self._id, self._env.now))
                yield self._env.process(bank.service_customer())
                print('Customer %d leaves at %.2f' % (self._id, self._env.now))
            else:
                print('Customer %d leaves without service at %.2f' % (self._id, self._env.now))


def alarm(env: simpy.Environment, delay: int, bank: Bank):
    yield env.timeout(abs(rd.normalvariate(delay / 2)))
    bank.action.interrupt()
    print("There is and alamr at %.2f" % env.now)


env = simpy.Environment()
bank = Bank(env)
env.process(alarm(env, 30, bank))
env.run(until=50)
print('The average intertrraival time is %.2f' % (bank.total_arrival_time / bank.clients))
print('The average waiting time is %.2f' % bank.get_waiting_time())
