import numpy as np
import pytest

import gymnasium
from gymnasium.wrappers import RecordEpisodeStatistics, VectorListInfo
from gymnasium.wrappers.record_episode_statistics import add_vector_episode_statistics


@pytest.mark.parametrize("env_id", ["CartPole-v1", "Pendulum-v1"])
@pytest.mark.parametrize("deque_size", [2, 5])
def test_record_episode_statistics(env_id, deque_size):
    env = gymnasium.make(env_id, disable_env_checker=True)
    env = RecordEpisodeStatistics(env, deque_size)

    for n in range(5):
        env.reset()
        assert env.episode_returns is not None and env.episode_lengths is not None
        assert env.episode_returns[0] == 0.0
        assert env.episode_lengths[0] == 0
        for t in range(env.spec.max_episode_steps):
            _, _, terminated, truncated, info = env.step(env.action_space.sample())
            if terminated or truncated:
                assert "episode" in info
                assert all([item in info["episode"] for item in ["r", "l", "t"]])
                break
    assert len(env.return_queue) == deque_size
    assert len(env.length_queue) == deque_size


def test_record_episode_statistics_reset_info():
    env = gymnasium.make("CartPole-v1", disable_env_checker=True)
    env = RecordEpisodeStatistics(env)
    ob_space = env.observation_space
    obs, info = env.reset()
    assert ob_space.contains(obs)
    assert isinstance(info, dict)


@pytest.mark.parametrize(
    ("num_envs", "asynchronous"), [(1, False), (1, True), (4, False), (4, True)]
)
def test_record_episode_statistics_with_vectorenv(num_envs, asynchronous):
    envs = gymnasium.vector.make(
        "CartPole-v1",
        render_mode=None,
        num_envs=num_envs,
        asynchronous=asynchronous,
        disable_env_checker=True,
    )
    envs = RecordEpisodeStatistics(envs)
    max_episode_step = (
        envs.env_fns[0]().spec.max_episode_steps
        if asynchronous
        else envs.env.envs[0].spec.max_episode_steps
    )
    envs.reset()
    for _ in range(max_episode_step + 1):
        _, _, terminateds, truncateds, infos = envs.step(envs.action_space.sample())
        if any(terminateds) or any(truncateds):
            assert "episode" in infos
            assert "_episode" in infos
            assert all(infos["_episode"] == np.bitwise_or(terminateds, truncateds))
            assert all([item in infos["episode"] for item in ["r", "l", "t"]])
            break
        else:
            assert "episode" not in infos
            assert "_episode" not in infos


def test_wrong_wrapping_order():
    envs = gymnasium.vector.make("CartPole-v1", num_envs=3, disable_env_checker=True)
    wrapped_env = RecordEpisodeStatistics(VectorListInfo(envs))
    wrapped_env.reset()

    with pytest.raises(AssertionError):
        wrapped_env.step(wrapped_env.action_space.sample())


def test_add_vector_episode_statistics():
    NUM_ENVS = 5

    info = {}
    for i in range(NUM_ENVS):
        episode_info = {
            "episode": {
                "r": i,
                "l": i,
                "t": i,
            }
        }
        info = add_vector_episode_statistics(info, episode_info["episode"], NUM_ENVS, i)
        assert np.alltrue(info["_episode"][: i + 1])

        for j in range(NUM_ENVS):
            if j <= i:
                assert info["episode"]["r"][j] == j
                assert info["episode"]["l"][j] == j
                assert info["episode"]["t"][j] == j
            else:
                assert info["episode"]["r"][j] == 0
                assert info["episode"]["l"][j] == 0
                assert info["episode"]["t"][j] == 0
