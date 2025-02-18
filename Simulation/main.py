import random
import simpy
import json


class Product:
    def __init__(self, product_id):
        self.id = product_id


class Workstation:
    def __init__(self, env: simpy.Environment, id, failure_rate, work_time_mean, fix_time_mean, defect_rate):
        self.env = env
        self.name = id
        self.failure_rate = failure_rate
        self.work_time_mean = work_time_mean
        self.fix_time_mean = fix_time_mean
        self.defect_rate = defect_rate
        self.working = True
        self.material = 25  # (2) Each container have 25 material units
        self.processed_count = 0
        self.total_fix_time = 0
        self.occupancy = 0
        self.downtime = 0
        self.supply_material = SupplyMaterial(env)

    def process_product(self, product):
        """Processes a product, checks for failure, and handles repairs if needed."""

        if self.material <= 0:  # (3) If a station runs out of material it needs supply
            yield self.env.process(self.supply_material.supply(self))

        if random.random() < self.failure_rate:  # (4) If a station fails, it needs to get fixed
            fix_time = random.expovariate(1 / self.fix_time_mean)
            self.total_fix_time += fix_time
            self.downtime += fix_time
            yield self.env.timeout(fix_time)  # Fixed time simulation

        process_time = abs(random.normalvariate(self.work_time_mean, 0.2))
        self.occupancy += process_time
        yield self.env.timeout(process_time)  # Simulating work
        self.processed_count += 1
        self.material -= 1

        # (7) There is a chance that the product has a defect after being processed
        if random.random() < self.defect_rate:
            return False  # Defect product
        return True  # Approved product


class SupplyMaterial:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.supply_devices = simpy.Resource(env, capacity=3)
        self.supply_time = 0
        self.occupancy = 0

    def supply(self, workstation: Workstation):
        """Resupplies a workstation with material."""
        with self.supply_devices.request() as request:
            yield request  # Wait until supllier is available
            supply_time = abs(random.normalvariate(2, 0.2))
            self.occupancy += supply_time
            yield self.env.timeout(supply_time)  # Supply time simulation
            workstation.material = 25


class Factory:

    def __init__(self, env: simpy.Environment, num_workstations, failure_rates, work_time_mean, fix_time_mean,
                 defect_rate):
        self.env = env
        self.workstations = [
            Workstation(env, i + 1, failure_rates[i], work_time_mean, fix_time_mean, defect_rate)
            for i in range(num_workstations)]
        self.products = []
        self.rejected_products = 0
        self.total_processing_time = 0
        self.accidents = 0
        self.downtime = 0
        self.simulation_running = True

    def run_simulation(self, time_limit):
        self.simulation = self.env.process(self.generate_products())
        self.timeLimit = time_limit
        self.env.run(until=time_limit)

        final_production = len(self.products) - self.rejected_products
        avg_fix_time = sum(ws.total_fix_time for ws in self.workstations)
        avg_bottleneck_delay = self.calculate_bottleneck_delay()
        supply_material_occupancy = sum(ws.supply_material.occupancy for ws in self.workstations)

        results = {
            "Final production": final_production,
            "Rejected productions": self.rejected_products,
            "Total fix time": avg_fix_time,
            "Average bottleneck delay": avg_bottleneck_delay,
            "Workstations occupancy": self.get_workstations_occupancy(),
            "Supplier occupancy": supply_material_occupancy,
            "Workstation downtime": self.get_workstation_downtime(),
            "Faulty Products Rate": self.rejected_products / (1 if len(self.products) == 0 else len(self.products))
        }
        return results

    def process_product_through_workstations(self, product):
        """Moves a product through all 6 workstations, handling failures and supply needs."""
        random_choice = random.choice([3, 4])

        # For to go to each station
        for i in range(6):

            station = self.workstations[i]

            if i == 3:
                station = self.workstations[random_choice]
            elif i == 4:
                if random_choice == 3:
                    station = self.workstations[4]
                else:
                    station = self.workstations[3]

            # Run the process at the station and wait for result
            result = yield self.env.process(station.process_product(product))

            if not self.simulation_running:
                break

            # If product defect, it is rejected
            if not result:
                self.rejected_products += 1
                return  # And stops the process

    def generate_products(self):
        """Generates products at the start and moves them through the system."""
        product_id = 0
        while self.simulation_running:
            try:
                product = Product(product_id)
                product_id += 1
                self.products.append(product)
                self.env.process(self.process_product_through_workstations(product))
                self.check_for_accident()
                if env.now == self.timeLimit - 1:
                    print(f"Simulation finished succesfully in time. {env.now + 1}")

                yield self.env.timeout(1)  # Generates a product each time unit
            except simpy.Interrupt:
                print('The bank is closes at %.2f get out' % (self.env.now))
        if not self.simulation_running:
            print(f"Simulation has interrupted in time. {env.now}")

    def check_for_accident(self):
        # (10) There is a chance that an accident occurs and the factory stops production.
        if random.random() < 0.01:
            self.accidents += 1
            # print("Accident occurred! Production stopped.")
            self.simulation_running = False
            return True
        return False

    def calculate_bottleneck_delay(self):
        bottleneck_delay = 0
        for ws in self.workstations:
            # (6) Each station has a mean time of work and fix time
            if ws.occupancy > ws.work_time_mean * 1.25:
                bottleneck_delay += ws.occupancy - ws.work_time_mean
        return bottleneck_delay / len(self.workstations) if len(self.workstations) > 0 else 1

    def get_workstations_occupancy(self):
        return {ws.name: round(ws.occupancy, 2) for ws in self.workstations}

    def get_workstation_downtime(self):
        return {ws.name: round(ws.downtime, 2) for ws in self.workstations}


for i in range(100):
    env = simpy.Environment()
    failure_rates = [0.02, 0.01, 0.05, 0.15, 0.07, 0.06]  # (4) Chance of failure for station
    defect_rate = 0.05 # (9) chance of product defect
    factory = Factory(env, num_workstations=6, failure_rates=failure_rates, work_time_mean=10, fix_time_mean=3,
                      defect_rate=defect_rate)
    print("-------------------Results-------------------")
    results = factory.run_simulation(5000)
    print(json.dumps(results, indent=3))
