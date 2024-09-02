# Starship Landing Gym
A Gym env for propulsive rocket landing. 

<p align="center">
  <img width="400" height="500" src="https://raw.githubusercontent.com/Armandpl/starship-landing-gym/master/images/landing.gif">
  <br/>
  <i> Successfull Rocket Landing </i>
</p>

The goal is to bring the rocket above the landing pad with a speed inferior to 5m/s.  

This is slightly modified version of the original [Armandpl's Starship Landing Gym](https://github.com/Armandpl/starship-landing-gym) with upper crash detection and time penalty.

## Installation

`pip install starship-landing-gym`

## Usage

```python
import gym
import starship_landing_gym

env = gym.make("StarshipLanding-v0")

done = False
env.reset()
while not done:
    action = ... # Your agent code here
    obs, reward, done, info = env.step(action)
    env.render()
```
