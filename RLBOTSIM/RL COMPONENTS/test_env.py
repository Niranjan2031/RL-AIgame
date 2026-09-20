"""
test_env.py

Standalone validation for TacticalShooterEnv.

This does NOT start the PyGame game. It uses lightweight test doubles
to verify the Gymnasium environment contract, all 13 actions,
20-value observations, weapon switching, shooting, rewards,
termination and reset behavior.

Run from the RL COMPONENTS folder:
    python test_env.py
"""

import math
import numpy as np

from tactical_shooter_env import TacticalShooterEnv


class DummyPlayer:
    def __init__(self):
        self.x = 600.0
        self.y = 300.0
        self.width = 40.0
        self.height = 40.0
        self.health = 30.0


class DummyBot:
    RL_MELEE_RANGE = 75.0

    WEAPONS = {
        "handgun": {"max_ammo": 12, "damage": 1, "melee_damage": 1},
        "shotgun": {"max_ammo": 6, "damage": 4, "melee_damage": 4},
        "rifle": {"max_ammo": 30, "damage": 1, "melee_damage": 1},
        "knife": {"max_ammo": 0, "damage": None, "melee_damage": 5},
    }

    def __init__(self):
        self.x = 200.0
        self.y = 300.0
        self.width = 40.0
        self.height = 40.0
        self.health = 30.0
        self.max_health = 30.0
        self.alive = True

        self.current_weapon = "handgun"
        self.max_ammo = 12
        self.ammo = 12

        self.facing_x = 1.0
        self.facing_y = 0.0

        self.rl_target_x = None
        self.rl_target_y = None
        self.rl_target_weapon = None

        self.navigation_bounds = (
            0.0,
            0.0,
            1000.0,
            700.0
        )

    def get_center(self):
        return (
            self.x + self.width / 2,
            self.y + self.height / 2
        )

    def aim_at(self, x, y):
        cx, cy = self.get_center()
        dx = x - cx
        dy = y - cy
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            self.facing_x = dx / distance
            self.facing_y = dy / distance

    def move(self, direction, obstacles=None, sprint=False):
        speed = 3.0 if sprint else 2.3

        if direction == "forward":
            dx = self.facing_x * speed
            dy = self.facing_y * speed
        elif direction == "backward":
            dx = -self.facing_x * speed
            dy = -self.facing_y * speed
        elif direction == "left":
            dx = self.facing_y * speed
            dy = -self.facing_x * speed
        elif direction == "right":
            dx = -self.facing_y * speed
            dy = self.facing_x * speed
        else:
            return

        self.x += dx
        self.y += dy

        left, top, right, bottom = self.navigation_bounds

        self.x = max(
            left,
            min(self.x, right - self.width)
        )
        self.y = max(
            top,
            min(self.y, bottom - self.height)
        )

    def shoot(self):
        if self.current_weapon == "knife":
            return False

        if self.ammo <= 0:
            return False

        self.ammo -= 1
        return True

    def reload(self):
        if self.current_weapon == "knife":
            return False

        self.ammo = self.max_ammo
        return True

    def melee_attack(self):
        return self.alive

    def switch_to_weapon(self, weapon):
        if weapon not in self.WEAPONS:
            return False

        self.current_weapon = weapon
        self.max_ammo = self.WEAPONS[weapon]["max_ammo"]
        self.ammo = self.max_ammo
        return True

    def switch_weapon(self):
        weapons = [
            "handgun",
            "shotgun",
            "rifle",
            "knife"
        ]

        index = weapons.index(self.current_weapon)
        return self.switch_to_weapon(
            weapons[(index + 1) % len(weapons)]
        )

    def get_damage(self):
        return self.WEAPONS[
            self.current_weapon
        ]["damage"]

    def get_melee_damage(self):
        return self.WEAPONS[
            self.current_weapon
        ]["melee_damage"]

    def collect_pickups(self, health_pickups, ammo_pickups):
        bot_rect = (
            self.x,
            self.y,
            self.width,
            self.height
        )

        def collides(pickup):
            px = pickup["x"]
            py = pickup["y"]

            return (
                bot_rect[0] < px + 13
                and
                bot_rect[0] + bot_rect[2] > px
                and
                bot_rect[1] < py + 13
                and
                bot_rect[1] + bot_rect[3] > py
            )

        for pickup in health_pickups:
            if (
                not pickup.get("collected", False)
                and collides(pickup)
            ):
                pickup["collected"] = True
                self.health = min(
                    self.max_health,
                    self.health + 15
                )
                break

        for pickup in ammo_pickups:
            if (
                not pickup.get("collected", False)
                and collides(pickup)
            ):
                pickup["collected"] = True
                self.ammo = self.max_ammo
                break


def player_center():
    return (
        player.x + player.width / 2,
        player.y + player.height / 2
    )


def shoot_callback(bot):
    """
    Test-world equivalent of a successful RL-bot bullet hit.
    Uses the RL bot's actual weapon damage values.
    """
    if bot.shoot():
        damage = bot.get_damage()

        if damage is not None:
            player.health = max(
                0.0,
                player.health - damage
            )


def melee_callback(bot):
    if bot.melee_attack():
        distance = math.dist(
            bot.get_center(),
            player_center()
        )

        if distance <= bot.RL_MELEE_RANGE:
            player.health = max(
                0.0,
                player.health - bot.get_melee_damage()
            )

        return True

    return False


def run_tests():
    global player

    player = DummyPlayer()
    bot = DummyBot()

    env = TacticalShooterEnv()

    env.set_game_state(
        player=player,
        bot=bot,
        obstacles=[],
        health_pickups=[],
        ammo_pickups=[],
        shoot_callback=shoot_callback,
        melee_callback=melee_callback
    )

    observation, info = env.reset()

    # =====================================================
    # RESET / SPACES
    # =====================================================

    assert env.action_space.n == 13
    assert observation.shape == (20,)
    assert observation.dtype == np.float32
    assert env.observation_space.contains(observation)

    print("PASS: reset and spaces (13 actions / 20 observations)")

    # =====================================================
    # ALL 13 ACTIONS
    # =====================================================

    # Make sure every action can execute without an exception.
    for action in range(13):
        bot.alive = True
        bot.health = 30.0
        player.health = 30.0

        # Shoot requires a gun with ammunition.
        if action == 6:
            bot.switch_to_weapon("handgun")

        env.step(action)

    print("PASS: all 13 actions execute")

    # =====================================================
    # DIRECT WEAPON ACTIONS
    # =====================================================

    weapon_actions = {
        9: "handgun",
        10: "shotgun",
        11: "rifle",
        12: "knife"
    }

    for action, expected_weapon in weapon_actions.items():
        env.step(action)

        assert bot.current_weapon == expected_weapon
        assert bot.rl_target_weapon is None

    print("PASS: direct weapon actions (9-12)")

    # =====================================================
    # SHOOTING
    # =====================================================

    env.reset()

    bot.switch_to_weapon("handgun")
    old_ammo = bot.ammo
    old_player_health = player.health

    bot.rl_target_x = player_center()[0]
    bot.rl_target_y = player_center()[1]

    _, reward, terminated, truncated, _ = env.step(6)

    assert bot.ammo == old_ammo - 1
    assert player.health < old_player_health
    assert reward > 0.0
    assert terminated is False
    assert truncated is False

    print("PASS: RL bot gun shooting and damage reward")

    # =====================================================
    # KNIFE CANNOT SHOOT
    # =====================================================

    env.reset()

    env.step(12)

    old_ammo = bot.ammo
    old_player_health = player.health

    env.step(6)

    assert bot.current_weapon == "knife"
    assert bot.ammo == old_ammo
    assert player.health == old_player_health

    print("PASS: knife does not fire bullets")

    # =====================================================
    # RELOAD
    # =====================================================

    env.reset()

    env.step(9)
    bot.ammo = 0

    env.step(7)

    assert bot.ammo == bot.max_ammo
    assert bot.ammo == 12

    print("PASS: reload")

    # =====================================================
    # MELEE DAMAGE
    # =====================================================

    env.reset()

    # Put the player close enough for melee.
    bot.x = 200.0
    bot.y = 300.0
    player.x = 240.0
    player.y = 300.0

    env.step(12)

    old_player_health = player.health

    env.step(8)

    assert player.health < old_player_health
    assert old_player_health - player.health == 5.0

    print("PASS: RL bot melee damage")

    # =====================================================
    # BOT-DEATH TERMINATION
    # =====================================================

    env.reset()

    bot.health = 0.0
    bot.alive = False

    _, reward, terminated, truncated, _ = env.step(0)

    assert terminated is True
    assert reward < 0.0

    print("PASS: bot death termination")

    # =====================================================
    # PLAYER-DEATH TERMINATION
    # =====================================================

    bot.health = 30.0
    bot.alive = True

    env.reset()

    player.health = 0.0

    _, reward, terminated, truncated, _ = env.step(0)

    assert terminated is True
    assert reward > 0.0

    print("PASS: player death termination")

    # =====================================================
    # FINAL VALIDATION
    # =====================================================

    bot.health = 30.0
    bot.alive = True
    player.health = 30.0

    env.reset()

    validation = env.validate()

    assert validation["observation_shape"] == (20,)
    assert validation["observation_valid"] is True

    print("PASS: environment validation")

    print("\nAll TacticalShooterEnv tests passed.")


if __name__ == "__main__":
    run_tests()
