import ast
import random
from pathlib import Path

import gym
import numpy as np
import pyvirtualdisplay
import torch
from gym.wrappers import TimeLimit
from stable_baselines3 import SAC, TD3, HerReplayBuffer  # noqa F420
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecVideoRecorder
from wandb.integration.sb3 import WandbCallback

import starship_landing_gym  # noqa F420
import wandb
from starship_landing_gym.wrappers import HistoryWrapper


def main(config):
    seed(config["seed"])  # reproducibility

    run = wandb.init(
        project="starship-landing",
        config=config,
        sync_tensorboard=True,  # auto-upload sb3's tensorboard metrics
        monitor_gym=True,  # auto-upload the videos of agents playing the game
        save_code=True,  # optional
    )

    pyvirtualdisplay.Display(visible=0, size=(1400, 900)).start()

    def make_env():
        env = gym.make(config["env_name"], reward_args=config["reward_args"],
                       random_goal=config["random_goal"],
                       random_init_state=config["random_init_state"],
                       augment_obs=config["augment_obs"])

        check_env(env)
        env = TimeLimit(env, config["max_episode_length"])
        if config["history"] > 1:
            env = HistoryWrapper(env, config["history"])

        env = Monitor(env)  # record stats such as returns

        # seed env
        env.seed(config["seed"])
        env.action_space.seed(config["seed"])
        env.observation_space.seed(config["seed"])

        return env

    env = DummyVecEnv([make_env])
    env = VecVideoRecorder(
        env,
        f"videos/{run.id}",
        record_video_trigger=lambda x: x % 4000 == 0,
        video_length=config["max_episode_length"],
    )

    model = config["model_class"](
        "MultiInputPolicy",
        env,
        replay_buffer_class=HerReplayBuffer if config["use_her"] else None,
        replay_buffer_kwargs=dict(
            n_sampled_goal=config["her_k"],
            goal_selection_strategy=config["goal_selection_strategy"],
            online_sampling=config["online_sampling"],
            max_episode_length=config["max_episode_length"],
            handle_timeout_termination=True,
        ) if config["use_her"] else None,
        batch_size=config["batch_size"],
        policy_kwargs=dict(net_arch=make_net_arch(config["net_arch"])),
        tensorboard_log=f"runs/{run.id}",
        verbose=1,
    )

    try:
        model.learn(
            total_timesteps=config["total_timesteps"],
            callback=WandbCallback(
                gradient_save_freq=100,
                verbose=2
            )
        )
    except KeyboardInterrupt:
        print("Interrupting training.")
        pass

    # upload trained model to wandb
    algo_name = type(model).__name__
    model_path = f"runs/{run.id}/models/{algo_name}.zip"
    model.save(model_path)
    upload_file_to_artifacts(model_path, f"{algo_name}_model", "model")

    run.finish()


def make_net_arch(arch):
    return ast.literal_eval(arch)


def seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = True


def check_config(config):
    if config["use_her"] is False:
        assert config["her_k"] is config["goal_selection_strategy"] is None


def upload_file_to_artifacts(pth, artifact_name, artifact_type):
    print(f"Saving {pth} to {artifact_name}")
    if not isinstance(pth, Path):
        pth = Path(pth)


if __name__ == "__main__":
    config = {
        "model_class": SAC,
        "total_timesteps": 500000,
        "env_name": "StarshipLanding-v0",
        "online_sampling": False,
        "max_episode_length": 500,
        "batch_size": 1024,  # 16384,
        "use_her": True,
        "her_k": 5,
        # Available strategies (cf paper): future, final, episode
        "goal_selection_strategy": "future",
        "history": 10,
        "seed": 1,
        "random_goal": True,
        "random_init_state": True,
        "augment_obs": False,
        "net_arch": "[512, 512, 512]",
        "reward_args": dict(
            distance_penalty=False,
            crash_penalty=True,
            crash_scale=200,
            success_reward=False,
            success_scale=5,
            step_penalty=True,
            step_penalty_scale=0.5
        )
    }

    check_config(config)
    main(config)
