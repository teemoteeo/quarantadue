*This project has been created as part of the 42 curriculum by tcostant*

# DESCRIPTION

The program reads text from a .txt file, stashes what it reads in a **stash** variable, extracts and returns every line from the stash (where a line is every char positioned before a '\n' character).

# INSTRUCTIONS

To use program be sure to have a .txt file in your directory and be sure to adjust line 111 in get_next_line.c to fit you file's name.

		IN TERMINAL ---> cc -Wall -Wextra -Werror get_next_line.c get_next_line_utils.c
						 ./a.out

# RESOURCES

YT:	-https://www.youtube.com/watch?v=8E9siq7apUU&t=905s&pp=ygUNZ2V0IG5leHQgbGluZQ%3D%3D
	-https://www.codequoi.com/en/local-global-static-variables-in-c/

GITHUB: -https://github.com/Tripouille/gnlTester

CHATGPT & GEMINI: used for code design and for general assistance

# EXPLANATION

Code structure is **"Read-Append-Split"**, task divided in 3 subproblems:

	-read_and_stash manages I/O.
	-extract_line manages output.
	-clean_stash manages stash and memory leaks.
