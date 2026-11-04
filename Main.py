"""
Project: Mobile Ecosystem Survival Sim (Hungry Newborns & Maturity Lockout)
--------------------------------------------------------------------------
- 🔵 Blue Circles: Large Water Holes (Strict solid obstacles; randomized shoreline distribution)
- 🟢 Green Dots: Plants (Take 9 hits base; auto-regenerate over time)
- 🟤 Brown Dots: Meat Carcasses (Take 3 chunks base; 5 chunks if pregnant death)
- 🟣 Purple Dots: Herbivores (Dynamic fear radius, dark green center when pregnant)
- 🔴 Red Dots: Carnivores (Cannibalism, live hunting, dark red center when pregnant)
"""

import pygame
import numpy as np
import sys

pygame.init()

# Auto-detect native mobile/PC screen resolution
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()

pygame.display.set_caption("Nexus // Ecosystem Sim")
clock = pygame.time.Clock()

# Font for UI overlay
try:
    font = pygame.font.SysFont("Arial", 22)
except:
    font = pygame.font.Font(None, 26)

class Ecosystem:
    def __init__(self):
        # Stationary Water Holes: Twice the size, one in middle, two in opposite corners
        self.water_holes = np.array([
            [WIDTH * 0.20, HEIGHT * 0.20, 100],  # Top-Left Corner
            [WIDTH * 0.80, HEIGHT * 0.80, 100],  # Bottom-Right Corner
            [WIDTH * 0.50, HEIGHT * 0.50, 110]   # Middle
        ], dtype=np.float32)

        # Plants (Capped limit)
        self.max_plants = 200
        self.plant_pos = np.zeros((self.max_plants, 2), dtype=np.float32)
        self.plant_hits = np.zeros(self.max_plants, dtype=np.int32)
        self.plant_active = np.zeros(self.max_plants, dtype=bool)
        self.plant_spawn_timer = 0
        
        for i in range(80):
            self.spawn_plant(np.random.uniform(50, WIDTH-50), np.random.uniform(50, HEIGHT-50), hits=9)

        # Meat Carcasses (Brown meat left by dead animals)
        self.max_meat = 50
        self.meat_pos = np.zeros((self.max_meat, 2), dtype=np.float32)
        self.meat_chunks = np.zeros(self.max_meat, dtype=np.int32)
        self.meat_timer = np.zeros(self.max_meat, dtype=np.int32)
        self.meat_active = np.zeros(self.max_meat, dtype=bool)

        # Herbivores (Purple)
        self.max_herbs = 200
        self.h_pos = np.zeros((self.max_herbs, 2), dtype=np.float32)
        self.h_vel = np.zeros((self.max_herbs, 2), dtype=np.float32)
        self.h_food = np.ones(self.max_herbs, dtype=np.float32) * 100.0
        self.h_water = np.ones(self.max_herbs, dtype=np.float32) * 100.0
        self.h_action_timer = np.zeros(self.max_herbs, dtype=np.int32)
        self.h_fade_timer = np.zeros(self.max_herbs, dtype=np.int32)
        self.h_mate_cooldown = np.zeros(self.max_herbs, dtype=np.int32)
        self.h_panic_timer = np.zeros(self.max_herbs, dtype=np.int32)
        self.h_gestation_timer = np.zeros(self.max_herbs, dtype=np.int32)
        self.h_target_plant = np.full(self.max_herbs, -1, dtype=np.int32)
        self.h_target_mate = np.full(self.max_herbs, -1, dtype=np.int32)
        self.h_target_pos = np.full((self.max_herbs, 2), -1.0, dtype=np.float32)
        self.h_active = np.zeros(self.max_herbs, dtype=bool)
        self.h_radius = 7.0
        self.h_speed = 2.0
        
        for i in range(40):
            self.spawn_herbivore(np.random.uniform(50, WIDTH-50), np.random.uniform(50, HEIGHT-50), food=80.0, water=80.0, mate_cooldown=80)

        # Carnivores (Red)
        self.max_carns = 40
        self.c_pos = np.zeros((self.max_carns, 2), dtype=np.float32)
        self.c_vel = np.zeros((self.max_carns, 2), dtype=np.float32)
        self.c_food = np.ones(self.max_carns, dtype=np.float32) * 100.0
        self.c_water = np.ones(self.max_carns, dtype=np.float32) * 100.0
        self.c_action_timer = np.zeros(self.max_carns, dtype=np.int32)
        self.c_fade_timer = np.zeros(self.max_carns, dtype=np.int32)
        self.c_mate_cooldown = np.zeros(self.max_carns, dtype=np.int32)
        self.c_gestation_timer = np.zeros(self.max_carns, dtype=np.int32)
        self.c_target_pos = np.full((self.max_carns, 2), -1.0, dtype=np.float32)
        self.c_active = np.zeros(self.max_carns, dtype=bool)
        self.c_radius = 9.0
        self.c_speed = 2.1

        for i in range(5):
            self.spawn_carnivore(np.random.uniform(50, WIDTH-50), np.random.uniform(50, HEIGHT-50), food=80.0, water=80.0, mate_cooldown=100)

        # Debug UI Indicator (Top-Left)
        self.show_lines = True
        self.button_rect = pygame.Rect(40, 40, 180, 50)

    def is_in_water(self, pos):
        """Returns True if a given coordinate falls inside any water hole."""
        for w in self.water_holes:
            center = w[:2]
            radius = w[2]
            if np.linalg.norm(pos - center) <= radius:
                return True
        return False

    def spawn_plant(self, x, y, hits=9):
        pos = np.array([x, y], dtype=np.float32)
        if self.is_in_water(pos):
            return

        inactive = np.where(~self.plant_active)[0]
        if len(inactive) > 0:
            idx = inactive[0]
            self.plant_pos[idx] = pos
            self.plant_hits[idx] = hits
            self.plant_active[idx] = True

    def spawn_meat(self, x, y, chunks=3):
        pos = np.array([x, y], dtype=np.float32)
        if self.is_in_water(pos):
            return

        inactive = np.where(~self.meat_active)[0]
        if len(inactive) > 0:
            idx = inactive[0]
            self.meat_pos[idx] = pos
            self.meat_chunks[idx] = chunks
            self.meat_timer[idx] = 600
            self.meat_active[idx] = True

    def spawn_herbivore(self, x, y, food=30.0, water=30.0, mate_cooldown=300):
        pos = np.array([x, y], dtype=np.float32)
        if self.is_in_water(pos):
            pos += 40

        inactive = np.where(~self.h_active)[0]
        if len(inactive) > 0:
            idx = inactive[0]
            self.h_pos[idx] = pos
            self.h_vel[idx] = np.random.uniform(-1, 1, 2)
            self.h_vel[idx] /= (np.linalg.norm(self.h_vel[idx]) + 0.001)
            self.h_vel[idx] *= self.h_speed
            self.h_food[idx] = food
            self.h_water[idx] = water
            self.h_action_timer[idx] = 0
            self.h_fade_timer[idx] = 0
            self.h_mate_cooldown[idx] = mate_cooldown  
            self.h_panic_timer[idx] = 0
            self.h_gestation_timer[idx] = 0
            self.h_target_plant[idx] = -1
            self.h_target_mate[idx] = -1
            self.h_target_pos[idx] = [-1.0, -1.0]
            self.h_active[idx] = True

    def spawn_carnivore(self, x, y, food=30.0, water=30.0, mate_cooldown=400):
        pos = np.array([x, y], dtype=np.float32)
        if self.is_in_water(pos):
            pos += 40

        inactive = np.where(~self.c_active)[0]
        if len(inactive) > 0:
            idx = inactive[0]
            self.c_pos[idx] = pos
            self.c_vel[idx] = np.random.uniform(-1, 1, 2)
            self.c_vel[idx] /= (np.linalg.norm(self.c_vel[idx]) + 0.001)
            self.c_vel[idx] *= self.c_speed
            self.c_food[idx] = food
            self.c_water[idx] = water
            self.c_action_timer[idx] = 0
            self.c_fade_timer[idx] = 0
            self.c_mate_cooldown[idx] = mate_cooldown  
            self.c_gestation_timer[idx] = 0
            self.c_target_pos[idx] = [-1.0, -1.0]
            self.c_active[idx] = True

    def get_curved_drain(self, stats):
        drain = np.zeros_like(stats)
        high = stats >= 75.0
        low = ~high
        drain[high] = 0.005
        drain[low] = 0.012 * (1.0 + ((75.0 - stats[low]) / 75.0) * 2.5)
        return drain

    def check_water_edge(self, pos):
        for w in self.water_holes:
            center = w[:2]
            radius = w[2]
            dist = np.linalg.norm(pos - center)
            if dist < radius:
                norm_dir = (pos - center) / (dist + 0.001)
                pos[:] = center + norm_dir * (radius + 6)
                return True
        return False

    def get_safest_water_target(self, agent_idx, agent_type, pos):
        if agent_type == 0:  
            threat_indices = np.where(self.c_active)[0]
            threat_pos_arr = self.c_pos[threat_indices] if len(threat_indices) > 0 else np.empty((0, 2))
        else:  
            threat_indices = np.where(self.c_active)[0]
            threat_indices = [idx for idx in threat_indices if idx != agent_idx]
            threat_pos_arr = self.c_pos[threat_indices] if len(threat_indices) > 0 else np.empty((0, 2))

        best_target = self.water_holes[0, :2]
        max_safety_score = -float('inf')

        for w in self.water_holes:
            w_center = w[:2]
            radius = w[2]
            dist_to_water = np.linalg.norm(w_center - pos)

            threat_score = 0.0
            if len(threat_pos_arr) > 0:
                threat_dists_to_water = np.linalg.norm(threat_pos_arr - w_center, axis=1)
                min_threat_dist = np.min(threat_dists_to_water)
                danger_radius = 280.0
                if min_threat_dist < danger_radius:
                    factor = (1.0 - (min_threat_dist / danger_radius))
                    threat_score = -1200.0 * (factor ** 2)

            safety_score = threat_score - dist_to_water
            if safety_score > max_safety_score:
                max_safety_score = safety_score
                
                rand_angle = np.random.uniform(0, 2 * np.pi)
                best_target = w_center + np.array([np.cos(rand_angle), np.sin(rand_angle)], dtype=np.float32) * (radius + np.random.uniform(6, 20))

        return best_target

    def resolve_agent_collisions(self):
        h_idx = np.where(self.h_active)[0]
        c_idx = np.where(self.c_active)[0]
        
        all_pos, all_radii, all_types, all_indices = [], [], [], []

        for idx in h_idx:
            if self.h_fade_timer[idx] > 0: continue
            all_pos.append(self.h_pos[idx])
            all_radii.append(self.h_radius)
            all_types.append(0)
            all_indices.append(idx)

        for idx in c_idx:
            if self.c_fade_timer[idx] > 0: continue
            all_pos.append(self.c_pos[idx])
            all_radii.append(self.c_radius)
            all_types.append(1)
            all_indices.append(idx)

        n = len(all_pos)
        if n < 2: return

        pos_arr = np.array(all_pos)
        radii_arr = np.array(all_radii)

        diff = pos_arr[:, np.newaxis, :] - pos_arr[np.newaxis, :, :]
        dist_sq = np.sum(diff ** 2, axis=-1)
        r_sum = radii_arr[:, np.newaxis] + radii_arr[np.newaxis, :]
        collision_mask = (dist_sq < (r_sum ** 2)) & (dist_sq > 0)
        
        rows, cols = np.nonzero(collision_mask)
        unique_pairs = rows < cols
        
        for i, j in zip(rows[unique_pairs], cols[unique_pairs]):
            p1, p2 = pos_arr[i], pos_arr[j]
            delta = p2 - p1
            dist = np.linalg.norm(delta)
            if dist == 0: continue
            
            norm = delta / dist
            overlap = (r_sum[i, j] - dist) * 0.45
            p1 -= norm * overlap
            p2 += norm * overlap
            
            t1, idx1 = all_types[i], all_indices[i]
            t2, idx2 = all_types[j], all_indices[j]
            
            if t1 == 0: self.h_pos[idx1] = p1
            else: self.c_pos[idx1] = p1
                
            if t2 == 0: self.h_pos[idx2] = p2
            else: self.c_pos[idx2] = p2

    def update(self):
        cur_w, cur_h = screen.get_size()
        center_screen = np.array([cur_w / 2.0, cur_h / 2.0], dtype=np.float32)
        drink_rate = 12.0

        self.h_mate_cooldown = np.maximum(0, self.h_mate_cooldown - 1)
        self.c_mate_cooldown = np.maximum(0, self.c_mate_cooldown - 1)
        self.h_panic_timer = np.maximum(0, self.h_panic_timer - 1)

        # --- AUTO-REGENERATE PLANTS OVER TIME ---
        self.plant_spawn_timer += 1
        if self.plant_spawn_timer >= 25:
            self.plant_spawn_timer = 0
            active_count = np.sum(self.plant_active)
            if active_count < self.max_plants:
                self.spawn_plant(np.random.uniform(50, cur_w - 50), np.random.uniform(50, cur_h - 50), hits=9)

        # --- UPDATE MEAT CARCASSES ---
        meat_idx = np.where(self.meat_active)[0]
        if len(meat_idx) > 0:
            self.meat_timer[meat_idx] -= 1
            expired_meat = meat_idx[self.meat_timer[meat_idx] <= 0]
            for em in expired_meat:
                self.meat_active[em] = False
                plant_hits = 5 if self.meat_chunks[em] >= 4 else 9
                self.spawn_plant(self.meat_pos[em, 0], self.meat_pos[em, 1], hits=plant_hits)

        # --- 1. HERBIVORE AI ---
        h_idx = np.where(self.h_active)[0]
        if len(h_idx) > 0:
            healthy_mask = self.h_fade_timer[h_idx] == 0
            healthy_h = h_idx[healthy_mask]
            if len(healthy_h) > 0:
                drain_mult = np.where(self.h_gestation_timer[healthy_h] > 0, 1.75, 1.0)
                self.h_food[healthy_h] -= self.get_curved_drain(self.h_food[healthy_h]) * drain_mult
                self.h_water[healthy_h] -= self.get_curved_drain(self.h_water[healthy_h]) * drain_mult

                starve_deaths = healthy_h[(self.h_food[healthy_h] <= 0) | (self.h_water[healthy_h] <= 0)]
                for d in starve_deaths:
                    self.h_active[d] = False
                    chunks = 5 if self.h_gestation_timer[d] > 0 else 3
                    self.spawn_meat(self.h_pos[d, 0], self.h_pos[d, 1], chunks=chunks)

            fading_h = h_idx[self.h_fade_timer[h_idx] > 0]
            for f in fading_h:
                self.h_fade_timer[f] -= 1
                if self.h_fade_timer[f] <= 0:
                    self.h_active[f] = False
                    chunks = 5 if self.h_gestation_timer[f] > 0 else 3
                    self.spawn_meat(self.h_pos[f, 0], self.h_pos[f, 1], chunks=chunks)

            h_idx = np.where(self.h_active)[0]

        for i in h_idx:
            if self.h_fade_timer[i] > 0: continue

            if self.h_gestation_timer[i] > 0:
                self.h_gestation_timer[i] -= 1
                if self.h_gestation_timer[i] == 0:
                    if len(h_idx) < self.max_herbs - 1:
                        self.spawn_herbivore(self.h_pos[i, 0], self.h_pos[i, 1], food=25.0, water=25.0, mate_cooldown=300)

            pos = self.h_pos[i]
            self.h_target_pos[i] = [-1.0, -1.0]

            if self.h_action_timer[i] > 0:
                self.h_action_timer[i] -= 1
                self.check_water_edge(pos)
                continue

            steering = np.zeros(2, dtype=np.float32)

            vital_min = min(self.h_food[i], self.h_water[i])
            dynamic_flee_dist = 60.0 + (vital_min / 100.0) * 100.0

            c_active = np.where(self.c_active)[0]
            fleeing = False
            if len(c_active) > 0:
                c_pos = self.c_pos[c_active]
                c_dists = np.linalg.norm(c_pos - pos, axis=1)
                nearest_c = np.argmin(c_dists)
                if c_dists[nearest_c] < dynamic_flee_dist:
                    flee_dir = pos - c_pos[nearest_c]
                    steering += flee_dir / (np.linalg.norm(flee_dir) + 0.1) * 4.0
                    fleeing = True
                    
                    self.h_panic_timer[i] = 120
                    self.h_target_plant[i] = -1
                    self.h_target_mate[i] = -1
                    self.h_target_pos[i] = c_pos[nearest_c]

            if not fleeing:
                for w in self.water_holes:
                    if w[2] <= np.linalg.norm(pos - w[:2]) <= w[2] + 15 and self.h_water[i] < 60.0:
                        self.h_water[i] = min(100.0, self.h_water[i] + drink_rate)
                        self.h_action_timer[i] = 20
                        self.h_target_plant[i] = -1
                        self.h_target_mate[i] = -1
                        break

                if self.h_panic_timer[i] > 0:
                    steering += self.h_vel[i] * 0.8 + np.random.uniform(-0.6, 0.6, 2)

                elif self.h_food[i] < 85.0:
                    self.h_target_mate[i] = -1
                    p_active = np.where(self.plant_active)[0]
                    
                    current_target = self.h_target_plant[i]
                    if current_target == -1 or not self.plant_active[current_target]:
                        if len(p_active) > 0:
                            p_pos = self.plant_pos[p_active]
                            p_dists = np.linalg.norm(p_pos - pos, axis=1) + np.random.uniform(0, 20, len(p_active))
                            best_local = np.argmin(p_dists)
                            self.h_target_plant[i] = p_active[best_local]
                        else:
                            self.h_target_plant[i] = -1

                    target_idx = self.h_target_plant[i]
                    if target_idx != -1 and self.plant_active[target_idx]:
                        target = self.plant_pos[target_idx]
                        self.h_target_pos[i] = target
                        dist_to_plant = np.linalg.norm(target - pos)
                        
                        if dist_to_plant < 15:
                            self.plant_hits[target_idx] -= 1
                            self.h_food[i] = min(100.0, self.h_food[i] + 35.0)
                            self.h_action_timer[i] = 20
                            if self.plant_hits[target_idx] <= 0:
                                self.plant_active[target_idx] = False
                                self.h_target_plant[i] = -1
                        else:
                            dir_vec = target - pos
                            steering += dir_vec / (np.linalg.norm(dir_vec) + 0.1) * 2.0

                elif self.h_water[i] < 60.0:
                    self.h_target_plant[i] = -1
                    self.h_target_mate[i] = -1
                    target = self.get_safest_water_target(i, 0, pos)
                    self.h_target_pos[i] = target
                    dir_vec = target - pos
                    steering += dir_vec / (np.linalg.norm(dir_vec) + 0.1) * 2.0

                elif self.h_food[i] >= 50.0 and self.h_water[i] >= 50.0 and self.h_mate_cooldown[i] == 0 and self.h_gestation_timer[i] == 0 and len(h_idx) > 1:
                    self.h_target_plant[i] = -1
                    other_indices = [idx for idx in h_idx if idx != i and self.h_fade_timer[idx] == 0 and self.h_mate_cooldown[idx] == 0 and self.h_gestation_timer[idx] == 0]
                    ready_mates = [idx for idx in other_indices if self.h_food[idx] >= 50.0 and self.h_water[idx] >= 50.0]
                    
                    current_mate = self.h_target_mate[i]
                    if current_mate == -1 or current_mate not in ready_mates or self.h_fade_timer[current_mate] > 0:
                        if ready_mates:
                            mate_pos_arr = self.h_pos[ready_mates]
                            mate_dists = np.linalg.norm(mate_pos_arr - pos, axis=1) + np.random.uniform(0, 20, len(ready_mates))
                            best_local = np.argmin(mate_dists)
                            self.h_target_mate[i] = ready_mates[best_local]
                        else:
                            self.h_target_mate[i] = -1

                    mate_idx = self.h_target_mate[i]
                    if mate_idx != -1 and mate_idx in ready_mates:
                        mate_pos = self.h_pos[mate_idx]
                        self.h_target_pos[i] = mate_pos
                        dist_to_mate = np.linalg.norm(mate_pos - pos)
                        
                        if dist_to_mate < 30 and len(h_idx) < self.max_herbs - 2:
                            self.h_food[i] -= 30.0
                            self.h_water[i] -= 20.0
                            self.h_mate_cooldown[i] = 120
                            self.h_gestation_timer[i] = 600
                            
                            self.h_food[mate_idx] -= 30.0
                            self.h_water[mate_idx] -= 20.0
                            self.h_mate_cooldown[mate_idx] = 120
                            
                            self.h_target_mate[i] = -1
                            self.h_target_mate[mate_idx] = -1
                        else:
                            dir_vec = mate_pos - pos
                            steering += dir_vec / (np.linalg.norm(dir_vec) + 0.1) * 1.5
                else:
                    self.h_target_plant[i] = -1
                    self.h_target_mate[i] = -1
                    steering += self.h_vel[i] * 0.5 + np.random.uniform(-0.4, 0.4, 2)

            wall_margin = 60
            if pos[0] < wall_margin or pos[0] > cur_w - wall_margin or pos[1] < wall_margin or pos[1] > cur_h - wall_margin:
                wall_steer = center_screen - pos
                steering += wall_steer / (np.linalg.norm(wall_steer) + 0.1) * 1.5

            steer_len = np.linalg.norm(steering)
            if steer_len > 0:
                vel = (steering / steer_len) * self.h_speed
            else:
                vel = self.h_vel[i] if np.linalg.norm(self.h_vel[i]) > 0 else np.array([1.0, 0.0], dtype=np.float32)

            self.h_vel[i] = vel
            pos += vel
            self.check_water_edge(pos)
            self.h_pos[i] = np.clip(pos, 10, [cur_w-10, cur_h-10])

        # --- 2. CARNIVORE AI ---
        c_idx = np.where(self.c_active)[0]
        if len(c_idx) > 0:
            healthy_c_mask = self.c_fade_timer[c_idx] == 0
            healthy_c = c_idx[healthy_c_mask]
            if len(healthy_c) > 0:
                drain_mult = np.where(self.c_gestation_timer[healthy_c] > 0, 1.75, 1.0)
                self.c_food[healthy_c] -= self.get_curved_drain(self.c_food[healthy_c]) * drain_mult
                self.c_water[healthy_c] -= self.get_curved_drain(self.c_water[healthy_c]) * drain_mult

                starve_deaths = healthy_c[(self.c_food[healthy_c] <= 0) | (self.c_water[healthy_c] <= 0)]
                for d in starve_deaths:
                    self.c_active[d] = False
                    chunks = 5 if self.c_gestation_timer[d] > 0 else 3
                    self.spawn_meat(self.c_pos[d, 0], self.c_pos[d, 1], chunks=chunks)

            fading_c = c_idx[self.c_fade_timer[c_idx] > 0]
            for f in fading_c:
                self.c_fade_timer[f] -= 1
                if self.c_fade_timer[f] <= 0:
                    self.c_active[f] = False
                    chunks = 5 if self.c_gestation_timer[f] > 0 else 3
                    self.spawn_meat(self.c_pos[f, 0], self.c_pos[f, 1], chunks=chunks)

            c_idx = np.where(self.c_active)[0]

        for i in c_idx:
            if self.c_fade_timer[i] > 0: continue

            if self.c_gestation_timer[i] > 0:
                self.c_gestation_timer[i] -= 1
                if self.c_gestation_timer[i] == 0:
                    if len(c_idx) < self.max_carns - 1:
                        self.spawn_carnivore(self.c_pos[i, 0], self.c_pos[i, 1], food=25.0, water=25.0, mate_cooldown=400)

            pos = self.c_pos[i]
            self.c_target_pos[i] = [-1.0, -1.0]

            if self.c_action_timer[i] > 0:
                self.c_action_timer[i] -= 1
                self.check_water_edge(pos)
                continue

            steering = np.zeros(2, dtype=np.float32)

            for w in self.water_holes:
                if w[2] <= np.linalg.norm(pos - w[:2]) <= w[2] + 15 and self.c_water[i] < 60.0:
                    self.c_water[i] = min(100.0, self.c_water[i] + drink_rate)
                    self.c_action_timer[i] = 20
                    break

            cannibalized = False
            if self.c_food[i] < 20.0 and len(c_idx) > 1:
                healthy_c_idx = [idx for idx in c_idx if idx != i and self.c_fade_timer[idx] == 0]
                if len(healthy_c_idx) > 0:
                    other_c_pos = self.c_pos[healthy_c_idx]
                    other_c_dists = np.linalg.norm(other_c_pos - pos, axis=1) + np.random.uniform(0, 15, len(healthy_c_idx))
                    closest_c = np.argmin(other_c_dists)
                    
                    target_carn = healthy_c_idx[closest_c]
                    self.c_target_pos[i] = self.c_pos[target_carn]

                    if other_c_dists[closest_c] < 22:
                        self.c_fade_timer[target_carn] = 60
                        self.c_food[i] = 100.0
                        self.c_action_timer[i] = 45
                        cannibalized = True

            if not cannibalized:
                if self.c_food[i] < 75.0:
                    meat_active_idx = np.where(self.meat_active)[0]
                    healthy_h_idx = [idx for idx in h_idx if self.h_fade_timer[idx] == 0]
                    
                    best_food_pos = None
                    is_meat_target = False
                    min_dist = float('inf')
                    target_meat_idx = -1
                    target_herb_idx = -1

                    if len(meat_active_idx) > 0:
                        m_pos = self.meat_pos[meat_active_idx]
                        m_dists = np.linalg.norm(m_pos - pos, axis=1)
                        closest_m = np.argmin(m_dists)
                        if m_dists[closest_m] < min_dist:
                            min_dist = m_dists[closest_m]
                            best_food_pos = m_pos[closest_m]
                            is_meat_target = True
                            target_meat_idx = meat_active_idx[closest_m]

                    if len(healthy_h_idx) > 0:
                        h_p = self.h_pos[healthy_h_idx]
                        h_dists = np.linalg.norm(h_p - pos, axis=1)
                        closest_h = np.argmin(h_dists)
                        if h_dists[closest_h] < min_dist:
                            min_dist = h_dists[closest_h]
                            best_food_pos = h_p[closest_h]
                            is_meat_target = False
                            target_herb_idx = healthy_h_idx[closest_h]

                    if best_food_pos is not None:
                        self.c_target_pos[i] = best_food_pos
                        if min_dist < 22:
                            if is_meat_target:
                                self.meat_chunks[target_meat_idx] -= 1
                                self.c_food[i] = min(100.0, self.c_food[i] + 40.0)
                                self.c_action_timer[i] = 30
                                if self.meat_chunks[target_meat_idx] <= 0:
                                    self.meat_active[target_meat_idx] = False
                            else:
                                self.h_fade_timer[target_herb_idx] = 60
                                self.c_food[i] = 100.0
                                self.c_action_timer[i] = 45
                        else:
                            dir_vec = best_food_pos - pos
                            steering += dir_vec / (np.linalg.norm(dir_vec) + 0.1) * 2.8

                elif self.c_water[i] < 60.0:
                    target = self.get_safest_water_target(i, 1, pos)
                    self.c_target_pos[i] = target
                    dir_vec = target - pos
                    steering += dir_vec / (np.linalg.norm(dir_vec) + 0.1) * 2.2

                elif self.c_food[i] >= 60.0 and self.c_water[i] >= 60.0 and self.c_mate_cooldown[i] == 0 and self.c_gestation_timer[i] == 0 and len(c_idx) > 1:
                    other_indices = [idx for idx in c_idx if idx != i and self.c_fade_timer[idx] == 0]
                    ready_mates = [idx for idx in other_indices if self.c_food[idx] >= 60.0 and self.c_water[idx] >= 60.0 and self.c_mate_cooldown[idx] == 0 and self.c_gestation_timer[idx] == 0]
                    
                    if ready_mates:
                        mate_pos_arr = self.c_pos[ready_mates]
                        mate_dists = np.linalg.norm(mate_pos_arr - pos, axis=1) + np.random.uniform(0, 30, len(ready_mates))
                        
                        sorted_mate_indices = np.argsort(mate_dists)
                        choosable_mates = sorted_mate_indices[:min(4, len(sorted_mate_indices))]
                        chosen_mate_local_idx = np.random.choice(choosable_mates)
                        
                        closest_mate_idx = ready_mates[chosen_mate_local_idx]
                        mate_pos = self.c_pos[closest_mate_idx]
                        self.c_target_pos[i] = mate_pos
                        
                        if np.linalg.norm(mate_pos - pos) < 25 and len(c_idx) < self.max_carns - 1:
                            self.c_food[i] -= 40.0
                            self.c_water[i] -= 30.0
                            self.c_mate_cooldown[i] = 140
                            self.c_gestation_timer[i] = 600

                            self.c_food[closest_mate_idx] -= 40.0
                            self.c_water[closest_mate_idx] -= 30.0
                            self.c_mate_cooldown[closest_mate_idx] = 140

                            recoil_dir = pos - mate_pos
                            norm_recoil = recoil_dir / (np.linalg.norm(recoil_dir) + 0.001)
                            self.c_vel[i] = norm_recoil * self.c_speed * 2.5
                            self.c_vel[closest_mate_idx] = -norm_recoil * self.c_speed * 2.5
                        else:
                            dir_vec = mate_pos - pos
                            steering += dir_vec / (np.linalg.norm(dir_vec) + 0.1) * 1.5
                else:
                    steering += self.c_vel[i] * 0.5 + np.random.uniform(-0.4, 0.4, 2)

            wall_margin = 60
            if pos[0] < wall_margin or pos[0] > cur_w - wall_margin or pos[1] < wall_margin or pos[1] > cur_h - wall_margin:
                wall_steer = center_screen - pos
                steering += wall_steer / (np.linalg.norm(wall_steer) + 0.1) * 1.5

            steer_len = np.linalg.norm(steering)
            if steer_len > 0:
                vel = (steering / steer_len) * self.c_speed
            else:
                vel = self.c_vel[i] if np.linalg.norm(self.c_vel[i]) > 0 else np.array([1.0, 0.0], dtype=np.float32)

            self.c_vel[i] = vel
            pos += vel
            self.check_water_edge(pos)
            self.c_pos[i] = np.clip(pos, 10, [cur_w-10, cur_h-10])

        self.resolve_agent_collisions()

    def draw(self, surface):
        # Draw Water Holes
        for w in self.water_holes:
            pygame.draw.circle(surface, (30, 100, 200), (int(w[0]), int(w[1])), int(w[2]))
            pygame.draw.circle(surface, (60, 160, 255), (int(w[0]), int(w[1])), int(w[2]), 3)

        # Draw Plants (Green Dots)
        p_active = np.where(self.plant_active)[0]
        for idx in p_active:
            p = self.plant_pos[idx]
            pygame.draw.circle(surface, (46, 204, 113), (int(p[0]), int(p[1])), 4)

        # Draw Meat Carcasses
        meat_idx = np.where(self.meat_active)[0]
        for idx in meat_idx:
            m = self.meat_pos[idx]
            m_radius = 8 if self.meat_chunks[idx] > 3 else 6
            pygame.draw.circle(surface, (139, 69, 19), (int(m[0]), int(m[1])), m_radius)

        # Draw Pathfinding Lines (If Toggle is Active)
        if self.show_lines:
            h_idx = np.where(self.h_active)[0]
            for idx in h_idx:
                h = self.h_pos[idx]
                t_pos = self.h_target_pos[idx]
                if t_pos[0] != -1.0:
                    pygame.draw.line(surface, (80, 40, 100), (int(h[0]), int(h[1])), (int(t_pos[0]), int(t_pos[1])), 1)

            c_idx = np.where(self.c_active)[0]
            for idx in c_idx:
                c = self.c_pos[idx]
                t_pos = self.c_target_pos[idx]
                if t_pos[0] != -1.0:
                    pygame.draw.line(surface, (120, 30, 30), (int(c[0]), int(c[1])), (int(t_pos[0]), int(t_pos[1])), 1)

        # Draw Herbivores
        h_idx = np.where(self.h_active)[0]
        for idx in h_idx:
            h = self.h_pos[idx]
            fade = self.h_fade_timer[idx]
            
            if fade > 0:
                ratio = fade / 60.0
                current_radius = max(2.0, self.h_radius * ratio)
                color = (int(155 * ratio), int(89 * ratio), int(182 * ratio))
                pygame.draw.circle(surface, color, (int(h[0]), int(h[1])), int(current_radius))
            else:
                pygame.draw.circle(surface, (155, 89, 182), (int(h[0]), int(h[1])), int(self.h_radius))
                if self.h_gestation_timer[idx] > 0:
                    pygame.draw.circle(surface, (20, 90, 40), (int(h[0]), int(h[1])), 3)

        # Draw Carnivores
        c_idx = np.where(self.c_active)[0]
        for idx in c_idx:
            c = self.c_pos[idx]
            fade = self.c_fade_timer[idx]
            
            if fade > 0:
                ratio = fade / 60.0
                current_radius = max(2.0, self.c_radius * ratio)
                color = (int(231 * ratio), int(76 * ratio), int(60 * ratio))
                pygame.draw.circle(surface, color, (int(c[0]), int(c[1])), int(current_radius))
            else:
                pygame.draw.circle(surface, (231, 76, 60), (int(c[0]), int(c[1])), int(self.c_radius))
                if self.c_gestation_timer[idx] > 0:
                    pygame.draw.circle(surface, (110, 15, 15), (int(c[0]), int(c[1])), 4)

        # Draw Status Indicator Box (Top-Left)
        btn_color = (50, 150, 50) if self.show_lines else (150, 50, 50)
        pygame.draw.rect(surface, btn_color, self.button_rect, border_radius=8)
        pygame.draw.rect(surface, (220, 220, 220), self.button_rect, 2, border_radius=8)
        
        status_text = "Lines: ON" if self.show_lines else "Lines: OFF"
        text_surf = font.render(status_text, True, (255, 255, 255))
        surface.blit(text_surf, (self.button_rect.x + 15, self.button_rect.y + 12))

def main():
    sim = Ecosystem()

    last_tap_time = 0
    double_tap_delay = 400  # milliseconds window for double-tap

    running = True
    while running:
        cur_w, cur_h = screen.get_size()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:  # Press 'L' to toggle lines on PC
                    sim.show_lines = not sim.show_lines
                elif event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                # Double-tap anywhere on screen to toggle lines on mobile / Pydroid
                current_time = pygame.time.get_ticks()
                if current_time - last_tap_time < double_tap_delay:
                    sim.show_lines = not sim.show_lines
                    last_tap_time = 0  # Reset
                else:
                    last_tap_time = current_time

        sim.update()

        screen.fill((20, 20, 25))
        sim.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
