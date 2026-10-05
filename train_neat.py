import math
import random
import pygame
import pickle
from pathlib import Path

from neat.config import Config
from neat.genome import DefaultGenome
from neat.nn import FeedForwardNetwork
from neat.population import Population
from neat.reporting import StdOutReporter
from neat.reproduction import DefaultReproduction
from neat.species import DefaultSpeciesSet
from neat.statistics import StatisticsReporter
from neat.stagnation import DefaultStagnation

from traffic import TRAFFIC_NODES, get_rotated_resources

pygame.init()
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("NEAT — Навчання об'їзду заторів")


class NEATCar:
    def __init__(self, start_node_id, car_id):
        self.id = car_id
        node_data = TRAFFIC_NODES[start_node_id]
        self.pos = pygame.Vector2(node_data["pos"])
        self.target_node = random.choice(node_data["next"])

        target_pos = pygame.Vector2(TRAFFIC_NODES[self.target_node]["pos"])
        diff_vec = target_pos - self.pos
        self.angle = math.degrees(math.atan2(diff_vec.y, diff_vec.x)) + 180

        self.speed = 0
        self.max_speed = 4.0
        self.is_alive = True
        self.stuck_time = 0

    def get_sensors(self, other_cars):
        sensors = [200.0] * 5
        angles = [0, -30, 30, -60, 60]

        for i, angle_offset in enumerate(angles):
            rad = math.radians(self.angle + 180 + angle_offset)
            ray_dir = pygame.Vector2(math.cos(rad), math.sin(rad))

            for other in other_cars:
                if other.id == self.id:
                    continue
                vec_to_other = other.pos - self.pos
                dist = vec_to_other.length()

                if 0 < dist < 200:
                    dot = ray_dir.dot(vec_to_other.normalize())
                    if dot > 0.9:
                        sensors[i] = min(sensors[i], dist)

        return sensors

    def update(self, outputs):
        if not self.is_alive:
            return

        steering = outputs[0]
        throttle = outputs[1]

        self.angle += steering * 5.0

        if throttle > 0:
            self.speed = min(self.max_speed, self.speed + 0.2)
        else:
            self.speed = max(0.0, self.speed - 0.3)

        forward_vec = pygame.Vector2(1, 0).rotate(self.angle + 180)
        self.pos += forward_vec * self.speed

        if self.speed < 0.5:
            self.stuck_time += 1
            if self.stuck_time > 120:
                self.is_alive = False
        else:
            self.stuck_time = max(0, self.stuck_time - 1)

        target_pos = pygame.Vector2(TRAFFIC_NODES[self.target_node]["pos"])
        if self.pos.distance_to(target_pos) < 50:
            self.target_node = random.choice(TRAFFIC_NODES[self.target_node]["next"])

    def draw(self, surface, camera_off):
        if not self.is_alive:
            return
        draw_pos = self.pos + camera_off
        img = get_rotated_resources(self.angle)
        surface.blit(img, img.get_rect(center=(int(draw_pos.x), int(draw_pos.y))))


def eval_genomes(genomes, config):
    cars = []
    nets = []
    ge = []

    nodes_list = list(TRAFFIC_NODES.keys())

    for _genome_id, genome in genomes:
        genome.fitness = 0.0
        net = FeedForwardNetwork.create(genome, config)

        start_node = random.choice(nodes_list)
        car = NEATCar(start_node, len(cars))

        cars.append(car)
        nets.append(net)
        ge.append(genome)

    clock = pygame.time.Clock()
    frame_count = 0

    while frame_count < 600:
        frame_count += 1
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        alive_count = 0
        for i, car in enumerate(cars):
            if not car.is_alive:
                continue

            alive_count += 1
            sensors = car.get_sensors(cars)
            outputs = nets[i].activate(sensors)
            car.update(outputs)

            ge[i].fitness += car.speed * 0.1

            if min(sensors) < 100 and car.speed > 2.0:
                ge[i].fitness += 2.0

        if alive_count == 0:
            break

        screen.fill((30, 30, 30))
        camera_off = pygame.Vector2(WIDTH // 2, HEIGHT // 2)
        for car in cars:
            if car.is_alive:
                camera_off -= car.pos
                break

        for car in cars:
            car.draw(screen, camera_off)

        pygame.display.flip()


def run_neat():
    config_path = str(Path(__file__).resolve().with_name("config-feedforward.txt"))

    config = Config(
        DefaultGenome,
        DefaultReproduction,
        DefaultSpeciesSet,
        DefaultStagnation,
        config_path,
    )

    p = Population(config)
    p.add_reporter(StdOutReporter(True))
    stats = StatisticsReporter()
    p.add_reporter(stats)

    winner = p.run(eval_genomes, 30)

    output_path = Path(__file__).resolve().with_name("best_brain.pkl")
    with output_path.open("wb") as f:
        pickle.dump(winner, f)
    print("\n✅ Навчання завершено! Найкращий мозок збережено у 'best_brain.pkl'")


if __name__ == "__main__":
    run_neat()