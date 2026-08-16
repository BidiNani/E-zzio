class EpisodeStore:
    def __init__(self):
        self.episodes = []

    def save_episode(self, episode: dict):
        self.episodes.append(episode)
