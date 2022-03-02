''' Wordle tree builder
Best tree has average length of 3.4211
Takes 3-5 hours to complete.
(Or about an hour if you override the first guess,
uncomment lines 81-82 for that)
'''

import time
import os.path
import numpy as np
import wordle
import math

def generate_the_matrix():
    ''' Generate the main matrix of answers: all guessing words X
    puzzle words: an answer number in the cell.
    '''
    matrix = np.zeros((len(puzzle_words), len(guessing_words)), dtype=np.uint8)
    for i, correct_word in enumerate(puzzle_words.word_list):
        for j, guess_word in enumerate(guessing_words.word_list):
            guess = wordle.Guess(guess_word, correct_word)
            matrix[i][j] = possible_answers[tuple(guess.result)]
    return matrix

def get_the_matrix():
    ''' Load the matrix if saved version exists.
    If not, generate, save, return
    '''
    if os.path.exists("wordle_big_file.npy"):
        matrix = np.load("wordle_big_file.npy")
    else:
        print("Generating the cross-check file (takes a couple of minutes)")
        matrix = generate_the_matrix()
        np.save("wordle_big_file.npy", matrix)
    return matrix

def generate_all_possible_answers():
    ''' Generate all posible answers. and put them om dictionary
    like this: {(0,0,0,0,0): 0 ..., (2,2,2,2,2): 242}
    '''
    out = {}
    for i in range(3**5):
        a_mask = tuple([(i // 3**j) % 3 for j in range(5)])
        out[a_mask] = i
    return out

def get_distribution(word_ns, guess_word_n):
    ''' get list of sizes of resulting wordlist, after splitting
    word_list by guess guess_word
    '''
    answers = {i:0 for i in range(243)}
    for n in word_ns:
        answers[matrix[n][guess_word_n]] += 1
    # remove zeros
    non_zero_sizes = []
    for count in answers.values():
        if count != 0:
            non_zero_sizes.append(count)
    return non_zero_sizes

def score_distribution(distribution):
    ''' return a score of distribution
    '''
    return STRATEGY(distribution)

def ave_entropy(distribution):
    p = len(distribution)
    ent = - sum([math.log2(n/p) for n in distribution])
    return ent / len(distribution)

def get_top_guesses(word_ns, ignore_ns):
    ''' Return top "tops" distributions with highest scores
    '''
    # First, can the list be broken by one if the words in it?
    if len(word_ns)<500:
        for guess_word in word_ns:
            distribution = get_distribution(word_ns, guess_word)
            if distribution.count(1) == len(distribution):
                return [guess_word]

    # Override the first guess
    #if len(word_ns) == 2315:
    #    return [10183]

    # Number of bests to check.
    # Minimum parameters for best result are: 3,5,10,20
    if len(word_ns) > 300:
        options = 3
    elif len(word_ns) >= 10:
        options = 10
    else:
        options = 20
        
    best_score = [None for _ in range(options)]
    best_n = [None for _ in range(options)]
    for guess_n in guess_words_ns:
        if guess_n in ignore_ns:
            continue
        distribution = get_distribution(word_ns, guess_n)
        score = score_distribution(distribution)
        
        # Find the best one
        for i in range(options):
            if best_n[i] is None or score > best_score[i]:
                best_score.insert(i, score)
                best_n.insert(i, guess_n)
                del best_score[options]
                del best_n[options]
                #print (best_n, best_score)
                break

    return best_n

def get_valid_results(word_ns, guess_word_n):
    ''' Return list of (answer, resulting_list) that are valid for this
    initial list and guess
    '''
    answers = {i:[] for i in range(243)}
    for n in word_ns:
        answers[matrix[n][guess_word_n]].append(n)
    # remove empty ones
    out = {}
    for answer, words in answers.items():
        if len(words) > 0:
            out[answer] = words
    return out

def result_length(result):
    ''' Len of this result (sum of the 2nd levels lenths)
    '''
    count = 0
    for line in result:
        count += len(line)
    return count

def add_node(word_ns, previous_guesses):
    ''' main recursive function
    '''

    final_result = None
    print (f"Starting new node for the list of {len(word_ns)}")
    best_guesses = get_top_guesses(word_ns, previous_guesses)
    print (f"Best  are: {best_guesses}")
    for i, best_guess in enumerate(best_guesses):
        
        out = []
        #print (f"Attempt {i}. Best word is: {best_guess}")
        answers = get_valid_results(word_ns, best_guess)

        for answer, new_list in answers.items():
            if len(new_list) == 1 or answer == 242:
                out.append(list(previous_guesses))

                if answer != 242:
                    out[-1].append(best_guess)
                out[-1].append(new_list[0])
                
            else:
                #print (f"After asnswer {answer} still a list of " + 
                #      f"{len(new_list)}")
                out += add_node(new_list, tuple(list(previous_guesses) + [best_guess]))
                
        if final_result is None or result_length(out) < result_length(final_result):
            final_result = out

    return final_result

def result_to_text(result):
    ''' Convert those numbers back to words
    '''
    out = ""
    for line in result:
        correct_word = guessing_words.word_list[line[-1]]
        for word in line:
            guess_word = guessing_words.word_list[word]
            out += guess_word + "\t"
            guess = wordle.Guess(guess_word, correct_word)
            guess_txt = "".join(str(c) for c in guess.result)
            out += guess_txt + "\t"
        out += "\n"
    return out



def main():
    '''
    '''
    word_ns = [n for n in range(len(puzzle_words))]
    prev = ()

    result = add_node(word_ns, prev)
    print (result[:10])
    with open("results.txt", "w") as fs:
        fs.write(result_to_text(result))
    print ("Ave:", result_length(result)/2315)

if __name__ == "__main__":

    t = time.time()

    puzzle_words = wordle.WordList("words-guess.txt")
    guessing_words = wordle.WordList("words-guess.txt", "words-all.txt")
    possible_answers = generate_all_possible_answers()
    matrix = get_the_matrix()
    guess_words_ns = [n for n in range(len(guessing_words))]
    
    STRATEGY = len
    #STRATEGY = ave_entropy
    
    main()
    print (time.time()-t)
