''' Hello Wordle Simulator
Can simulate games of Wordle of 2-15 letters long,
played on 3 levels of difficulty (normal, hard, ultra hard).
Solver is aware of both allowed and secret words dictionaries,
uses imperfect, but fast solution method.
'''

import random
import hashlib
import os
import time  # Only used in main() to time execution

from dataclasses import dataclass

import numpy as np


@dataclass
class SimulationOptions:
    ''' Class for all simulation options
    '''

    # Number of runs
    runs: int = 100

    # Which word length to use
    # (it will get only words of this lengths from the input files)
    word_length: int = 5

    # Wordle difficulty: 0 - Normal, 2 - Hard, 3 - Ultra Hard
    difficulty: int = 0

    # Bot's strength (how many random words to choose the guess from)
    strength: int = 100

    # True to show the detailed info (guess/result) of each game
    verbose: bool = False

    # File to keep log all games (each line is a space separated
    # list of guesses, that goes on, until correct answer is found).
    # Final word is the guess word, if there are 6 or fewer guesses,
    # the game was won.
    logfile_name: str = ""


class WordList():
    ''' Class to keep the list of words (either secret or all)
    Keeps all the words in "words" dict as {n:"word"}
    '''

    def __init__(self, words_file=None, words_len=5, words_list=None):
        ''' New Words list. Take words of length words_len
        from the file words_file and/or list words_list.
        Word list stored as {n:"word"},
        so words could be deleted but we still have their numbers.
        '''
        # Main dict to store words data
        self.words = {}
        # Dict to speed up searching a number by word
        self.reverse = {}

        # Used in "reduce_by_difficulty". Class variable so it we don't have to
        # calculate it over and over again
        self.max_allowed_letter_count = {}

        word_count = 0
        # Add words from the file
        if words_file:
            with open(words_file, "r", encoding="UTF-8") as words:
                for line in words:
                    word = line.strip()
                    if len(word) == words_len and "*" not in word:
                        self.words[word_count] = word
                        self.reverse[word] = word_count
                        word_count += 1

        # Add worlds from the list (useful for debugging)
        if words_list:
            for word in words_list:
                if len(word) == words_len and "*" not in word:
                    self.words[word_count] = word
                    self.reverse[word] = word_count
                    word_count += 1

    def get_distribution(self, guess_n, data):
        ''' Given a number of a guessing word, return list of lengths of
        resulting word lists, if this guess is played.
        data is WData object for lists of secrets and guesses
        '''
        # This is where we store count of words for each possible answer
        answers = set()

        # Go through matrix and find all possible results for this guess
        for secret_n in self.words:
            answer = data.matrix[secret_n][guess_n]
            answers.add(answer)

        return len(answers)

    def find_best_guess(self, guesses, data, strength=100):
        ''' Try "strength" random guesses, and return one
        that produces the longest distribution
        if strength == -1, check all guesses (very slow)
        Return (best word number, resulting distribution length)
        '''
        # If there is one word lest - return this word
        if len(self) == 1:
            only_word = list(self.words.values())[0]
            return guesses.word2n(only_word), 1

        # If the list of possible secret words is small enough:
        # does any of the words in it break down the list into
        # the distribution of maximum possible length.
        # This part is skipped with strength == -1
        # (as we are going to analyze all possible words anyway)
        if len(self) < strength:
            for secret_n in self.words:
                guess_n = guesses.word2n(self.words[secret_n])
                distribution = self.get_distribution(guess_n, data)
                # Resulting distribution is exactly as big as the
                # list of remaining secrets: return that
                if distribution == len(self):
                    return guess_n, distribution

        # Now let's check random guesses and return the best
        best_guess = None
        best_distribution = None

        # Use all words if strength == -1,
        # or random sample if it is an actual number
        if strength == -1:
            guesses_to_analyze = list(guesses.words.keys())
        else:
            guesses_to_analyze = guesses.sample(strength, use_numbers=True)

        for guess_n in guesses_to_analyze:
            distribution = self.get_distribution(guess_n, data)
            if best_distribution is None or distribution > best_distribution:
                best_distribution = distribution
                best_guess = guess_n

        return best_guess, best_distribution

    def reduce_by_guess(self, guess_n, answer, data):
        ''' Given guess (as a number) and an answer (as a list of numbers),
        purge the entries, leaving only those
        in keeping with these guess and answer.
        Used on the list of remaining secret words.
        '''
        words_to_delete = []
        for secret_n in self.words:
            if data.matrix[secret_n][guess_n] != answer:
                words_to_delete.append(secret_n)
        for word_to_delete in words_to_delete:
            del self.words[word_to_delete]

    # Following are functions to be used by reduce_by_difficulty
    @staticmethod
    def check_green(word, guess, answer):
        ''' Check if "GREEN" condition is fulfilled
        Green letter is in that place.
        If found, replace it with "*"
        '''
        for position, (g_letter, g_result) in enumerate(zip(guess, answer)):
            if g_result == 2:
                if g_letter != word[position]:
                    return False
                # remove letter from word
                word[position] = "*"
        return True

    @staticmethod
    def check_yellow_lax(word, guess, answer):
        ''' Check if "SIMPLE YELLOW" condition is fulfilled:
        Yellow letter is in word
        If found, replace it with "*"
        '''
        letter_to_ignore = []
        for g_letter, g_result in zip(guess, answer):
            if g_result == 1:
                if g_letter not in word:
                    return False
                letter_to_ignore.append(g_letter)

        # Remove those yellow letters from the word,
        # so check_grey would leave them alone
        if letter_to_ignore:
            for position, w_letter in enumerate(word):
                if w_letter in letter_to_ignore:
                    # Don't remove it if there is a grey letter in that spot
                    # Will affect difficulty level 2 - we want such letter
                    # to be caught by check_grey
                    if guess[position] != w_letter or answer[position] != 0:
                        word[position] = "*"
        return True

    @staticmethod
    def check_yellow_strict(word, guess, answer):
        ''' Check if "STRICT YELLOW" condition is fulfilled
        Yellow should not contain this letter
        '''
        for position, (g_letter, g_result) in enumerate(zip(guess, answer)):
            if g_result == 1 and g_letter == word[position]:
                return False
        return True

    @staticmethod
    def check_grey(word, guess, answer):
        ''' Check if "GREY" condition is fulfilled:
        Grey letter is not in word
        '''
        for g_letter, g_result in zip(guess, answer):
            if g_result == 0 and g_letter in word:
                return False
        return True

    def calculate_allowed_letter_count(self, guess, answer):
        ''' Check if there is a limit on letter count (it happens when
        you have "green and grey", "yellow and grey" of the same letter
        Add instance variable "max_allowed_letter_count" with
        {letter: max_allowed count}
        '''
        self.max_allowed_letter_count = {}
        greens_n_yellows = []
        greys = []
        # Generate lists of all greys and all not greys
        for g_letter, g_result in zip(guess, answer):
            if g_result == 0:
                greys.append(g_letter)
            else:
                greens_n_yellows.append(g_letter)

        # Allowed count happens when you have greys and not greys
        # It is equal to the number of non-greys in this situation
        for letter in "abcdefghijklmnopqrstuvwxyz":
            if letter in greens_n_yellows and letter in greys:
                self.max_allowed_letter_count[letter] = \
                    greens_n_yellows.count(letter)

    def check_letter_count(self, word, _, __):
        ''' Check if the word has allowed number of letters
        Use instance variable "max_allowed_letter_count"
        '''
        for letter, allowed_count in self.max_allowed_letter_count.items():
            if word.count(letter) > allowed_count:
                return False
        return True

    def reduce_by_difficulty(self, guess, answer, difficulty):
        ''' Given the guess and answer, filter the list,
        so it would comply with HARD (difficulty==1) and
        ULTRA HARD (difficulty==2) rules.
        Used for the list of guesses - as not all guesses are valid on
        higher difficulties.
        '''
        # Do nothing for NORMAL difficulty level
        if difficulty == 0:
            return None

        # List of checks to perform on the words
        # Each one is a function that gets (word, guess, answer)
        # and returns False if a word is not acceptable
        checks = []
        # hecks for HARD
        if difficulty == 1:
            checks = [self.check_green, self.check_yellow_lax]
        # Checks for ULTRA HARD
        # Note that Yellow_lax has to come after Yellow_strict
        if difficulty == 2:
            self.calculate_allowed_letter_count(guess, answer)
            checks = [self.check_letter_count,
                      self.check_green,
                      self.check_yellow_strict,
                      self.check_yellow_lax,
                      self.check_grey]

        # Apply these checks on all the words in the list
        words_to_delete = []
        for word_n, word_original in self.words.items():
            word = list(word_original)
            for check in checks:
                if not check(word, guess, answer):
                    words_to_delete.append(word_n)
                    break

        # Purge those who don't comply
        for word_to_delete in words_to_delete:
            del self.words[word_to_delete]

        return None

    def sample(self, sample_size, use_numbers=False):
        ''' Return sample_size size words from the list (or all remaining,
        if there are fewer left). Can be used to get the words themselves
        (for example one secret word) or their numbers (for example when
        looking for the best guess)
        '''
        # Pick the thing to sample
        if use_numbers:
            sample_space = self.words.keys()
        else:
            sample_space = self.words.values()

        if sample_size >= len(self):
            return list(sample_space)

        return random.sample(list(sample_space), sample_size)

    def copy(self):
        ''' Create and return a copy of itself, by copying internal dicts
        '''
        the_copy = WordList()
        the_copy.words = self.words.copy()
        the_copy.reverse = self.reverse.copy()
        return the_copy

    def word2n(self, word):
        ''' Return the index of the word
        '''
        return self.reverse[word]

    def __len__(self):
        ''' Return the length of the word list
        '''
        return len(self.words)

    def __str__(self):
        ''' String rep: length of the word list, and first and last words
        '''

        # How many words to display in the  beginning and in the end
        max_words_to_show = 4
        words = self.sample(max_words_to_show)

        out = f"WordList ({len(self)})"

        if self:
            out += ": "

        out += ", ".join(words)

        if len(self) > max_words_to_show:
            out += " ..."

        return out


class WData():
    ''' Class to calculate all necessary data for the solution:
    intersection of guesses and answers, list of answers etc.
    '''

    # Folder to store cross-check files
    folder_name = "./wordle_matrixes/"

    def __init__(self, guesses, secrets):
        ''' Generate the data. Incoming are two WordList objects
        '''
        # Word length
        self.word_length = len(secrets.words[0])
        # possible answers and their indexes
        self.pos_answers = self.generate_all_possible_answers(self.word_length)
        self.matrix = self.get_the_matrix(secrets, guesses)

    @staticmethod
    def generate_all_possible_answers(word_len):
        ''' Generate all possible answers for the word length word_len.
        Put them in a dictionary like this:
        {(0,0,0,0,0): 0, (0,0,0,0,1): 1,  ..., (2,2,2,2,2): 242}
        '''
        out = {}
        # Precalculate powers of 3 to 0..word_len
        powers = {j: 3**j for j in range(word_len)}

        # There are exactly 3**word_len possible answers
        for i in range(3**word_len):
            answer = tuple((i // powers[j]) % 3 for j in range(word_len))
            out[answer] = i
        return out

    @staticmethod
    def generate_filename(secrets, guesses):
        ''' Hash two input word lists, keep last 8 digits.
        Use that in the file name of the cross-check file (matrix).
        This way we can re-use previously calculated data,
        but we'll immediately see if it is not up-to-date.
        '''
        hashed_items = hashlib.new('sha256')
        hashed_items.update(str(secrets.words).encode("utf-8"))
        hashed_items.update(str(guesses.words).encode("utf-8"))
        hash_str = hashed_items.hexdigest()
        return f"{WData.folder_name}wordle_matrix_{hash_str[:8]}.npy"

    def get_the_matrix(self, secrets, guesses):
        ''' Load the matrix if saved version exists.
        If not, generate, save, return.
        Matrix saved as "/{folder_name}/wordle_matrix_[last 8 hash digits].npy"
        Hash is generated from all words of both word lists
        '''
        filename = self.generate_filename(secrets, guesses)

        # Use existing file if it is there
        if os.path.exists(filename):
            matrix = np.load(filename)

        # Generate a new file
        else:
            print("Generating a cross-check file " +
                  "(may take a few minutes) ... ")
            matrix = self.generate_the_matrix(secrets, guesses)

            # Create a folder if needed
            if not os.path.exists(WData.folder_name):
                os.makedirs(WData.folder_name)

            # Save the file for future use
            np.save(filename, matrix)
            print("Done")

        return matrix

    def generate_the_matrix(self, secrets, guesses):
        ''' Generate the main matrix of answers: all guessing words X
        puzzle words: an answer number in the cell.

        Matrix works like this:
        matrix[secret_word][guess] = code_of_the_answer

        code_of_the_answer is the value from the dictionary of all possible
        answers, generated by generate_all_possible_answers.
        '''

        # Pick the size of the element in the matrix
        if len(self.pos_answers) < 256:
            data_type = np.uint8
        elif len(self.pos_answers) < 256**2:
            data_type = np.uint16
        else:
            data_type = np.int32

        matrix = np.zeros((len(secrets), len(guesses)), dtype=data_type)
        for i, correct_word in secrets.words.items():
            for j, guess_word in guesses.words.items():
                answer = get_the_answer(guess_word, correct_word)
                matrix[i][j] = self.pos_answers[answer]
        return matrix


class Wordle:
    ''' Class to hold one game's data: the secret word, guess attempts, result.
    This class has no information about word lists, it only has a secret word
    and deals with guesses and answers.
    '''

    def __init__(self, secret_word):
        ''' Create  new game, with secret_word secret
        '''
        self.secret_word = secret_word
        self.history = []

    def make_move(self, guess_word):
        ''' One Move in wordle. Gets a guess in (as a word),
        returns an answer (as (2,1,1,1,0))
        '''
        answer = get_the_answer(guess_word, self.secret_word)
        self.history.append((guess_word, answer))
        return answer

    def to_single_str(self):
        ''' Represent Wordle game as one string,
        with guesses, separated by space.
        Used in log file.
        '''
        return " ".join([word for word, _ in self.history])

    def __len__(self):
        ''' Length (number of made guesses) of a game
        '''
        return len(self.history)

    def __str__(self):
        ''' String form of how the game went, in the form of:
        1. slate: YG__Y
        Used when verbose=True in simulation options.
        '''
        out = ""
        for move, (word, answer) in enumerate(self.history):
            answer_colors = "".join([str(c) for c in answer])\
                .replace("2", "G").replace("1", "Y").replace("0", "_")
            out += f"{move+1}: {word} {answer_colors}\n"
        return out


def get_the_answer(guess_word, correct_word):
    ''' Given secret word and the guess, return the answer
    as (0,0,1,2,0), where 0 is grey, 1 - yellow, 2 - green
    '''
    # Start with all greys
    result = [0 for _ in range(len(correct_word))]
    # We are using a copy to be able delete guessed green and yellow letters,
    # to process doubles letters correctly
    correct_copy = list(correct_word)

    # First, find greens
    for i, guessed_char in enumerate(guess_word):
        if guessed_char == correct_copy[i]:
            result[i] = 2
            correct_copy[i] = ""

    # Then, yellows
    for i, guessed_char in enumerate(guess_word):
        if guessed_char in correct_copy and result[i] != 2:
            result[i] = 1
            # Remove that letter fro the correct word
            # So that it is encountered in the guess again
            # it would not be automatically yellow
            for j in range(len(correct_word)):
                if correct_copy[j] == guess_word[i]:
                    correct_copy[j] = ""
                    # However, remove it from the correct word only once,
                    # so if there are 2 yellows, both would work.
                    # Therefore, break.
                    break

    return tuple(result)


def one_game(secrets_original, guesses_original, data,
             difficulty=0, strength=100):
    ''' Playing one game of Wordle.
    Inputs WordList objects for secret words, possible guesses,
    cross-check data, difficulty level of Wordle, strength of the bot.
    Returns the Wordle object with finished game.
    '''

    # We'll be deleting invalid items, so let's make a copy
    # of both word lists first
    secrets = secrets_original.copy()
    guesses = guesses_original.copy()

    # Pick a random word
    secret = secrets.sample(1)[0]
    game = Wordle(secret)

    while True:

        # This (empty list of remaining possible words)
        # should not happen if everything works fine
        if not secrets:
            print("EMPTY SECRETS")
            print(secret)
            print(game)
            raise RuntimeError

        # Main part of what bot does: pick the guess
        guess_n, _ = secrets.find_best_guess(guesses, data, strength=strength)

        # Transform it in a word and get the answer from the game
        guess = guesses.words[guess_n]
        answer = game.make_move(guess)

        # If we answer is all green: we are done
        if 0 not in answer and 1 not in answer:
            break

        # Only keep secret words that comply with the last guess and answer
        secrets.reduce_by_guess(guess_n, data.pos_answers[answer], data)

        # Purge secrets and guesses according to the chosen difficulty
        if difficulty != 0:
            guesses.reduce_by_difficulty(guess, answer, difficulty)
            secrets.reduce_by_difficulty(guess, answer, difficulty)

    return game


def simulation(options: SimulationOptions):
    ''' Simulation. Play the games run times
    verbose=True to print out each game
    Returns win rate, average length of all games
    '''

    # Initiate word lists and data
    secrets, guesses, data = init_data(options.word_length)

    wins = 0
    results = []
    log = ""

    for _ in range(options.runs):
        game_result = one_game(secrets, guesses, data,
                               difficulty=options.difficulty,
                               strength=options.strength)
        if options.verbose:
            print(game_result)
        if options.logfile_name:
            log += f"{game_result.to_single_str()}\n"

        if len(game_result) <= 6:
            wins += 1
            results.append(len(game_result))

    if options.logfile_name:
        with open(options.logfile_name, "w", encoding="utf-8") as log_fs:
            log_fs.write(log)

    # Return win rate, average game length, max length
    win_rate = wins / options.runs
    ave_length = sum(results) / wins if wins > 0 else 0

    return win_rate, ave_length


def find_one_best_opening(secrets, guesses, data):
    ''' Find the best opening word (has largest distribution).
    Also, how large was the distribution and
    was it as big as secrets list?
    '''
    word_n, distribution = secrets.find_best_guess(guesses, data, strength=-1)
    return guesses.words[word_n], distribution


def find_all_best_openings():
    ''' Find the best opening word for all word length
    '''
    for word_length in range(1, 16):
        secrets, guesses, data = init_data(word_length)
        word, distribution = find_one_best_opening(secrets, guesses, data)
        print(f"Word length {word_length}: best word is '{word}' " +
              f"(results in {distribution} possible answers " +
              f"out of {len(secrets)} total secrets)")


def show_word_stat():
    ''' Display word count for all word lengths
    '''
    for word_length in range(1, 16):
        secrets = WordList("hello-wordle-secret.txt", word_length)
        guesses = WordList("hello-wordle-all.txt", word_length)
        print(f"Word length: {word_length}")
        print(secrets)
        print(guesses)
        print(f"Guesses to secrets ratio: {len(secrets)/len(guesses):.1%}")
        print("\n")


def init_data(word_length):
    ''' Load words, calculate the cross-reference data
    '''
    secrets = WordList("hello-wordle-secret.txt", word_length)
    guesses = WordList("hello-wordle-all.txt", word_length)
    data = WData(guesses, secrets)
    return secrets, guesses, data


def main():

    ''' Main run: simulations for all word lengths and difficulties
    '''

    start_time = time.time()

    # Simulation options, see SimulationOptions class for more
    options = SimulationOptions(
        # How many games to simulate
        runs=1000,
        # Whether to output all guesses and answers for each game
        verbose=False,
        # Bot strength (how many random words it choses the guess from)
        strength=5,
        # File to log out the games (1 game - 1 line)
        # logfile_name="hello-wordle-sim-log.txt"
    )

    for options.word_length in range(2, 16):

        for options.difficulty in range(3):

            print(f"Simulation: Word length: {options.word_length}, " +
                  f"runs: {options.runs}, difficulty: {options.difficulty}, " +
                  f"Bot strength: {options.strength}")

            win_rate, ave_len = simulation(options)
            print(f"Win rate: {win_rate:.1%}, " +
                  f"AverageLength: {ave_len:.2f}\n")

    print(f"Running time: {time.time() - start_time}")


if __name__ == "__main__":
    # Show all available word lists stats
    #show_word_stat()

    # Show best opening words for all word lengths
    #find_all_best_openings()

    # Run the main simulation (2-15 letters, 0-2 difficulty, 100 games oer run)
    main()
