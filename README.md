# Wordle simulator

This is a simple Python Wordle simulator that can use different strategies, play thousands of games to test those strategies (or 2315 if a strategy is deterministic).

## Source words
Words are stored in two files
* words-guess.txt are all the *secret words*
* words-all.txt are all *additional* words that program can use

## Simple approach + Strategies (wordle.py)

Strategies can be switched on and off in the “param” list

### “naive” or “basic” or “greedy” strategy
This is a default strategy based on the colors of letters in answers. This  one cannot be switched off, this is the basis for all others

### “scored"
Weigh words by the frequency of the words

###  "recount"
Recalculate weights for every guess. Obviously, it only makes sense if “scored" is on.

###   "position"
Use letter weights that also consider letters’ positions

### "easymode"
With this strategy the program doesn't use the word from a narrowed down list of possible answers, but instead tries to reuse green spaces to get more information about the word.

### Results
Strategies would get winning rate from 89% (naive) to 99.6% (“easymode” a.k.a. “ reuse green)”.

## Building answers tree (wordle_tree.py)

This is a different approach to solving this problem. We try to find the most efficient way to break down the answers space by guesses. We do it by building a tree, where nodes are guesses and branches – remaining possible answers.

We choose X best candidates for each node and after calculating the branch, keep the most one resulting in fewer guesses.
The best result is achieved with varying branching factors (see lines 87-94).
"Salet" is the third option in the root node, there is on option to override and set it oon the beginning for max fast generation. In this case program runs under an hour on a fast PC.

Result for this one is a 100% winning rate. Best average game length is 3.421 (same as 3b1b got in his video)
