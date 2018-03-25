from argparse import ArgumentParser
from collections import deque

import gym
import numpy as np
import pandas as pd

from models.ddqn import DDQN
from models.dqn import DQN
from models.dqn_plain import DQNPlain
from utils.logger import logger
from utils.memory_bank import MemoryBank

# Params for cart pole
n_episodes = 3000
epsilon = 0.99
epsilon_min = 0.003
batch_size = 128
gamma = 0.99
memory_bank_size = 5000
learning_rate = 0.005
update_rate = 10000
loss = 'mse'

# Initialize environment
env_name = 'CartPole-v0'
env = gym.make(env_name)
nS = env.observation_space.shape[0]
nA = env.env.action_space.n

# Initialize
memory_bank = MemoryBank(memory_bank_size)


def train_main(args):
    # Initialize memory bank and model
    memory_bank = MemoryBank(memory_bank_size)

    if args.model == 'dqn_plain':
        model = DQNPlain(nS, nA, [64], gamma, learning_rate, epsilon, epsilon_min, loss)
    elif args.model == 'dqn':
        model = DQN(nS, nA, [64], gamma, learning_rate, epsilon, epsilon_min, 1000, loss)
    elif args.model == 'ddqn':
        model = DDQN(nS, nA, [64], gamma, learning_rate, epsilon, epsilon_min, 1000, loss)

    # Initialize logging variables
    reward_list = deque()
    current_index = 0
    train_log = deque()

    for episode in range(n_episodes):
        state = env.reset()
        done = False
        steps = 0
        total_reward = 0

        while not done:
            action, e = model.take_action(state, episode)
            new_state, reward, done, info = env.step(action)
            memory_bank.add(state, action, reward, new_state, done)

            state = new_state

            if current_index > memory_bank_size:
                # Get minibatch
                minibatch = memory_bank.get_mini_batch(batch_size)

                # Train on minibatch
                model.train_minibatch(minibatch)

            steps += 1
            total_reward += int(reward)
            current_index += 1

            if (args.render_env == 'y') and (episode % args.render_freq == 0):
                env.render()

        reward_list.append(total_reward)
        moving_average = np.mean(reward_list)
        if len(reward_list) > 100:
            reward_list.popleft()

        train_log.append((episode, steps, e, total_reward, moving_average))
        logger.info(
            'Ep: {} | Steps: {} | epsilon: {:.3f} | reward: {} | moving average: {:.2f}'.format(episode, steps, e,
                                                                                                total_reward,
                                                                                                moving_average))
        if moving_average > 150:
            break

    # Save log and model weights
    train_df = pd.DataFrame(data=list(train_log),
                            columns=['episode', 'steps', 'epsilon', 'total_reward', 'moving_average'])
    train_df.to_csv('./logs/{}_{}_log.csv'.format(env_name, args.model), index=False)

    # Save memory bank and weights
    memory_bank.save_memory('./logs/{}_memory_bank'.format(env_name))
    model.save_model('./logs/{}_{}_weights'.format(env_name, args.model))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--model', default='ddqn',
                        help='DeepRL model to use (options: dqn_plain, dqn, ddqn; default: %(default)s)')
    parser.add_argument('--render-env', default='y', help='Whether to render the environment (default: %(default)s)')
    parser.add_argument('--render-freq', type=int, default=100,
                        help='How frequently to render the env (default: %(default)s) '
                             '--render-env must be set to "y" to render environment')

    args = parser.parse_args()
    train_main(args)
