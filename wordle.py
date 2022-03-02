''' Wordle simulator.
Strategies: naive; weighted by letters, weighted by positions; re-use green.
'''

import random
import time

class WordList:
    ''' Class to load the list of words from file
    Initialized with the file(s) to load words from
    '''

    def __init__(self, *files):
        # list of all the words
        self.word_list = []
        for file in files:
            with open(file, "r", encoding="UTF-8") as in_file:
                for line in in_file:
                    self.word_list.append(line.strip())

        # letter counts in all words in the list: {"a": 100, "b": 200, ...}
        self.letter_count = {}

        # words' scores: {"apple": 100, "fruit": 200} etc
        # score is the sum of all letters' frequences
        self.word_scores = {}

        # Same, but scores accont for letter positions
        self.position_letter_count = [{}, {}, {}, {}, {}]
        self.position_word_scores = {}

        # Gererate the word scores
        # (both positional and total)
        self.gen_word_scores()
        self.gen_positional_word_scores()

    def copy(self):
        ''' Copy of existing wordlist
        '''
        new_word_list = WordList()
        new_word_list.word_list = self.word_list.copy()
        new_word_list.word_scores = self.word_scores.copy()
        new_word_list.position_word_scores = self.position_word_scores.copy()
        return new_word_list

    def __len__(self):
        ''' Return count of remaining words: len(word_list)
        '''
        return len(self.word_list)

    def get_random_word(self):
        ''' Return random word from the word list
        '''
        return random.choice(self.word_list)

    def get_hiscore_word(self, use_position=False):
        ''' Return the word with the highest score
        use_position: whether or not use position-based scores
        '''
        scores = self.position_word_scores if use_position else self.word_scores
        best_word = ""
        best_score = 0
        for word in self.word_list:
            if scores[word] > best_score:
                best_score = scores[word]
                best_word = word
        return best_word

    def get_maximized_word(self, letters):
        ''' Return the word with maximized number of "letters"
        '''
        best_word = ""
        best_score = 0
        for word in self.word_list:
            this_score = 0
            for letter in letters:
                if letter in word:
                    this_score += 1
            if this_score > best_score:
                best_score = this_score
                best_word = word
        return best_word

    def gen_letter_count(self):
        ''' Calculate counts of all letters in the word_list
        '''
        self.letter_count = {c:0 for c in "abcdefghijklmnopqrstuvwxyz"}
        for word in self.word_list:
            for letter in set(word):
                self.letter_count[letter] += 1

    def gen_positional_letter_count(self):
        ''' calculate letter count for each letter position
        '''
        for i in range(5):
            self.position_letter_count[i] = \
                            {c:0 for c in "abcdefghijklmnopqrstuvwxyz"}
        for word in self.word_list:
            for i, letter in enumerate(word):
                self.position_letter_count[i][letter] += 1

    def gen_word_scores(self):
        ''' Calculate scores for each word
        '''
        self.gen_letter_count()
        self.word_scores = {}
        for word in self.word_list:
            word_score = 0
            for letter in set(list(word)):
                word_score += self.letter_count[letter]
            self.word_scores[word] = word_score

    def gen_positional_word_scores(self):
        ''' Calculate positional scores for each word
        '''
        self.gen_positional_letter_count()
        self.position_word_scores = {}
        for word in self.word_list:
            # Sum up scores, but if the letter is twice in the word
            # use the highest score only
            word_score = {}
            for i, letter in enumerate(word):
                if letter not in word_score:
                    word_score[letter] = self.position_letter_count[i][letter]
                else:
                    word_score[letter] = max(word_score[letter],
                                             self.position_letter_count[i][letter])
            self.position_word_scores[word] = sum(word_score.values())

    def filter_by_mask(self, mask, antimask, must_use):
        ''' Removing words from the word list, according to the mask
        '''
        # I feel if would be faster to just create a new list instead of
        # deleting in-place
        new_words = []
        # make a copy. we'll be deleting letters (n case of doubles)
        for word in self.word_list:
            # check if all the letters from must_use are present
            for letter in must_use:
                if letter not in word:
                    break
            else:
                # check if the word complies to the mask
                # if mask letter not found - discard
                for i, letter in enumerate(word):
                    if letter not in mask[i]:
                        break
                else:
                    # check if the word complies with antimask
                    # if antimask letter found - discard
                    for i, letter in enumerate(word):
                        if letter in antimask[i]:
                            break
                    else:
                        new_words.append(word)
        self.word_list = new_words

class Guess:
    ''' Class for one guess attempt
    Contains the guessed word and list of results
    '''

    def __init__(self, guess_word, correct_word):
        self.word = guess_word
        # Set to True, but will be swithed
        self.guessed_correctly = False
        self.result = self.get_result(correct_word)

    def __str__(self):
        ''' String representation looks like: ducky: G__Y_
        G, Y, _ is for green / yellow / grey
        '''
        out = f"{self.word}: "
        for letter_result in self.result:
            if letter_result == 2:
                out += "G"
            elif letter_result == 1:
                out += "Y"
            if letter_result == 0:
                out += "_"
        return out


    def get_result(self, correct_word):
        ''' Given the guessed and the right word
        generate the list of letter results:
        0/1/2 meaning no/misplaced/correct
        '''
        result = [0, 0, 0, 0, 0]
        # we are using a copy to blank guessed green and yellow
        # letters (to correctly display doubles)
        correct_copy = list(correct_word)

        for i, guessed_char in enumerate(self.word):
            if guessed_char == correct_copy[i]:
                result[i] = 2
                correct_copy[i] = ""
        for i, guessed_char in enumerate(self.word):
            if self.word[i] in correct_copy and result[i] != 2:
                result[i] = 1
                for j in range(5):
                    if correct_copy[j] == self.word[i]:
                        correct_copy[j] = ""
                        break
        if result == [2, 2, 2, 2, 2]:
            self.guessed_correctly = True
        return result


class Wordle:
    ''' Class representing one wordle game.
    methods include initiating a secret word,
    returning green/yellow/grey results,
    keeping track of guessed letters
    '''

    def __init__(self, correct_word=None):
        # the word to guess
        if correct_word in puzzle_words.word_list:
            self.correct_word = correct_word
        else:
            self.correct_word = puzzle_words.get_random_word()

        # list of guesses so far
        self.guesses = []

    def __str__(self):
        out = f"::{self.correct_word}::"
        for i, guess in enumerate(self.guesses):
            out += f"\n{i+1}. {guess}"
        return out

    def guess(self, word):
        ''' One turn of the game
        get guessed word, add new Guess in guesses list
        if guessed correctly, return True, esle False
        '''
        self.guesses.append(Guess(word, self.correct_word))
        # Return True/False if you got the word right
        return self.guesses[-1].guessed_correctly


class Player:
    ''' Default player (random)
        Guesses a random word from the whole list
    '''

    def __init__(self):
        # five lists: which letters ae allowed in each spot
        self.mask = [set(list('abcdefghijklmnopqrstuvwxyz')) for _ in range(5)]
        # which letter has to be in the word, from green and yellow letters
        self.must_use = set()
        # copy of the global wordset (we'll be removing unfit words from it)
        self.remaining_words = guessing_words.copy()

    def filter_word_list(self):
        ''' Removing words from the word list, that don't fit with
        what we know about the word (using mask and must_use)
        '''
        antimask = [set() for _ in range(5)]
        self.remaining_words.filter_by_mask(self.mask, antimask, self.must_use)

    def reuse_green(self):
        ''' Try to re-use "green" space by putting some remaining letters there
        '''

        # 1. Find Green masks
        # 2. Combine masks from non-green letters
        mask_lens = [len(self.mask[i]) for i in range(5)]
        combined_mask = set()
        green_masks = []
        for i, mask_len in enumerate(mask_lens):
            if mask_len == 1:
                green_masks.append(i)
            else:
                combined_mask = set.union(combined_mask, self.mask[i])

        # Add some vowels for better chance of finding a good word
        original_mask = combined_mask.copy()
        combined_mask = set.union(combined_mask, set(["a", "e", "i", "o"]))

        # Create temporary masks to filter original word list
        # Antimask to prevent from accidentally using green letters again
        temp_mask = self.mask.copy()
        temp_antimask = [set() for _ in range(5)]
        for i in range(5):
            if i in green_masks:
                temp_antimask[i] = temp_mask[i]
                temp_mask[i] = combined_mask

        # Find the word to fit temporary mask
        temp_words = guessing_words.copy()
        temp_words.filter_by_mask(temp_mask, temp_antimask, set())
        if len(temp_words) > 0:
            return temp_words.get_maximized_word(original_mask)

        return ""

    def make_guess(self):
        ''' Pick the word from the list
        '''
        # Use random word if:
        # 1. "scored" is no set
        # 2. "firstrandom" is set and this is the first guess
        # (word list has not been filtered yet)
        if "scored" not in params or \
           "firstrandom" in params and \
           len(self.remaining_words) == len(guessing_words):
            return self.remaining_words.get_random_word()

        # list of masks' lenths
        mask_lens = [len(self.mask[i]) for i in range(5)]
        # Conditions for "re-use green" logic:
        # has Green; more than 2 potential answers
        if "easymode" in params and mask_lens.count(1) > 0 \
           and len(self.remaining_words) > 2:
            # if reusing green is successful, return that word
            reuse_green_word = self.reuse_green()
            if reuse_green_word != "":
                return reuse_green_word

        # recount / don't recount all scores
        if "recount" in  params:
            self.remaining_words.gen_word_scores()
            self.remaining_words.gen_positional_word_scores()

        # use / don't use position letter weights
        if "position" in  params:
            return self.remaining_words.get_hiscore_word(use_position=True)
        return self.remaining_words.get_hiscore_word(use_position=False)

    def update_mask_green(self, guess):
        ''' Use Green result: delete all other letters in this mask
        '''
        for i, letter_result in enumerate(guess.result):
            if letter_result == 2: # green: right letter and place
                self.mask[i] = set(guess.word[i])
                self.must_use.add(guess.word[i])

    def update_mask_yellow(self, guess):
        ''' Use Yellow
        1. Delete this letter in this mask
        2. Add it to "must use"
        '''
        # Delete the letter in the same place in the mask
        for i, letter_result in enumerate(guess.result):
            if letter_result == 1:
                if guess.word[i] in self.mask[i]:
                    self.mask[i].remove(guess.word[i])
                self.must_use.add(guess.word[i])

    def update_mask_grey(self, guess):
        ''' Use Grey results. Delete this letter from all masks
        '''
        letters_to_delete = []
        for i, letter_result in enumerate(guess.result):
            if letter_result == 0: # gray: no letter in this word
                # if it is also was in green or yellow -
                # only delete in this place
                if guess.word[i] in self.must_use \
                   and guess.word[i] in self.mask[i]:
                    self.mask[i].remove(guess.word[i])
                # this is a weird case that can occure in "easymode" strategy
                # out-of-remainig list word can accidentaly trigger deleting
                # more words than it should. This stops it.
                elif guess.word[i] in self.must_use \
                   and guess.word[i] not in self.mask[i]:
                    pass
                # if not - remove everywhere
                else:
                    letters_to_delete.append(guess.word[i])
        # This is where we remove them from all masks
        for i, one_mask in enumerate(self.mask):
            for letter_to_delete in letters_to_delete:
                if letter_to_delete in one_mask:
                    one_mask.remove(letter_to_delete)

    def update_mask_with_guess(self, guess):
        ''' Combine mask updating functions
        according to parameters
        '''
        # the order is important for correct handling of double letters
        self.update_mask_green(guess)
        self.update_mask_yellow(guess)
        self.update_mask_grey(guess)


    def update_mask_with_wordlist(self):
        ''' Update the mask according to the word in the remaining_words
        '''
        self.mask = [set() for _ in range(5)]
        for word in self.remaining_words.word_list:
            for i, letter in enumerate(word):
                self.mask[i].add(letter)


    def remove_word(self, word):
        ''' Remove a word from possible guesses
        used to remove used words
        '''
        if word in self.remaining_words.word_list:
            self.remaining_words.word_list.remove(word)

def play_one_game(quiet=True, correct_word=None):
    ''' Playing one round of Wordle using player strategy
    from PlayerType
    '''
    game = Wordle(correct_word)
    player = Player()
    done = False

    # Cycle until we are done
    while not done:

        # Make a guess
        players_guess = player.make_guess()

        # Play the guess, see if we are done
        if game.guess(players_guess):
            done = True

        # Post-guess action:
        # Remove the words we just played
        player.remove_word(players_guess)
        # Update mask with guess results
        player.update_mask_with_guess(game.guesses[-1])

        # Filter the word down according to new mask
        player.filter_word_list()
        # Filter the mask according to the remaining words
        player.update_mask_with_wordlist()

    if not quiet:
        print (game)
    if game.guesses[-1].guessed_correctly:
        return game.guesses
    return -1 # This shouldn't happen


def parse_results(results):
    ''' Get couple of main statistics from the list of results
    '''
    frequencies = {}
    lengths = []
    complete = 0
    turns_sum = 0
    for result in results:
        length = len(result)
        lengths.append(length)
        if length in frequencies:
            frequencies[length] += 1
        else:
            frequencies[length] = 1
        turns_sum += length
        if length <= MAX_TURNS:
            complete += 1

    print (f"Wins: {complete}, Losses: {len(results)-complete}")
    print (f"Winrate: {complete*100/len(results):.1f}%")

    if complete > 0:
        print (f"Average length: {turns_sum/len(results):.1f}")

    print (f"Median length: {sorted(lengths)[len(results) // 2]}")


def write_log(results):
    ''' Write the results of the simulation in the txt file
    format is "guess1 guess2 guess3"
    final guess is also the secret word
    '''
    filename = f"wordle_log_{int(time.time())}.txt"
    with open(filename, "w", encoding="utf-8") as log_file:
        for result in results:
            for i, guess in enumerate(result):
                log_file.write (guess.word)
                if i != len(result) - 1:
                    log_file.write(" ")
                else:
                    log_file.write("\n")


def simulation(number_of_runs):
    ''' play the game number_of_runs times
    return the list with all results
    '''
    print (f"Parameters: {params}, Runs: {number_of_runs}")
    simulation_results = []
    words_to_solve = puzzle_words.word_list.copy()

    for _ in range(number_of_runs):
        if number_of_runs == 2315:
            word = words_to_solve.pop()
            simulation_results.append(play_one_game(correct_word=word))
        else:
            simulation_results.append(play_one_game())

    parse_results(simulation_results)
    write_log(simulation_results)

def main():
    ''' launch the simulation
    '''
    start_time = time.time()

    if N_GAMES == 1:
        play_one_game(quiet=False)
    else:
        simulation(N_GAMES)

    print (f"Time: {time.time()-start_time}")

if __name__ == "__main__":

    # Word lists to use:
    # List that wordle game uses as a target word
    puzzle_words = WordList("words-guess.txt")
    # List that the "player" program uses
    guessing_words = WordList("words-guess.txt", "words-all.txt")

    # Game length (the game will go on, but it will affect the % of wins)
    MAX_TURNS = 6

    # Player's settings:
    # With everything off uses the naive greedy method (limit the potential
    # answers and randomly chose a word from the remaining list)
    # "scored": weight words by the frequency of the words
    #   "recount": recalculate weights for every guess
    #   "firstrandom": random first guess
    #       (worse results but more interesting to watch)
    #   "position": use positional letter weights
    # "easymode": don't have to use current result (reuse green space)
    params = ["scored", "recount", "firstrandom_off", "position", "easymode"]

    # Number of games to simulate
    # if == 1, plays one random game, shows how the game went
    # if == 2315, runs simulation for all Wordle words (for deterministic methods)
    # other numbers - play N_GAMES games with random words from puzzle_words
    N_GAMES = 2315

    main()
