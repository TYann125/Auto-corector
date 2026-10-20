import json
import os
from typing import Dict

class UserLearning:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.user_dictionary: Dict[str, int] = {}
        self.load()

    def load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.user_dictionary = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.user_dictionary = {}
        else:
            self.user_dictionary = {}

    def save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.user_dictionary, f, ensure_ascii=False, indent=2)

    def learn_word(self, word: str):
        if not word:
            return
        word = word.lower()
        self.user_dictionary[word] = self.user_dictionary.get(word, 0) + 1
        # Save periodically or on certain conditions? 
        # For a daemon, we might want to save every X words or on exit.
        # For now, let's save on every learn to be safe, but consider performance.
        self.save()

    def get_frequency(self, word: str) -> int:
        return self.user_dictionary.get(word.lower(), 0)

    def get_all_learned_words(self) -> Dict[str, int]:
        return self.user_dictionary
