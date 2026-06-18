# Q-learning

Q-learning is a model-free reinforcement learning algorithm. Its primary goal is to enable an agent to learn an optimal policy, which dictates the best action to take in any given state to maximize the cumulative future rewards in an environment.

## Key Concepts:
*   **Q-function (Action-Value Function):** This function estimates the expected future rewards for taking a specific action in a particular state. The Q-value for a state-action pair `(s, a)` represents the "quality" of taking action `a` when in state `s`.
*   **Model-Free:** Q-learning is considered model-free because it does not require a model of the environment (i.e., it doesn't need to know the transition probabilities between states or the exact reward function). Instead, it learns directly from interactions with the environment.
*   **Optimal Policy:** Through repeated interactions and updates to the Q-values, the agent aims to converge on an optimal policy. This policy specifies the action that yields the highest Q-value for each state, thus leading to the maximum possible cumulative reward over time.
*   **Temporal Difference (TD) Learning:** Q-learning uses TD learning to update its Q-values. It updates the estimate for a state-action pair based on the observed reward and the maximum Q-value of the next state. The update rule involves a learning rate and a discount factor to balance immediate and future rewards.

## Applications:
Q-learning has been applied to various problems, including:
*   General Game Playing (GGP) for small-board games like Tic-Tac-Toe, Connect Four, and Hex, where it can achieve high win rates, especially with enhancements like dynamic epsilon-greedy strategies and Monte Carlo Search [1810.06078](https://arxiv.org/abs/1810.06078).
*   Deep Q-Networks (DQNs) extend Q-learning by using deep neural networks to approximate the Q-function, enabling its application to more complex problems with high-dimensional state spaces, such as playing Atari games.

## Enhancements:
To improve the performance of classical Q-learning, especially in General Game Playing, enhancements have been proposed, such as:
*   **Dynamic ε-greedy algorithm:** A modification of the ε-greedy strategy for action selection.
*   **QM-learning:** Combines online search methods like Monte Carlo Search with offline learning to enhance performance [1810.06078](https://arxiv.org/abs/1810.06078).