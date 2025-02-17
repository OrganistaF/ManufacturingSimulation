import random
import simpy


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
        self.material = 25  # (2) Each station has 25 units of work material
        self.processed_count = 0
        self.total_fix_time = 0
        self.occupancy = 0
        self.downtime = 0
        self.supply_material = SupplyMaterial(env)

    def process_product(self, product):
        """Processes a product, checks for failure, and handles repairs if needed."""

        if self.material <= 0:
            yield self.env.process(self.supply_material.supply(self))
        if random.random() < self.failure_rate: # (4) Si una estación falla, debe repararse antes de continuar.
            fix_time = random.expovariate(1 / self.fix_time_mean)
            self.total_fix_time += fix_time
            self.downtime += fix_time
            yield self.env.timeout(fix_time)  # Simulando tiempo de reparación.

        process_time = max(1, random.gauss(self.work_time_mean, 1))  # Asegura un tiempo mínimo de 1.
        self.occupancy += process_time
        yield self.env.timeout(process_time)  # Simulando trabajo.
        self.processed_count += 1
        self.material -= 1

        # (7) Cada producto tiene una probabilidad de ser defectuoso después de ser procesado.
        if random.random() < self.defect_rate:
            return False  # Producto defectuoso.
        return True  # Producto aprobado.


class SupplyMaterial:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.supply_devices = simpy.Resource(env, capacity=3)
        self.supply_time = 0
        self.occupancy = 0

    def supply(self, workstation: Workstation):
        """Resupplies a workstation with material."""
        with self.supply_devices.request() as request:
            yield request  # Esperar disponibilidad del recurso.
            supply_time = max(1, random.gauss(2, 0.5))  # Distribución normal (promedio de 2).
            self.occupancy += supply_time
            yield self.env.timeout(supply_time)  # Simulando tiempo de suministro.
            workstation.material = 25  # (3) Si una estación se queda sin material, debe reabastecerse.


class Factory:
    def __init__(self, env: simpy.Environment, num_workstations, failure_rates, work_time_mean, fix_time_mean, defect_rate):
        self.env = env
        self.workstations = [
            Workstation(env, i + 1, failure_rates[i], work_time_mean, fix_time_mean, defect_rate)
            for i in range(num_workstations)]
        self.products = []
        self.rejected_products = 0
        self.total_processing_time = 0
        self.accidents = 0
        self.downtime = 0

    def run_simulation(self, time_limit):
        self.env.process(self.generate_products())
        self.env.run(until=time_limit)

        # Collect statistics
        final_production = len(self.products) - self.rejected_products
        avg_fix_time = sum(ws.total_fix_time for ws in self.workstations)
        avg_bottleneck_delay = self.calculate_bottleneck_delay()
        supply_material_occupancy = sum(ws.supply_material.occupancy for ws in self.workstations)

        results = {
            "final_production": final_production,
            "rejected_products": self.rejected_products,
            "total_fix_time": avg_fix_time,
            "avg_bottleneck_delay": avg_bottleneck_delay,
            "workstation_occupancy": self.get_workstations_occupancy(),
            "supplier_occupancy": supply_material_occupancy,
            "workstation_downtime": self.get_workstation_downtime(),
            "faulty_products_rate": self.rejected_products / (1 if len(self.products) == 0 else len(self.products))
        }
        return results

        # final_production = len(self.products) - self.rejected_products
        # avg_fix_time = self.total_repair_time / (1 if len(self.products) == 0 else len(self.products))
        # avg_bottleneck_delay = self.calculate_bottleneck_delay()

        # results = {
        #     "final_production": final_production,
        #     "rejected_products": self.rejected_products,
        #     "total_repair_time": self.total_repair_time,
        #     "avg_fix_time": avg_fix_time,
        #     "avg_bottleneck_delay": avg_bottleneck_delay,
        #     "workstation_occupancy": self.get_workstation_occupancy(),
        #     "supplier_occupancy": self.supply_material.occupancy,
        #     "workstation_downtime": self.get_workstation_downtime(),
        #     "faulty_products_rate": self.rejected_products / (
        #         1 if len(self.products) == 0 else len(self.products)) if len(self.products) > 0 else 0
        # }
        # return results

    def process_product_through_workstations(self, product):
        """Moves a product through all 6 workstations, handling failures and supply needs."""
        for i, station in enumerate(self.workstations):
            if i == 3:  # (5) Después de la estación 3, el trabajo puede ser tomado por la estación 4 o 5.
                station = random.choice([self.workstations[3], self.workstations[4]])
            # Process the product
            result = yield self.env.process(station.process_product(product))

            if not result:  # (8) Si un producto es defectuoso, se cuenta como rechazado.
                self.rejected_products += 1
                return

    def generate_products(self):
        """Generates products at the start and moves them through the system."""
        product_id = 0
        while True:
            product = Product(product_id)
            self.products.append(product)
            self.env.process(self.process_product_through_workstations(product))
            yield self.env.timeout(1)  # Genera un nuevo producto cada unidad de tiempo.

    def check_for_accident(self):
         #(10) Existe una probabilidad del 0.01% de que ocurra un accidente en la fábrica, lo que detendría la producción.
        if random.random() < 0.01 / 24:
            self.accidents += 1
            return True
        return False

    def calculate_bottleneck_delay(self):
        bottleneck_delay = 0
        for ws in self.workstations:
            # (6) Cada estación tiene un tiempo promedio de procesamiento y reparación.
            if ws.occupancy > ws.work_time_mean * 1.5:
                bottleneck_delay += ws.occupancy - ws.work_time_mean
        return bottleneck_delay / len(self.workstations) if len(self.workstations) > 0 else 1

    def get_workstations_occupancy(self):
        return {ws.name: ws.occupancy for ws in self.workstations}

    def get_workstation_downtime(self):
        return {ws.name: ws.downtime for ws in self.workstations}


env = simpy.Environment()
failure_rates = [0.02, 0.01, 0.05, 0.15, 0.07, 0.06]  # (4) Probabilidad de falla por estación.
defect_rate = 0.05 # (9) 0.05 de probabilidad de defecto
factory = Factory(env, num_workstations=6, failure_rates=failure_rates, work_time_mean=4, fix_time_mean=3,
                  defect_rate=defect_rate)

results = factory.run_simulation(5000)

if factory.check_for_accident():
    print("Accident occurred! Production stopped.")

# Print results
for key, value in results.items():
    print(f"{key}: {value}\n")
